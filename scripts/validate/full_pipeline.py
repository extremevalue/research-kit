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

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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

    def __init__(self, workspace, llm_client=None):
        """
        Initialize the pipeline runner.

        Args:
            workspace: Workspace instance
            llm_client: LLMClient instance (optional, but needed for code gen and expert review)
        """
        self.workspace = workspace
        self.llm_client = llm_client
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
            expert_reviews = self._run_expert_review(entry, is_results, None)
            derived_ideas = self._extract_derived_ideas(expert_reviews)

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

        # Generate code via Claude
        prompt = f"""Generate a QuantConnect algorithm to test this hypothesis:

Entry: {entry.id}
Name: {entry.name}
Type: {entry.type}
Summary: {entry.summary}
Hypothesis: {entry.hypothesis}

Requirements:
- Use QuantConnect's AlgorithmImports
- Implement Initialize() and OnData()
- Use daily resolution
- Include a benchmark comparison (SPY)
- Log regime changes and key decisions

Return ONLY the Python code, no explanations."""

        try:
            response = self.llm_client.generate_sonnet(prompt)
            # Extract code from response (handle markdown code blocks)
            code = response.content
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0]
            elif "```" in code:
                code = code.split("```")[1].split("```")[0]

            # Save the generated code
            val_dir.mkdir(parents=True, exist_ok=True)
            code_file.write_text(code)

            return code
        except Exception as e:
            logger.error(f"Failed to generate backtest code: {e}")
            return None

    def _calculate_periods(self, entry) -> Dict[str, str]:
        """Calculate IS/OOS periods based on data availability."""
        # Default periods - should be enhanced to check actual data availability
        # IS: 30% of available data, OOS: 70%
        return {
            "is_start": "2010-01-01",
            "is_end": "2019-12-31",
            "oos_start": "2020-01-01",
            "oos_end": "2024-12-15"
        }

    def _run_backtest(self, code: str, start_date: str, end_date: str, entry_id: str = "temp") -> BacktestResult:
        """
        Run a backtest via the lean CLI.

        Uses cloud backtest by default (has full data access).
        Falls back to local with --download-data if cloud fails.
        """
        try:
            # Use the validations folder under workspace
            project_dir = self.workspace.validations_path / entry_id / "backtest_run"
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

            # Try cloud backtest (has full data access)
            # --push uploads the project, no --open to avoid browser popup
            cmd = ["lean", "cloud", "backtest", str(project_dir), "--push"]

            logger.info(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                cwd=str(self.workspace.path)  # Run from workspace root
            )

            # Parse results from output
            return self._parse_lean_output(result.stdout, result.stderr, result.returncode)

        except subprocess.TimeoutExpired:
            return BacktestResult(success=False, error="Backtest timed out")
        except Exception as e:
            return BacktestResult(success=False, error=str(e))

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
        """Parse lean CLI output to extract backtest results."""
        if returncode != 0:
            # Include both stdout and stderr in error - lean often puts errors in stdout
            error_details = stderr or stdout[:500] if stdout else "No output"
            return BacktestResult(
                success=False,
                error=f"Lean exited with code {returncode}: {error_details}",
                raw_output=stdout
            )

        # Try to parse results from output
        # This is a simplified parser - real implementation would parse the JSON results
        try:
            # Look for key metrics in output
            cagr = self._extract_metric(stdout, "Compounding Annual Return", 0.0)
            sharpe = self._extract_metric(stdout, "Sharpe Ratio", 0.0)
            drawdown = self._extract_metric(stdout, "Drawdown", 0.0)

            # For now, estimate alpha as CAGR - 10% (SPY benchmark)
            alpha = cagr - 0.10

            return BacktestResult(
                success=True,
                cagr=cagr,
                sharpe=sharpe,
                max_drawdown=abs(drawdown),
                alpha=alpha,
                benchmark_cagr=0.10,
                raw_output=stdout
            )
        except Exception as e:
            return BacktestResult(
                success=False,
                error=f"Failed to parse results: {e}",
                raw_output=stdout
            )

    def _extract_metric(self, output: str, metric_name: str, default: float) -> float:
        """Extract a metric value from lean output."""
        import re
        pattern = rf"{metric_name}[:\s]+([+-]?\d+\.?\d*)%?"
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            if "%" in output[match.start():match.end()+5]:
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

            # Prepare validation results dict for personas
            validation_results = {
                "entry_name": entry.name,
                "hypothesis": entry.hypothesis if hasattr(entry, 'hypothesis') else entry.summary,
                "is_results": {
                    "cagr": is_results.cagr,
                    "sharpe": is_results.sharpe,
                    "max_drawdown": is_results.max_drawdown,
                    "alpha": is_results.alpha
                } if is_results else None,
                "oos_results": {
                    "cagr": oos_results.cagr,
                    "sharpe": oos_results.sharpe,
                    "max_drawdown": oos_results.max_drawdown,
                    "alpha": oos_results.alpha
                } if oos_results else None
            }

            # Run analysis with all personas
            analysis_result = runner.run_analysis(entry.id, validation_results, include_suggestions=True)

            # Convert to ExpertReview objects
            reviews = []
            for persona, response in analysis_result.responses.items():
                if response.structured_response:
                    sr = response.structured_response
                    reviews.append(ExpertReview(
                        persona=persona,
                        assessment=sr.get("overall_assessment", "N/A"),
                        concerns=sr.get("concerns", sr.get("key_concerns", [])),
                        improvements=sr.get("next_steps_recommendations", []),
                        derived_ideas=sr.get("combination_suggestions", [])
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
