"""
Full Pipeline Runner - The core validation + expert review loop.

This module implements the complete validation workflow:
1. Generate backtest code from hypothesis
2. Run IS backtest via lean CLI
3. Check gates (alpha, sharpe, drawdown)
4. Run OOS backtest (one shot)
5. Run expert review (multiple personas)
6. Mark result (VALIDATED/INVALIDATED)
7. Add derived ideas to catalog

Usage:
    from scripts.validate.full_pipeline import FullPipelineRunner

    runner = FullPipelineRunner(workspace, llm_client)
    result = runner.run("STRAT-309")
"""

import base64
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.utils.logging_config import get_logger

logger = get_logger("full_pipeline")


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    success: bool
    cagr: Optional[float] = None
    sharpe: Optional[float] = None
    max_drawdown: Optional[float] = None
    alpha: Optional[float] = None
    total_return: Optional[float] = None
    benchmark_cagr: Optional[float] = None
    error: Optional[str] = None
    raw_output: Optional[str] = None


@dataclass
class ExpertReview:
    """Results from expert review."""
    persona: str
    assessment: str
    concerns: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    derived_ideas: List[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Results from the full pipeline run."""
    entry_id: str
    determination: str  # VALIDATED, CONDITIONAL, INVALIDATED, FAILED
    is_results: Optional[BacktestResult] = None
    oos_results: Optional[BacktestResult] = None
    expert_reviews: List[ExpertReview] = field(default_factory=list)
    derived_ideas: List[str] = field(default_factory=list)
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class FullPipelineRunner:
    """
    Runs the complete validation + expert review loop.

    This is the core orchestrator that:
    - Drives the entire process deterministically
    - Calls Claude for code generation and expert review
    - Makes gate decisions based on thresholds (not LLM judgment)
    """

    # Gate thresholds
    IS_MIN_ALPHA = 0.0  # IS must have non-negative alpha
    OOS_MIN_ALPHA = 0.0  # OOS must have non-negative alpha
    OOS_MIN_SHARPE = 0.3  # OOS Sharpe must exceed this
    OOS_MAX_DRAWDOWN = 0.50  # OOS drawdown must be less than 50%

    def __init__(self, workspace, llm_client=None, use_local: bool = False):
        """
        Initialize the pipeline runner.

        Args:
            workspace: Workspace instance
            llm_client: LLMClient instance (optional, but needed for code gen and expert review)
            use_local: If True, use local Docker backtest; if False (default), use cloud
        """
        self.workspace = workspace
        self.llm_client = llm_client
        self.use_local = use_local
        self.catalog = None

        # Lazy load catalog
        from research_system.core.catalog import Catalog
        self.catalog = Catalog(workspace.catalog_path)

    def run(self, entry_id: str) -> PipelineResult:
        """
        Run the full pipeline for a single entry.

        Args:
            entry_id: The catalog entry ID to process

        Returns:
            PipelineResult with determination and all results
        """
        logger.info(f"Starting full pipeline for {entry_id}")

        # Get entry from catalog
        entry = self.catalog.get(entry_id)
        if not entry:
            return PipelineResult(
                entry_id=entry_id,
                determination="FAILED",
                error=f"Entry not found: {entry_id}"
            )

        if entry.status == "BLOCKED":
            return PipelineResult(
                entry_id=entry_id,
                determination="BLOCKED",
                error=f"Entry is BLOCKED: {entry.blocked_reason}"
            )

        # Step 1: Generate backtest code (or load existing)
        print("  Generating backtest code...")
        backtest_code = self._generate_backtest_code(entry)
        if not backtest_code:
            return PipelineResult(
                entry_id=entry_id,
                determination="FAILED",
                error="Failed to generate backtest code"
            )

        # Step 2: Calculate IS/OOS periods
        periods = self._calculate_periods(entry)
        print(f"  IS Period: {periods['is_start']} to {periods['is_end']}")
        print(f"  OOS Period: {periods['oos_start']} to {periods['oos_end']}")

        # Step 3: Run IS backtest
        print("  Running IS backtest...")
        is_results = self._run_backtest(backtest_code, periods['is_start'], periods['is_end'], entry_id)

        if not is_results.success:
            return PipelineResult(
                entry_id=entry_id,
                determination="FAILED",
                is_results=is_results,
                error=f"IS backtest failed: {is_results.error}"
            )

        print(f"    CAGR: {is_results.cagr*100:.1f}%  |  Sharpe: {is_results.sharpe:.2f}  |  Max DD: {is_results.max_drawdown*100:.1f}%")
        print(f"    Alpha vs Benchmark: {is_results.alpha*100:.1f}%")

        # Step 4: Check IS gates
        is_passed, is_reason = self._check_is_gates(is_results)
        if not is_passed:
            print(f"  IS Gates: FAILED ({is_reason})")
            # Still run expert review to get improvement ideas
            print("  Running expert review for improvement ideas...")
            expert_reviews = self._run_expert_review(entry, is_results, None)
            derived_ideas = self._extract_derived_ideas(expert_reviews)

            # Print expert summaries
            if expert_reviews:
                print("\n  Expert Analysis:")
                for review in expert_reviews:
                    print(f"    [{review.persona}] {review.assessment[:80]}...")
                    if review.concerns:
                        print(f"      Concerns: {', '.join(review.concerns[:2])}")
                    if review.improvements:
                        print(f"      Suggestions: {', '.join(review.improvements[:2])}")

            # Add derived ideas to catalog
            if derived_ideas:
                self._add_derived_ideas(entry, derived_ideas)
                print(f"\n  Added {len(derived_ideas)} derived ideas to catalog")

            # Update catalog status and save results
            self._update_entry_status(entry_id, "INVALIDATED")
            self._save_results(entry_id, is_results, None, expert_reviews, "INVALIDATED")

            return PipelineResult(
                entry_id=entry_id,
                determination="INVALIDATED",
                is_results=is_results,
                expert_reviews=expert_reviews,
                derived_ideas=derived_ideas,
                error=f"IS gates failed: {is_reason}"
            )

        print("  IS Gates: PASSED")

        # Step 5: Run OOS backtest (ONE SHOT)
        print("  Running OOS backtest (ONE SHOT)...")
        oos_results = self._run_backtest(backtest_code, periods['oos_start'], periods['oos_end'], entry_id)

        if not oos_results.success:
            return PipelineResult(
                entry_id=entry_id,
                determination="FAILED",
                is_results=is_results,
                oos_results=oos_results,
                error=f"OOS backtest failed: {oos_results.error}"
            )

        print(f"    CAGR: {oos_results.cagr*100:.1f}%  |  Sharpe: {oos_results.sharpe:.2f}  |  Max DD: {oos_results.max_drawdown*100:.1f}%")
        print(f"    Alpha vs Benchmark: {oos_results.alpha*100:.1f}%")

        # Step 6: Check OOS gates
        oos_passed, oos_reason = self._check_oos_gates(oos_results)
        if not oos_passed:
            print(f"  OOS Gates: FAILED ({oos_reason})")
        else:
            print("  OOS Gates: PASSED")

        # Step 7: Run expert review
        print("  Running expert review...")
        expert_reviews = self._run_expert_review(entry, is_results, oos_results)
        derived_ideas = self._extract_derived_ideas(expert_reviews)

        # Print expert summaries
        for review in expert_reviews:
            print(f"    [{review.persona}] {review.assessment[:60]}...")

        # Step 8: Make determination
        if oos_passed:
            determination = "VALIDATED"
        else:
            determination = "INVALIDATED"

        # Step 9: Add derived ideas to catalog
        if derived_ideas:
            self._add_derived_ideas(entry, derived_ideas)

        # Step 10: Update entry status
        self._update_entry_status(entry_id, determination)

        # Step 11: Save results
        self._save_results(entry_id, is_results, oos_results, expert_reviews, determination)

        return PipelineResult(
            entry_id=entry_id,
            determination=determination,
            is_results=is_results,
            oos_results=oos_results,
            expert_reviews=expert_reviews,
            derived_ideas=derived_ideas
        )

    def _generate_backtest_code(self, entry) -> Optional[str]:
        """Generate backtest code from the entry's hypothesis."""
        if not self.llm_client:
            logger.warning("No LLM client - cannot generate backtest code")
            return None

        # Check if code already exists in validation folder
        val_dir = self.workspace.validations_path / entry.id
        code_file = val_dir / "backtest.py"
        if code_file.exists():
            return code_file.read_text()

        # Generate code via Claude with detailed API guidance
        prompt = f"""Generate a QuantConnect algorithm to test this hypothesis:

Entry: {entry.id}
Name: {entry.name}
Type: {entry.type}
Summary: {entry.summary}
Hypothesis: {entry.hypothesis}

CRITICAL - Use these EXACT QuantConnect Python API patterns:

1. Resolution enum (ALL CAPS):
   Resolution.DAILY, Resolution.HOUR, Resolution.MINUTE (not Resolution.Daily)

2. Adding securities (snake_case methods):
   self.add_equity("SPY", Resolution.DAILY)
   self.add_future(Futures.Indices.SP_500_E_MINI, Resolution.DAILY)

3. Indicators (snake_case, use symbol's resolution by default):
   # Simple form - uses the security's default resolution
   self.rsi_indicator = self.rsi("SPY", 14)
   self.sma_fast = self.sma("SPY", 10)
   self.sma_slow = self.sma("SPY", 50)
   # If you need explicit resolution, include MovingAverageType:
   # self.rsi_indicator = self.rsi("SPY", 14, MovingAverageType.WILDERS, Resolution.DAILY)

4. Futures symbols (underscores):
   Futures.Indices.SP_500_E_MINI (not SP500EMini)
   Futures.Indices.NASDAQ_100_E_MINI (not NASDAQ100EMini)

5. Accessing data:
   if self.rsi_indicator.is_ready:
       rsi_value = self.rsi_indicator.current.value

6. Trading:
   self.set_holdings("SPY", 1.0)  # 100% long
   self.liquidate("SPY")

7. Benchmark:
   self.set_benchmark("SPY")

IMPORTANT - Variable naming:
   NEVER use indicator method names as variable names (they shadow the methods):
   WRONG: self.rsi = self.rsi(...)      # shadows self.rsi() method!
   WRONG: self.sma = self.sma(...)      # shadows self.sma() method!
   RIGHT: self.rsi_indicator = self.rsi(...)
   RIGHT: self.sma_short = self.sma(...)

Example structure:
```python
from AlgorithmImports import *

class MyAlgorithm(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2020, 1, 1)
        self.set_cash(100000)
        self.spy = self.add_equity("SPY", Resolution.DAILY).symbol
        self.set_benchmark("SPY")
        # Use descriptive names that don't shadow methods
        # Simple form uses security's default resolution
        self.rsi_indicator = self.rsi(self.spy, 14)

    def on_data(self, data):
        if not self.rsi_indicator.is_ready:
            return
        if self.rsi_indicator.current.value < 30:
            self.set_holdings(self.spy, 1.0)
        elif self.rsi_indicator.current.value > 70:
            self.liquidate()
```

Requirements:
- Use the EXACT patterns shown above
- Use snake_case for all method names (initialize, on_data, set_holdings)
- Use Resolution.DAILY (all caps)
- Include benchmark comparison with SPY

Return ONLY the Python code, no explanations."""

        try:
            response = self.llm_client.generate_sonnet(prompt)
            # Extract code from response (handle markdown code blocks)
            code = response.content
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0]
            elif "```" in code:
                code = code.split("```")[1].split("```")[0]

            # Post-process to fix common issues
            code = self._fix_qc_api_issues(code)

            # Save the generated code
            val_dir.mkdir(parents=True, exist_ok=True)
            code_file.write_text(code)

            return code
        except Exception as e:
            logger.error(f"Failed to generate backtest code: {e}")
            return None

    def _fix_qc_api_issues(self, code: str) -> str:
        """
        Post-process generated code to fix common QuantConnect API issues.

        Fixes:
        - Resolution.Daily -> Resolution.DAILY (and other resolutions)
        - Futures symbol names with incorrect casing
        - Method name casing issues
        """
        # Fix Resolution enum casing
        resolution_fixes = {
            "Resolution.Daily": "Resolution.DAILY",
            "Resolution.Minute": "Resolution.MINUTE",
            "Resolution.Hour": "Resolution.HOUR",
            "Resolution.Second": "Resolution.SECOND",
            "Resolution.Tick": "Resolution.TICK",
        }
        for wrong, correct in resolution_fixes.items():
            code = code.replace(wrong, correct)

        # Fix common Futures symbol names
        futures_fixes = {
            "SP500EMini": "SP_500_E_MINI",
            "SP500": "SP_500_E_MINI",
            "NASDAQ100EMini": "NASDAQ_100_E_MINI",
            "NASDAQ100": "NASDAQ_100_E_MINI",
            "Nasdaq100EMini": "NASDAQ_100_E_MINI",
            "Russell2000EMini": "RUSSELL_2000_E_MINI",
        }
        for wrong, correct in futures_fixes.items():
            code = code.replace(wrong, correct)

        # Fix method casing (PascalCase -> snake_case for common methods)
        # Only fix standalone method calls, not class names
        method_fixes = [
            (r'\bself\.SetStartDate\b', 'self.set_start_date'),
            (r'\bself\.SetEndDate\b', 'self.set_end_date'),
            (r'\bself\.SetCash\b', 'self.set_cash'),
            (r'\bself\.SetBenchmark\b', 'self.set_benchmark'),
            (r'\bself\.AddEquity\b', 'self.add_equity'),
            (r'\bself\.AddFuture\b', 'self.add_future'),
            (r'\bself\.AddCrypto\b', 'self.add_crypto'),
            (r'\bself\.SetHoldings\b', 'self.set_holdings'),
            (r'\bself\.Liquidate\b', 'self.liquidate'),
            (r'\bself\.Debug\b', 'self.debug'),
            (r'\bself\.Log\b', 'self.log'),
            (r'\bself\.RSI\b', 'self.rsi'),
            (r'\bself\.SMA\b', 'self.sma'),
            (r'\bself\.EMA\b', 'self.ema'),
            (r'\bself\.MACD\b', 'self.macd'),
            (r'\bself\.BB\b', 'self.bb'),
            (r'\bself\.ATR\b', 'self.atr'),
            (r'\bdef Initialize\b', 'def initialize'),
            (r'\bdef OnData\b', 'def on_data'),
            (r'\bdef OnOrderEvent\b', 'def on_order_event'),
            (r'\bdef OnEndOfDay\b', 'def on_end_of_day'),
            (r'\.Symbol\b', '.symbol'),
            (r'\.IsReady\b', '.is_ready'),
            (r'\.Current\.Value\b', '.current.value'),
        ]
        for pattern, replacement in method_fixes:
            code = re.sub(pattern, replacement, code)

        # Fix incorrect indicator signatures (Resolution without MovingAverageType)
        # Wrong: self.rsi(symbol, 14, Resolution.DAILY)
        # Right: self.rsi(symbol, 14) - uses default resolution from security
        indicator_signature_fixes = [
            # Remove Resolution argument from indicator calls (uses security's default)
            (r'self\.rsi\(([^,]+),\s*(\d+),\s*Resolution\.\w+\)', r'self.rsi(\1, \2)'),
            (r'self\.sma\(([^,]+),\s*(\d+),\s*Resolution\.\w+\)', r'self.sma(\1, \2)'),
            (r'self\.ema\(([^,]+),\s*(\d+),\s*Resolution\.\w+\)', r'self.ema(\1, \2)'),
            (r'self\.atr\(([^,]+),\s*(\d+),\s*Resolution\.\w+\)', r'self.atr(\1, \2)'),
        ]
        for pattern, replacement in indicator_signature_fixes:
            code = re.sub(pattern, replacement, code)

        # Fix variable names that shadow indicator methods
        # Pattern: self.rsi = self.rsi(...) or self.rsi = {} followed by self.rsi[...] = self.rsi(...)
        indicator_shadowing_fixes = [
            # Direct assignment shadowing: self.rsi = self.rsi(...)
            (r'self\.rsi\s*=\s*self\.rsi\(', 'self.rsi_indicator = self.rsi('),
            (r'self\.sma\s*=\s*self\.sma\(', 'self.sma_indicator = self.sma('),
            (r'self\.ema\s*=\s*self\.ema\(', 'self.ema_indicator = self.ema('),
            (r'self\.macd\s*=\s*self\.macd\(', 'self.macd_indicator = self.macd('),
            (r'self\.bb\s*=\s*self\.bb\(', 'self.bb_indicator = self.bb('),
            (r'self\.atr\s*=\s*self\.atr\(', 'self.atr_indicator = self.atr('),
            # Dict then method call: self.rsi = {} ... self.rsi[x] = self.rsi(...)
            (r'self\.rsi\s*=\s*\{\}', 'self.rsi_indicators = {}'),
            (r'self\.sma\s*=\s*\{\}', 'self.sma_indicators = {}'),
            (r'self\.ema\s*=\s*\{\}', 'self.ema_indicators = {}'),
            # Fix references to renamed dicts
            (r'self\.rsi\[', 'self.rsi_indicators['),
            (r'self\.sma\[', 'self.sma_indicators['),
            (r'self\.ema\[', 'self.ema_indicators['),
        ]
        for pattern, replacement in indicator_shadowing_fixes:
            code = re.sub(pattern, replacement, code)

        return code

    def _calculate_periods(self, entry) -> Dict[str, str]:
        """
        Calculate IS/OOS periods based on data availability.

        Adjusts date ranges based on asset class:
        - Crypto: Data typically starts 2015-2017, use 2017-2021 for IS
        - Equities: Use standard 2010-2019 for IS
        """
        # Check if entry involves crypto assets
        is_crypto = self._is_crypto_strategy(entry)

        if is_crypto:
            # Crypto data is limited - most coins have data from 2017+
            return {
                "is_start": "2017-01-01",
                "is_end": "2021-12-31",
                "oos_start": "2022-01-01",
                "oos_end": "2024-12-15"
            }
        else:
            # Standard equity/futures periods
            return {
                "is_start": "2010-01-01",
                "is_end": "2019-12-31",
                "oos_start": "2020-01-01",
                "oos_end": "2024-12-15"
            }

    def _is_crypto_strategy(self, entry) -> bool:
        """
        Detect if an entry involves cryptocurrency assets.

        Checks name, summary, hypothesis, and tags for crypto indicators.
        """
        crypto_keywords = [
            "crypto", "bitcoin", "btc", "ethereum", "eth", "solana", "sol",
            "binance", "coinbase", "defi", "blockchain", "altcoin", "token",
            "btcusd", "ethusd", "cryptocurrency"
        ]

        # Check all text fields
        text_to_check = " ".join([
            entry.name or "",
            entry.summary or "",
            entry.hypothesis or "",
            " ".join(entry.tags or [])
        ]).lower()

        return any(keyword in text_to_check for keyword in crypto_keywords)

    def _run_backtest(self, code: str, start_date: str, end_date: str, entry_id: str = "temp") -> BacktestResult:
        """
        Run a backtest via the lean CLI.

        Uses cloud backtest by default (has full data access).
        Falls back to local with --download-data if cloud fails.
        Includes retry logic for rate limiting errors.
        """
        import time
        max_retries = 3
        retry_delay = 30  # seconds

        for attempt in range(max_retries):
            try:
                # Use unique project name with timestamp to avoid cloud naming conflicts
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                project_name = f"{entry_id}_{start_date[:4]}_{end_date[:4]}_{timestamp}"
                project_dir = self.workspace.validations_path / entry_id / project_name
                project_dir.mkdir(parents=True, exist_ok=True)

                # Write the algorithm code
                main_py = project_dir / "main.py"
                modified_code = self._inject_dates(code, start_date, end_date)
                main_py.write_text(modified_code)

                # Create config.json for lean
                config = {
                    "algorithm-language": "Python",
                    "parameters": {}
                }
                config_file = project_dir / "config.json"
                config_file.write_text(json.dumps(config))

                # Build command based on mode
                if self.use_local:
                    # Local Docker backtest with data download from QC
                    cmd = ["lean", "backtest", str(project_dir), "--download-data"]
                    # Find lean.json for local config
                    lean_config = self.workspace.path / "lean.json"
                    if lean_config.exists():
                        cmd.extend(["--lean-config", str(lean_config)])
                else:
                    # Cloud backtest (has full data access)
                    # --push uploads the project, no --open to avoid browser popup
                    cmd = ["lean", "cloud", "backtest", str(project_dir), "--push"]

                logger.info(f"Running: {' '.join(cmd)}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=900 if self.use_local else 600,  # Local Docker may need more time
                    cwd=str(self.workspace.path)  # Run from workspace root
                )

                # Debug: save raw output for troubleshooting
                debug_file = self.workspace.validations_path / entry_id / "last_lean_output.txt"
                try:
                    debug_file.write_text(f"=== RETURNCODE: {result.returncode} ===\n\n=== STDOUT ===\n{result.stdout}\n\n=== STDERR ===\n{result.stderr}")
                except Exception:
                    pass

                # Check for rate limiting / no spare nodes error - retry if so
                if "no spare nodes" in result.stdout.lower() or "no spare nodes" in result.stderr.lower():
                    if attempt < max_retries - 1:
                        logger.warning(f"QC rate limit hit, waiting {retry_delay}s before retry {attempt + 2}/{max_retries}")
                        # Clean up before retry
                        try:
                            shutil.rmtree(project_dir)
                        except Exception:
                            pass
                        time.sleep(retry_delay)
                        continue
                    else:
                        return BacktestResult(
                            success=False,
                            error="QC rate limit: no spare nodes available after retries",
                            raw_output=result.stdout
                        )

                # Parse results from output
                backtest_result = self._parse_lean_output(result.stdout, result.stderr, result.returncode)

                # Clean up timestamped project folder (keep main validation folder clean)
                try:
                    shutil.rmtree(project_dir)
                except Exception as cleanup_error:
                    logger.debug(f"Failed to clean up {project_dir}: {cleanup_error}")

                return backtest_result

            except subprocess.TimeoutExpired:
                return BacktestResult(success=False, error="Backtest timed out")
            except Exception as e:
                return BacktestResult(success=False, error=str(e))

        # Should not reach here, but just in case
        return BacktestResult(success=False, error="Backtest failed after all retries")

    def _inject_dates(self, code: str, start_date: str, end_date: str) -> str:
        """Inject start/end dates into the algorithm code."""
        # Parse dates
        start_parts = start_date.split("-")
        end_parts = end_date.split("-")

        # Look for SetStartDate and SetEndDate calls and replace them
        import re

        # Replace SetStartDate
        code = re.sub(
            r'self\.SetStartDate\([^)]+\)',
            f'self.SetStartDate({start_parts[0]}, {int(start_parts[1])}, {int(start_parts[2])})',
            code
        )

        # Replace SetEndDate
        code = re.sub(
            r'self\.SetEndDate\([^)]+\)',
            f'self.SetEndDate({end_parts[0]}, {int(end_parts[1])}, {int(end_parts[2])})',
            code
        )

        return code

    def _parse_lean_output(self, stdout: str, stderr: str, returncode: int) -> BacktestResult:
        """Parse lean CLI output to extract backtest results.

        Uses QC API to fetch reliable JSON statistics instead of parsing table output.
        """
        if returncode != 0:
            # Include both stdout and stderr in error - lean often puts errors in stdout
            error_details = stderr or stdout[:500] if stdout else "No output"
            return BacktestResult(
                success=False,
                error=f"Lean exited with code {returncode}: {error_details}",
                raw_output=stdout
            )

        # Check for runtime errors in the output (even with exit code 0)
        if "An error occurred during this backtest:" in stdout:
            error_match = re.search(r"An error occurred during this backtest:\s*(.+?)(?:\s+at\s+|$)", stdout, re.DOTALL)
            error_msg = error_match.group(1).strip() if error_match else "Unknown runtime error"
            return BacktestResult(
                success=False,
                error=f"Backtest runtime error: {error_msg}",
                raw_output=stdout
            )

        # Extract project ID and backtest ID from output
        project_id, backtest_id = self._extract_backtest_ids(stdout)

        if not project_id or not backtest_id:
            # Fallback to table parsing if we can't extract IDs
            return self._parse_lean_output_table(stdout)

        # Fetch results from QC API (more reliable than parsing table)
        try:
            stats = self._fetch_backtest_stats(project_id, backtest_id)
            if stats:
                # Parse percentage strings like "10.127%" to floats
                def parse_pct(s):
                    if isinstance(s, (int, float)):
                        return float(s)
                    if isinstance(s, str):
                        return float(s.replace('%', '').replace('$', '').replace(',', ''))
                    return 0.0

                cagr = parse_pct(stats.get("Compounding Annual Return", 0)) / 100
                sharpe = parse_pct(stats.get("Sharpe Ratio", 0))
                drawdown = parse_pct(stats.get("Drawdown", 0)) / 100
                alpha = parse_pct(stats.get("Alpha", 0))
                total_return = parse_pct(stats.get("Net Profit", 0)) / 100

                return BacktestResult(
                    success=True,
                    cagr=cagr,
                    sharpe=sharpe,
                    max_drawdown=abs(drawdown),
                    alpha=alpha,
                    total_return=total_return,
                    benchmark_cagr=0.10,
                    raw_output=stdout
                )
        except Exception as e:
            logger.warning(f"API fetch failed, falling back to table parsing: {e}")

        # Fallback to table parsing
        return self._parse_lean_output_table(stdout)

    def _extract_backtest_ids(self, stdout: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract project ID and backtest ID from lean output."""
        # Look for: Project ID: 27018367
        # Look for: Backtest id: 205d98ce63238f18187f9da04186e199
        project_match = re.search(r"Project ID:\s*(\d+)", stdout)
        backtest_match = re.search(r"Backtest id:\s*([a-f0-9]+)", stdout)

        project_id = project_match.group(1) if project_match else None
        backtest_id = backtest_match.group(1) if backtest_match else None

        return project_id, backtest_id

    def _fetch_backtest_stats(self, project_id: str, backtest_id: str) -> Optional[Dict[str, Any]]:
        """Fetch backtest statistics from QC API."""
        # Load credentials from ~/.lean/credentials
        creds_file = Path.home() / ".lean" / "credentials"
        if not creds_file.exists():
            logger.warning("No QC credentials found at ~/.lean/credentials")
            return None

        try:
            creds = json.loads(creds_file.read_text())
            user_id = creds.get("user-id")
            api_token = creds.get("api-token")

            if not user_id or not api_token:
                return None

            # QC API requires timestamp and hash
            timestamp = str(int(time.time()))
            hash_data = f"{api_token}:{timestamp}"
            hash_value = hashlib.sha256(hash_data.encode()).hexdigest()

            # Build request
            params = urllib.parse.urlencode({"projectId": project_id, "backtestId": backtest_id})
            url = f"https://www.quantconnect.com/api/v2/backtests/read?{params}"

            auth_string = f"{user_id}:{hash_value}"
            auth_bytes = base64.b64encode(auth_string.encode()).decode()

            request = urllib.request.Request(url)
            request.add_header("Authorization", f"Basic {auth_bytes}")
            request.add_header("Timestamp", timestamp)

            response = urllib.request.urlopen(request, timeout=30)
            data = json.loads(response.read().decode())

            if data.get("success"):
                return data.get("backtest", {}).get("statistics", {})
            else:
                logger.warning(f"QC API error: {data.get('errors', [])}")
                return None

        except Exception as e:
            logger.warning(f"Failed to fetch from QC API: {e}")
            return None

    def _parse_lean_output_table(self, stdout: str) -> BacktestResult:
        """Fallback: Parse lean CLI table output to extract backtest results."""
        try:
            # Extract metrics from the table format
            cagr = self._extract_table_metric(stdout, "Compounding Annual", None)
            sharpe = self._extract_table_metric(stdout, "Sharpe Ratio", None)
            drawdown = self._extract_table_metric(stdout, "Drawdown", None)
            alpha = self._extract_table_metric(stdout, "Alpha", None)
            total_return = self._extract_table_metric(stdout, "Return", None)

            # Check if we got any valid metrics
            if cagr is None or sharpe is None:
                return BacktestResult(
                    success=False,
                    error="Could not parse backtest results from output",
                    raw_output=stdout
                )

            # If alpha wasn't found, estimate from CAGR vs benchmark
            if alpha is None and cagr is not None:
                alpha = cagr - 0.10

            return BacktestResult(
                success=True,
                cagr=cagr or 0.0,
                sharpe=sharpe or 0.0,
                max_drawdown=abs(drawdown) if drawdown else 0.0,
                alpha=alpha or 0.0,
                total_return=total_return or 0.0,
                benchmark_cagr=0.10,
                raw_output=stdout
            )
        except Exception as e:
            return BacktestResult(
                success=False,
                error=f"Failed to parse results: {e}",
                raw_output=stdout
            )

    def _extract_table_metric(self, output: str, metric_name: str, default: Optional[float]) -> Optional[float]:
        """Extract a metric value from lean table output format."""
        import re

        # Try multiple patterns for table format
        # Pattern 1: │ Metric Name │ Value │ (with possible whitespace)
        patterns = [
            # Table format with │ separators - value followed by optional %
            rf"│\s*{re.escape(metric_name)}\s*│\s*([+-]?\d+\.?\d*)\s*%",
            # Table format without %
            rf"│\s*{re.escape(metric_name)}\s*│\s*([+-]?\d+\.?\d*)\s*│",
            # Simpler format: Metric Name │ Value
            rf"{re.escape(metric_name)}\s*│\s*([+-]?\d+\.?\d*)\s*%?",
            # Key-value format: Metric Name: Value
            rf"{re.escape(metric_name)}[:\s]+([+-]?\d+\.?\d*)\s*%?",
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
            if match:
                value = float(match.group(1))
                # Check if it's a percentage (look for % in the matched region)
                matched_text = output[match.start():match.end()+5]
                if "%" in matched_text:
                    value /= 100
                return value

        return default

    def _check_is_gates(self, results: BacktestResult) -> tuple[bool, str]:
        """Check if IS results pass the gates."""
        if results.alpha is not None and results.alpha < self.IS_MIN_ALPHA:
            return False, f"Alpha {results.alpha*100:.1f}% < {self.IS_MIN_ALPHA*100:.0f}% minimum"
        return True, "Passed"

    def _check_oos_gates(self, results: BacktestResult) -> tuple[bool, str]:
        """Check if OOS results pass the gates."""
        failures = []

        if results.alpha is not None and results.alpha < self.OOS_MIN_ALPHA:
            failures.append(f"Alpha {results.alpha*100:.1f}% < {self.OOS_MIN_ALPHA*100:.0f}%")

        if results.sharpe is not None and results.sharpe < self.OOS_MIN_SHARPE:
            failures.append(f"Sharpe {results.sharpe:.2f} < {self.OOS_MIN_SHARPE}")

        if results.max_drawdown is not None and results.max_drawdown > self.OOS_MAX_DRAWDOWN:
            failures.append(f"Drawdown {results.max_drawdown*100:.1f}% > {self.OOS_MAX_DRAWDOWN*100:.0f}%")

        if failures:
            return False, ", ".join(failures)
        return True, "Passed"

    def _run_expert_review(self, entry, is_results: BacktestResult, oos_results: Optional[BacktestResult]) -> List[ExpertReview]:
        """Run expert review using multiple personas."""
        if not self.llm_client:
            logger.warning("No LLM client - skipping expert review")
            return []

        # Import persona runner
        try:
            from agents.runner import PersonaRunner
            runner = PersonaRunner(self.llm_client)

            # Determine which results to use (prefer OOS, fall back to IS)
            results = oos_results if oos_results else is_results
            test_type = "oos" if oos_results else "is"

            # Build validation results in the format expected by prompt templates
            # Template expects flat keys like sharpe_ratio, alpha, cagr, etc.
            validation_results = {
                # Component info
                "component_name": entry.name,
                "component_type": entry.type if hasattr(entry, 'type') else "strategy",
                "hypothesis": entry.hypothesis if hasattr(entry, 'hypothesis') else (entry.summary if hasattr(entry, 'summary') else "N/A"),

                # Test configuration
                "test_type": test_type,
                "start_date": "2010-01-01",  # From _calculate_periods
                "end_date": "2024-12-15",
                "base_strategy": "SPY Buy & Hold",
                "filter_config": "N/A",

                # Performance metrics (as percentages for display)
                "sharpe_ratio": f"{results.sharpe:.2f}" if results and results.sharpe else "N/A",
                "alpha": f"{results.alpha * 100:.1f}" if results and results.alpha else "N/A",
                "cagr": f"{results.cagr * 100:.1f}" if results and results.cagr else "N/A",
                "max_drawdown": f"{results.max_drawdown * 100:.1f}" if results and results.max_drawdown else "N/A",
                "total_trades": "N/A",  # Not available from current backtest
                "win_rate": "N/A",

                # Comparison to baseline (estimate vs SPY ~10% CAGR)
                "baseline_sharpe": "0.50",
                "sharpe_improvement": f"{(results.sharpe - 0.5):.2f}" if results and results.sharpe else "N/A",
                "baseline_max_dd": "55.0",  # SPY 2008 drawdown
                "drawdown_improvement": f"{55.0 - (results.max_drawdown * 100):.1f}" if results and results.max_drawdown else "N/A",

                # Include IS vs OOS comparison if both available
                "is_sharpe": f"{is_results.sharpe:.2f}" if is_results and is_results.sharpe else "N/A",
                "is_cagr": f"{is_results.cagr * 100:.1f}" if is_results and is_results.cagr else "N/A",
                "oos_sharpe": f"{oos_results.sharpe:.2f}" if oos_results and oos_results.sharpe else "N/A",
                "oos_cagr": f"{oos_results.cagr * 100:.1f}" if oos_results and oos_results.cagr else "N/A",

                # Statistical analysis (not available, provide placeholders)
                "p_value": "N/A",
                "bonferroni_p": "N/A",
                "n_tests": "1",
                "is_significant": "Not tested",
                "effect_size": "N/A",

                # Regime results (not available)
                "regime_results": [],

                # Sanity flags
                "sanity_flags": [],
            }

            # Run analysis with all personas
            analysis_result = runner.run_analysis(entry.id, validation_results, include_suggestions=True)

            # Convert to ExpertReview objects
            reviews = []
            for persona, response in analysis_result.responses.items():
                if response.structured_response:
                    sr = response.structured_response

                    # Handle different output formats from different personas
                    if persona == "mad-genius":
                        # Mad-genius has creative_modifications, unconventional_uses, etc.
                        improvements = []
                        for mod in sr.get("creative_modifications", []):
                            if isinstance(mod, dict):
                                improvements.append(f"{mod.get('idea', '')}: {mod.get('rationale', '')}")
                            else:
                                improvements.append(str(mod))
                        for use in sr.get("unconventional_uses", []):
                            if isinstance(use, dict):
                                improvements.append(f"{use.get('use_case', '')}: {use.get('example', '')}")
                        improvements.extend(sr.get("next_experiments", []))

                        # Get moonshot as a derived idea
                        moonshot = sr.get("moonshot_variation", {})
                        derived = []
                        if moonshot and isinstance(moonshot, dict):
                            derived.append(f"Moonshot: {moonshot.get('description', '')}")
                        for combo in sr.get("combination_ideas", []):
                            if isinstance(combo, dict):
                                derived.append(f"Combine with {combo.get('pair_with', '')}: {combo.get('synergy', '')}")

                        reviews.append(ExpertReview(
                            persona=persona,
                            assessment=sr.get("overall_assessment", sr.get("hidden_potential", "N/A")),
                            concerns=sr.get("edge_cases_to_exploit", []),
                            improvements=improvements[:5],  # Limit to top 5
                            derived_ideas=derived[:3]  # Limit to top 3
                        ))

                    elif persona == "quant-researcher":
                        # Quant-researcher outputs: verdict, methodology_critique, recommendations
                        reviews.append(ExpertReview(
                            persona=persona,
                            assessment=sr.get("verdict", sr.get("scientific_validity", "N/A")),
                            concerns=sr.get("methodology_critique", []),
                            improvements=sr.get("recommendations", []),
                            derived_ideas=[]
                        ))

                    elif persona == "contrarian":
                        # Contrarian outputs: dissent_level, challenges_to_consensus, bear_case
                        concerns = []
                        # Extract challenges
                        for challenge in sr.get("challenges_to_consensus", []):
                            if isinstance(challenge, dict):
                                concerns.append(f"{challenge.get('claim', '')}: {challenge.get('challenge', '')}")
                            else:
                                concerns.append(str(challenge))
                        # Add bear case
                        bear_case = sr.get("bear_case", {})
                        if isinstance(bear_case, dict) and bear_case.get("primary_failure_mode"):
                            concerns.append(f"Bear case: {bear_case.get('primary_failure_mode', '')}")

                        # Extract what would change mind as improvements
                        improvements = sr.get("what_would_change_my_mind", [])

                        # Get final verdict
                        final = sr.get("final_verdict", sr.get("final_dissent", {}))
                        if isinstance(final, dict):
                            assessment = f"{sr.get('dissent_level', 'N/A')} dissent - {'proceed' if final.get('proceed') else 'do not proceed'}"
                        else:
                            assessment = sr.get("dissent_level", "N/A")

                        reviews.append(ExpertReview(
                            persona=persona,
                            assessment=assessment,
                            concerns=concerns[:5],
                            improvements=improvements[:3],
                            derived_ideas=[]
                        ))

                    elif persona == "report-synthesizer":
                        # Report-synthesizer outputs: final_determination, consensus_points, areas_of_disagreement
                        final_det = sr.get("final_determination", {})
                        if isinstance(final_det, dict):
                            assessment = final_det.get("status", sr.get("integrated_assessment", {}).get("overall_verdict", "N/A"))
                        else:
                            assessment = "N/A"

                        # Extract consensus points
                        consensus = []
                        for point in sr.get("consensus_points", []):
                            if isinstance(point, dict):
                                consensus.append(point.get("point", str(point)))
                            else:
                                consensus.append(str(point))

                        # Extract disagreements as concerns
                        concerns = []
                        for disagreement in sr.get("areas_of_disagreement", []):
                            if isinstance(disagreement, dict):
                                concerns.append(f"{disagreement.get('topic', '')}: {disagreement.get('resolution', '')}")
                            else:
                                concerns.append(str(disagreement))

                        # Recommended actions as improvements
                        improvements = []
                        for action in sr.get("recommended_actions", []):
                            if isinstance(action, dict):
                                improvements.append(action.get("action", str(action)))
                            else:
                                improvements.append(str(action))

                        reviews.append(ExpertReview(
                            persona=persona,
                            assessment=assessment,
                            concerns=concerns[:5],
                            improvements=improvements[:3],
                            derived_ideas=consensus[:3]  # Use consensus points as derived insights
                        ))

                    else:
                        # Standard format for momentum-trader and risk-manager
                        reviews.append(ExpertReview(
                            persona=persona,
                            assessment=sr.get("overall_assessment", "N/A"),
                            concerns=sr.get("concerns", sr.get("key_concerns", [])),
                            improvements=sr.get("next_steps_recommendations", []),
                            derived_ideas=sr.get("combination_suggestions", [])
                        ))
                elif response.raw_response:
                    # Fallback: use raw response when JSON parsing failed
                    # Extract first paragraph as assessment
                    raw = response.raw_response.strip()
                    assessment = raw[:500] + "..." if len(raw) > 500 else raw
                    reviews.append(ExpertReview(
                        persona=persona,
                        assessment=assessment,
                        concerns=[],
                        improvements=[],
                        derived_ideas=[]
                    ))

            return reviews

        except ImportError:
            logger.warning("Persona runner not available - using simplified review")
            return self._simplified_expert_review(entry, is_results, oos_results)
        except Exception as e:
            logger.warning(f"Expert review failed: {e} - using simplified review")
            return self._simplified_expert_review(entry, is_results, oos_results)

    def _simplified_expert_review(self, entry, is_results, oos_results) -> List[ExpertReview]:
        """Simplified expert review when full persona system not available."""
        reviews = []

        # Risk manager perspective
        if oos_results and oos_results.max_drawdown and oos_results.max_drawdown > 0.30:
            reviews.append(ExpertReview(
                persona="risk-manager",
                assessment=f"High drawdown ({oos_results.max_drawdown*100:.1f}%) is concerning",
                concerns=[f"Max drawdown of {oos_results.max_drawdown*100:.1f}% exceeds comfort level"],
                improvements=["Consider adding drawdown protection", "Add position sizing limits"]
            ))

        # Quant researcher perspective
        if is_results and oos_results:
            alpha_decay = (is_results.alpha or 0) - (oos_results.alpha or 0)
            if alpha_decay > 0.05:
                reviews.append(ExpertReview(
                    persona="quant-researcher",
                    assessment=f"Significant alpha decay ({alpha_decay*100:.1f}%) between IS and OOS",
                    concerns=["Possible overfitting to IS period", "Strategy may not be robust"],
                    improvements=["Test with different parameter ranges", "Check for regime sensitivity"]
                ))

        return reviews

    def _build_review_context(self, entry, is_results, oos_results) -> str:
        """Build context string for expert review."""
        context = f"""
Entry: {entry.id}
Name: {entry.name}
Hypothesis: {entry.hypothesis}

IN-SAMPLE RESULTS:
- CAGR: {is_results.cagr*100:.1f}%
- Sharpe: {is_results.sharpe:.2f}
- Max Drawdown: {is_results.max_drawdown*100:.1f}%
- Alpha: {is_results.alpha*100:.1f}%
"""

        if oos_results:
            context += f"""
OUT-OF-SAMPLE RESULTS:
- CAGR: {oos_results.cagr*100:.1f}%
- Sharpe: {oos_results.sharpe:.2f}
- Max Drawdown: {oos_results.max_drawdown*100:.1f}%
- Alpha: {oos_results.alpha*100:.1f}%

Alpha Decay: {(is_results.alpha - oos_results.alpha)*100:.1f}%
"""

        return context

    def _extract_derived_ideas(self, reviews: List[ExpertReview]) -> List[str]:
        """Extract derived ideas from expert reviews."""
        ideas = []
        for review in reviews:
            ideas.extend(review.improvements[:2])  # Take top 2 improvements per reviewer
        return list(set(ideas))[:5]  # Dedupe and limit to 5

    def _add_derived_ideas(self, parent_entry, ideas: List[str]):
        """Add derived ideas to the catalog."""
        for idea in ideas:
            try:
                self.catalog.add_derived(
                    parent_id=parent_entry.id,
                    name=f"{parent_entry.name} - {idea[:50]}",
                    hypothesis=idea,
                    entry_type="idea"
                )
            except Exception as e:
                logger.warning(f"Failed to add derived idea: {e}")

    def _update_entry_status(self, entry_id: str, determination: str):
        """Update the entry status in the catalog."""
        try:
            self.catalog.update_status(entry_id, determination)
        except Exception as e:
            logger.warning(f"Failed to update entry status: {e}")

    def _save_results(self, entry_id: str, is_results, oos_results, reviews, determination):
        """Save all results to the validations folder."""
        val_dir = self.workspace.validations_path / entry_id
        val_dir.mkdir(parents=True, exist_ok=True)

        # Save IS results
        if is_results:
            is_file = val_dir / "is_results.json"
            is_file.write_text(json.dumps({
                "success": is_results.success,
                "cagr": is_results.cagr,
                "sharpe": is_results.sharpe,
                "max_drawdown": is_results.max_drawdown,
                "alpha": is_results.alpha
            }, indent=2))

        # Save OOS results
        if oos_results:
            oos_file = val_dir / "oos_results.json"
            oos_file.write_text(json.dumps({
                "success": oos_results.success,
                "cagr": oos_results.cagr,
                "sharpe": oos_results.sharpe,
                "max_drawdown": oos_results.max_drawdown,
                "alpha": oos_results.alpha
            }, indent=2))

        # Save expert reviews
        if reviews:
            reviews_file = val_dir / "expert_reviews.json"
            reviews_file.write_text(json.dumps([
                {
                    "persona": r.persona,
                    "assessment": r.assessment,
                    "concerns": r.concerns,
                    "improvements": r.improvements
                }
                for r in reviews
            ], indent=2))

        # Save determination
        determination_file = val_dir / "determination.json"
        determination_file.write_text(json.dumps({
            "entry_id": entry_id,
            "determination": determination,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }, indent=2))
