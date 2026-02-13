"""Backtest execution infrastructure for V4 validation.

This module provides backtest execution capabilities:
- BacktestResult: Results from a backtest run
- BacktestExecutor: Execute backtests via LEAN CLI (local or cloud)
- WalkForwardResult: Aggregated results from walk-forward validation

Extracted from scripts/validate/full_pipeline.py for V4 integration.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import logging

logger = logging.getLogger(__name__)


# Patterns that indicate errors that might be fixable by LLM code correction
CORRECTABLE_ERROR_PATTERNS = [
    r"AttributeError:.*object has no attribute",
    r"AttributeError:.*has no attribute",
    r"NameError: name '.*' is not defined",
    r"TypeError: .*argument",
    r"TypeError: .*takes \d+ positional argument",
    r"IndexError: .*index out of range",
    r"KeyError:",
    r"No such option:",
    r"Resolution\.",
    r"DataNormalizationMode",
    r"has no attribute 'is_ready'",
    r"invalid syntax",
    r"unexpected keyword argument",
    r"missing \d+ required positional argument",
    r"object is not callable",
    r"object is not subscriptable",
    r"[Zz]ero trades executed",
]


@dataclass
class BacktestResult:
    """Results from a backtest run."""

    success: bool
    cagr: float | None = None
    sharpe: float | None = None
    max_drawdown: float | None = None
    alpha: float | None = None
    total_return: float | None = None
    win_rate: float | None = None
    total_trades: int | None = None
    benchmark_cagr: float | None = None
    error: str | None = None
    raw_output: str | None = None
    rate_limited: bool = False
    engine_crash: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "cagr": self.cagr,
            "sharpe": self.sharpe,
            "max_drawdown": self.max_drawdown,
            "alpha": self.alpha,
            "total_return": self.total_return,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "benchmark_cagr": self.benchmark_cagr,
            "error": self.error,
            "rate_limited": self.rate_limited,
            "engine_crash": self.engine_crash,
        }


@dataclass
class WalkForwardWindow:
    """Results from a single walk-forward window."""

    window_id: int
    start_date: str
    end_date: str
    result: BacktestResult


@dataclass
class WalkForwardResult:
    """Aggregated results from walk-forward validation."""

    strategy_id: str
    windows: list[WalkForwardWindow] = field(default_factory=list)
    mean_return: float | None = None
    median_return: float | None = None
    aggregate_sharpe: float | None = None
    aggregate_cagr: float | None = None
    max_drawdown: float | None = None
    consistency: float | None = None  # % of profitable windows
    determination: str = "PENDING"  # VALIDATED, INVALIDATED, BLOCKED, RETRY_LATER
    determination_reason: str = ""
    is_transient: bool = False  # True if failure is transient (rate limit, no nodes)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "strategy_id": self.strategy_id,
            "windows": [
                {
                    "window_id": w.window_id,
                    "start_date": w.start_date,
                    "end_date": w.end_date,
                    "result": w.result.to_dict(),
                }
                for w in self.windows
            ],
            "mean_return": self.mean_return,
            "median_return": self.median_return,
            "aggregate_sharpe": self.aggregate_sharpe,
            "aggregate_cagr": self.aggregate_cagr,
            "max_drawdown": self.max_drawdown,
            "consistency": self.consistency,
            "determination": self.determination,
            "determination_reason": self.determination_reason,
            "is_transient": self.is_transient,
            "timestamp": self.timestamp,
        }


class BacktestExecutor:
    """Execute backtests via LEAN CLI.

    Supports both local Docker execution and QuantConnect cloud execution.
    Cloud execution provides full data access but requires API credentials.
    """

    # All available walk-forward windows (5 rolling windows)
    ALL_WINDOWS = [
        ("2012-01-01", "2015-12-31"),
        ("2014-01-01", "2017-12-31"),
        ("2016-01-01", "2019-12-31"),
        ("2018-01-01", "2021-12-31"),
        ("2020-01-01", "2023-12-31"),
    ]

    # Default: 1 window (fastest iteration for single-node accounts)
    # Use --windows 2 for IS/OOS, --windows 5 for thorough validation
    DEFAULT_WINDOWS = [
        ("2012-01-01", "2023-12-31"),  # Full period
    ]

    # 2 windows: IS/OOS style
    TWO_WINDOWS = [
        ("2012-01-01", "2017-12-31"),  # In-sample period
        ("2018-01-01", "2023-12-31"),  # Out-of-sample period
    ]

    def __init__(
        self,
        workspace_path: Path,
        use_local: bool = False,
        cleanup_on_start: bool = True,
        num_windows: int = 1,
        timeout: int = 600,
        reuse_project: bool = True,
    ):
        """Initialize backtest executor.

        Args:
            workspace_path: Path to the V4 workspace
            use_local: If True, use local Docker; if False, use QC cloud
            cleanup_on_start: If True, clean up stuck backtests on init
            num_windows: Number of walk-forward windows (1, 2, or 5)
            timeout: Backtest execution timeout in seconds (default: 600)
            reuse_project: If True, reuse a single QC cloud project to avoid
                100/day project creation limit. Only applies to cloud mode.
        """
        self.workspace_path = Path(workspace_path)
        self.validations_path = self.workspace_path / "validations"
        self.use_local = use_local
        self.reuse_project = reuse_project and not use_local
        self.num_windows = num_windows
        self.timeout = timeout

        # Fixed project directory for reuse mode
        self._runner_project_dir = self.validations_path / "_runner"

        # Select windows based on num_windows
        if num_windows >= 5:
            self.windows = self.ALL_WINDOWS
        elif num_windows == 2:
            self.windows = self.TWO_WINDOWS
        else:
            self.windows = self.DEFAULT_WINDOWS

        if cleanup_on_start and not use_local:
            self._cleanup_all_stuck_backtests()

    def run_single(
        self,
        code: str,
        start_date: str,
        end_date: str,
        strategy_id: str = "temp",
    ) -> BacktestResult:
        """Execute a single backtest.

        Args:
            code: Python algorithm code
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            strategy_id: Strategy ID for file naming

        Returns:
            BacktestResult with metrics or error
        """
        if self.reuse_project:
            return self._run_single_reuse(code, start_date, end_date, strategy_id)
        return self._run_single_new_project(code, start_date, end_date, strategy_id)

    def _run_single_new_project(
        self,
        code: str,
        start_date: str,
        end_date: str,
        strategy_id: str,
    ) -> BacktestResult:
        """Execute a backtest by creating a new project each time (legacy mode)."""
        # Create project directory
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        project_name = f"{strategy_id}_{start_date[:4]}_{end_date[:4]}_{timestamp}"
        project_dir = self.validations_path / strategy_id / project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        # Write algorithm code with date injection
        main_py = project_dir / "main.py"
        modified_code = self._inject_dates(code, start_date, end_date)
        main_py.write_text(modified_code)

        # Create config.json
        config = {"algorithm-language": "Python", "parameters": {}}
        config_file = project_dir / "config.json"
        config_file.write_text(json.dumps(config))

        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = self._execute_backtest(project_dir, strategy_id, attempt, max_retries)
                if result is not None:
                    # Clean up project directory
                    self._cleanup_project(project_dir)
                    return result
            except Exception as e:
                if attempt == max_retries - 1:
                    self._cleanup_project(project_dir)
                    return BacktestResult(success=False, error=str(e))
                time.sleep(30)

        self._cleanup_project(project_dir)
        return BacktestResult(success=False, error="Backtest failed after all retries")

    def _run_single_reuse(
        self,
        code: str,
        start_date: str,
        end_date: str,
        strategy_id: str,
    ) -> BacktestResult:
        """Execute a backtest by reusing a single QC cloud project.

        This avoids the 100 projects/day creation limit by overwriting
        main.py in a fixed project directory each time.
        """
        project_dir = self._runner_project_dir
        project_dir.mkdir(parents=True, exist_ok=True)

        # Overwrite algorithm code with date injection
        main_py = project_dir / "main.py"
        modified_code = self._inject_dates(code, start_date, end_date)
        main_py.write_text(modified_code)

        # Ensure config.json exists
        config_file = project_dir / "config.json"
        if not config_file.exists():
            config = {"algorithm-language": "Python", "parameters": {}}
            config_file.write_text(json.dumps(config))

        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = self._execute_backtest(project_dir, strategy_id, attempt, max_retries)
                if result is not None:
                    # Do NOT clean up - we reuse this directory
                    return result
            except Exception as e:
                if attempt == max_retries - 1:
                    return BacktestResult(success=False, error=str(e))
                time.sleep(30)

        return BacktestResult(success=False, error="Backtest failed after all retries")

    def run_walk_forward(
        self,
        code: str,
        strategy_id: str,
        windows: list[tuple[str, str]] | None = None,
    ) -> WalkForwardResult:
        """Execute walk-forward validation with multiple time windows.

        Args:
            code: Python algorithm code
            strategy_id: Strategy ID
            windows: List of (start_date, end_date) tuples, or None for defaults

        Returns:
            WalkForwardResult with aggregated metrics
        """
        if windows is None:
            windows = self.windows

        wf_result = WalkForwardResult(strategy_id=strategy_id)
        total_windows = len(windows)

        for i, (start_date, end_date) in enumerate(windows):
            window_num = i + 1
            print(f"    Window {window_num}/{total_windows}: {start_date} to {end_date}...", end="", flush=True)
            logger.info(f"Running window {window_num}/{total_windows}: {start_date} to {end_date}")

            window_start = time.time()
            result = self.run_single(code, start_date, end_date, strategy_id)
            window_elapsed = time.time() - window_start

            # Print result on same line
            if result.success:
                print(f" done ({window_elapsed:.0f}s)")
            elif result.rate_limited:
                print(f" rate limited ({window_elapsed:.0f}s)")
            elif result.engine_crash:
                print(f" engine crash ({window_elapsed:.0f}s)")
            else:
                print(f" failed ({window_elapsed:.0f}s)")

            wf_result.windows.append(
                WalkForwardWindow(
                    window_id=i + 1,
                    start_date=start_date,
                    end_date=end_date,
                    result=result,
                )
            )

            # If rate limited, stop and retry later (transient - don't block)
            if result.rate_limited:
                wf_result.determination = "RETRY_LATER"
                wf_result.determination_reason = "Rate limited during walk-forward - retry when nodes available"
                wf_result.is_transient = True
                return wf_result

            # If engine crashed, mark as blocked (permanent - needs investigation)
            if result.engine_crash:
                wf_result.determination = "BLOCKED"
                wf_result.determination_reason = "LEAN engine crash"
                wf_result.is_transient = False
                return wf_result

        # Aggregate results
        self._aggregate_walk_forward_results(wf_result)
        return wf_result

    def _is_correctable_error(self, error: str) -> bool:
        """Check if error is potentially correctable by LLM.

        Args:
            error: Error message from backtest

        Returns:
            True if the error pattern suggests it could be fixed by code correction
        """
        if not error:
            return False

        for pattern in CORRECTABLE_ERROR_PATTERNS:
            if re.search(pattern, error, re.IGNORECASE):
                return True
        return False

    def run_single_with_correction(
        self,
        code: str,
        start_date: str,
        end_date: str,
        strategy_id: str,
        strategy: dict[str, Any],
        code_generator,
        max_attempts: int = 3,
    ) -> tuple[BacktestResult, int]:
        """Run backtest with automatic error correction.

        Attempts to run the backtest, and if it fails with a correctable error,
        uses the LLM to correct the code and retries.

        Args:
            code: Python algorithm code
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            strategy_id: Strategy ID for file naming
            strategy: Original strategy document (for correction context)
            code_generator: V4CodeGenerator instance with LLM client
            max_attempts: Maximum number of attempts (including original)

        Returns:
            Tuple of (BacktestResult, attempts_made)
        """
        current_code = code

        for attempt in range(1, max_attempts + 1):
            logger.info(f"Backtest attempt {attempt}/{max_attempts} for {strategy_id}")
            result = self.run_single(current_code, start_date, end_date, strategy_id)

            if result.success:
                return result, attempt

            # Check if we should try correction
            if attempt >= max_attempts:
                logger.info(f"Max attempts ({max_attempts}) reached for {strategy_id}")
                break

            error_msg = result.error or ""
            if not self._is_correctable_error(error_msg):
                logger.info(f"Error is not correctable: {error_msg[:100]}...")
                break

            # Skip correction for rate limiting or engine crashes
            if result.rate_limited or result.engine_crash:
                logger.info("Skipping correction for rate limit or engine crash")
                break

            # Attempt correction
            print(f" (correcting...)", end="", flush=True)
            logger.info(f"Attempting code correction for {strategy_id}")
            correction = code_generator.correct_code_error(
                current_code,
                error_msg,
                strategy,
                attempt=attempt,
            )

            if not correction.success:
                print(f" correction failed", flush=True)
                logger.warning(f"Code correction failed: {correction.error}")
                break

            current_code = correction.corrected_code
            print(f" retrying...", end="", flush=True)
            logger.info(f"Code corrected, retrying backtest (attempt {attempt + 1})")

        return result, attempt

    def run_walk_forward_with_correction(
        self,
        code: str,
        strategy_id: str,
        strategy: dict[str, Any],
        code_generator,
        windows: list[tuple[str, str]] | None = None,
        max_correction_attempts: int = 3,
    ) -> tuple[WalkForwardResult, int]:
        """Execute walk-forward validation with automatic error correction.

        For the first window, attempts correction if there's a correctable error.
        Subsequent windows use the (potentially corrected) code.

        Args:
            code: Python algorithm code
            strategy_id: Strategy ID
            strategy: Original strategy document
            code_generator: V4CodeGenerator instance with LLM client
            windows: List of (start_date, end_date) tuples, or None for defaults
            max_correction_attempts: Maximum correction attempts for first window

        Returns:
            Tuple of (WalkForwardResult, total_correction_attempts)
        """
        if windows is None:
            windows = self.windows

        wf_result = WalkForwardResult(strategy_id=strategy_id)
        current_code = code
        total_attempts = 1
        total_windows = len(windows)

        for i, (start_date, end_date) in enumerate(windows):
            window_num = i + 1
            print(f"    Window {window_num}/{total_windows}: {start_date} to {end_date}...", end="", flush=True)
            logger.info(f"Running window {window_num}/{total_windows}: {start_date} to {end_date}")

            window_start = time.time()

            # Only try correction on first window
            if i == 0:
                result, attempts = self.run_single_with_correction(
                    current_code,
                    start_date,
                    end_date,
                    strategy_id,
                    strategy,
                    code_generator,
                    max_attempts=max_correction_attempts,
                )
                total_attempts = attempts
            else:
                result = self.run_single(current_code, start_date, end_date, strategy_id)

            window_elapsed = time.time() - window_start

            # Print result on same line
            if result.success:
                print(f" done ({window_elapsed:.0f}s)")
            elif result.rate_limited:
                print(f" rate limited ({window_elapsed:.0f}s)")
            elif result.engine_crash:
                print(f" engine crash ({window_elapsed:.0f}s)")
            else:
                print(f" failed ({window_elapsed:.0f}s)")

            wf_result.windows.append(
                WalkForwardWindow(
                    window_id=i + 1,
                    start_date=start_date,
                    end_date=end_date,
                    result=result,
                )
            )

            # If rate limited, stop and retry later (transient - don't block)
            if result.rate_limited:
                wf_result.determination = "RETRY_LATER"
                wf_result.determination_reason = "Rate limited during walk-forward - retry when nodes available"
                wf_result.is_transient = True
                return wf_result, total_attempts

            # If engine crashed, mark as blocked (permanent - needs investigation)
            if result.engine_crash:
                wf_result.determination = "BLOCKED"
                wf_result.determination_reason = "LEAN engine crash"
                wf_result.is_transient = False
                return wf_result, total_attempts

        # Aggregate results
        self._aggregate_walk_forward_results(wf_result)
        return wf_result, total_attempts

    def _aggregate_walk_forward_results(self, wf_result: WalkForwardResult) -> None:
        """Calculate aggregate metrics from walk-forward windows."""
        successful_windows = [w for w in wf_result.windows if w.result.success]

        if not successful_windows:
            wf_result.determination = "BLOCKED"
            wf_result.determination_reason = "No successful backtest windows"
            return

        # Calculate returns
        returns = [w.result.cagr for w in successful_windows if w.result.cagr is not None]
        if returns:
            wf_result.mean_return = sum(returns) / len(returns)
            sorted_returns = sorted(returns)
            mid = len(sorted_returns) // 2
            wf_result.median_return = (
                sorted_returns[mid]
                if len(sorted_returns) % 2
                else (sorted_returns[mid - 1] + sorted_returns[mid]) / 2
            )

        # Calculate aggregate Sharpe
        sharpes = [w.result.sharpe for w in successful_windows if w.result.sharpe is not None]
        if sharpes:
            wf_result.aggregate_sharpe = sum(sharpes) / len(sharpes)

        # Calculate aggregate CAGR (mean of all window CAGRs)
        cagrs = [w.result.cagr for w in successful_windows if w.result.cagr is not None]
        if cagrs:
            wf_result.aggregate_cagr = sum(cagrs) / len(cagrs)

        # Max drawdown (worst across all windows)
        drawdowns = [w.result.max_drawdown for w in successful_windows if w.result.max_drawdown is not None]
        if drawdowns:
            wf_result.max_drawdown = max(drawdowns)

        # Consistency: % of windows with positive CAGR
        profitable = [1 for w in successful_windows if w.result.cagr and w.result.cagr > 0]
        wf_result.consistency = len(profitable) / len(successful_windows) if successful_windows else 0

    def _execute_backtest(
        self,
        project_dir: Path,
        strategy_id: str,
        attempt: int,
        max_retries: int,
    ) -> BacktestResult | None:
        """Execute the backtest command and handle the result."""
        # Check for lean.json config - required to avoid interactive prompts
        lean_config = self.workspace_path / "lean.json"
        if not lean_config.exists():
            return BacktestResult(
                success=False,
                error=f"No lean.json found. Run 'lean init' in your workspace directory to set up QuantConnect backtesting. See the README for details.",
            )

        # Build command
        if self.use_local:
            cmd = ["lean", "backtest", str(project_dir), "--download-data"]
            cmd.extend(["--lean-config", str(lean_config)])
        else:
            # Note: lean cloud backtest doesn't support --lean-config flag
            cmd = ["lean", "cloud", "backtest", str(project_dir), "--push"]

        logger.info(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            cwd=str(self.workspace_path),
        )

        # Save debug output
        debug_file = self.validations_path / strategy_id / "last_lean_output.txt"
        debug_file.parent.mkdir(parents=True, exist_ok=True)
        debug_file.write_text(
            f"=== RETURNCODE: {result.returncode} ===\n\n"
            f"=== STDOUT ===\n{result.stdout}\n\n"
            f"=== STDERR ===\n{result.stderr}"
        )

        # Check for rate limiting
        output_lower = (result.stdout + result.stderr).lower()
        rate_limit_patterns = ["no spare nodes", "rate limit", "too many", "throttl", "quota", "capacity limit", "maximum number of projects"]
        if any(pattern in output_lower for pattern in rate_limit_patterns):
            cleaned = self._cleanup_all_running_backtests()
            if cleaned > 0:
                time.sleep(30)
                return None  # Retry

            if attempt < max_retries - 1:
                time.sleep(60)
                return None  # Retry

            return BacktestResult(
                success=False,
                error="QC nodes unavailable - clean up stuck jobs",
                raw_output=result.stdout,
                rate_limited=True,
            )

        # Extract IDs and wait for completion if cloud
        if not self.use_local:
            project_id, backtest_id = self._extract_backtest_ids(result.stdout)
            if project_id and backtest_id:
                status = self._get_backtest_status(project_id, backtest_id)
                if status == "Running":
                    final_status = self._wait_for_backtest_completion(project_id, backtest_id)
                    if final_status == "Timeout":
                        self._delete_backtest(project_id, backtest_id)
                        if attempt < max_retries - 1:
                            return None  # Retry
                        return BacktestResult(
                            success=False,
                            error="Backtest timed out",
                            rate_limited=True,
                        )

        return self._parse_lean_output(result.stdout, result.stderr, result.returncode)

    def _inject_dates(self, code: str, start_date: str, end_date: str) -> str:
        """Inject start/end dates into algorithm code."""
        start_parts = start_date.split("-")
        end_parts = end_date.split("-")

        # Replace PascalCase
        code = re.sub(
            r"self\.SetStartDate\([^)]+\)",
            f"self.SetStartDate({start_parts[0]}, {int(start_parts[1])}, {int(start_parts[2])})",
            code,
        )
        code = re.sub(
            r"self\.SetEndDate\([^)]+\)",
            f"self.SetEndDate({end_parts[0]}, {int(end_parts[1])}, {int(end_parts[2])})",
            code,
        )

        # Replace snake_case
        code = re.sub(
            r"self\.set_start_date\([^)]+\)",
            f"self.set_start_date({start_parts[0]}, {int(start_parts[1])}, {int(start_parts[2])})",
            code,
        )
        code = re.sub(
            r"self\.set_end_date\([^)]+\)",
            f"self.set_end_date({end_parts[0]}, {int(end_parts[1])}, {int(end_parts[2])})",
            code,
        )

        return code

    def _parse_lean_output(self, stdout: str, stderr: str, returncode: int) -> BacktestResult:
        """Parse LEAN CLI output to extract backtest results."""
        combined_output = (stdout or "") + (stderr or "")

        # Check for engine crashes
        engine_crash_patterns = [
            "PAL_SEHException",
            "core dumped",
            "FATAL UNHANDLED EXCEPTION",
            "Aborted (core dumped)",
            "Segmentation fault",
        ]
        for pattern in engine_crash_patterns:
            if pattern in combined_output:
                return BacktestResult(
                    success=False,
                    error=f"LEAN engine crash: {pattern}",
                    raw_output=stdout,
                    engine_crash=True,
                )

        # Check for errors
        if returncode != 0:
            combined_lower = combined_output.lower()
            rate_limit_patterns = [
                "no spare nodes", "rate limit", "too many requests",
                "quota exceeded", "throttl", "capacity limit",
                "maximum number of projects",
            ]
            for pattern in rate_limit_patterns:
                if pattern in combined_lower:
                    return BacktestResult(
                        success=False,
                        error=f"Rate limited: {pattern}",
                        raw_output=stdout,
                        rate_limited=True,
                    )

            error_details = combined_output[-1000:] if len(combined_output) > 1000 else combined_output
            return BacktestResult(
                success=False,
                error=f"Lean exited with code {returncode}: {error_details}",
                raw_output=stdout,
            )

        # Check for runtime errors
        if "An error occurred during this backtest:" in stdout:
            error_match = re.search(r"An error occurred during this backtest:\s*(.+?)(?:\s+at\s+|$)", stdout, re.DOTALL)
            error_msg = error_match.group(1).strip() if error_match else "Unknown runtime error"
            return BacktestResult(
                success=False,
                error=f"Backtest runtime error: {error_msg}",
                raw_output=stdout,
            )

        # Try to get results from QC API
        project_id, backtest_id = self._extract_backtest_ids(stdout)
        if project_id and backtest_id:
            stats = self._fetch_backtest_stats(project_id, backtest_id)
            if stats:
                return self._parse_stats(stats, stdout)

        # Fallback to table parsing
        return self._parse_lean_output_table(stdout)

    def _parse_stats(self, stats: dict[str, Any], raw_output: str) -> BacktestResult:
        """Parse QC API statistics to BacktestResult."""
        def parse_pct(s: Any) -> float:
            if isinstance(s, (int, float)):
                return float(s)
            if isinstance(s, str):
                return float(s.replace("%", "").replace("$", "").replace(",", ""))
            return 0.0

        result = BacktestResult(
            success=True,
            cagr=parse_pct(stats.get("Compounding Annual Return", 0)) / 100,
            sharpe=parse_pct(stats.get("Sharpe Ratio", 0)),
            max_drawdown=abs(parse_pct(stats.get("Drawdown", 0))) / 100,
            alpha=parse_pct(stats.get("Alpha", 0)),
            total_return=parse_pct(stats.get("Net Profit", 0)) / 100,
            win_rate=parse_pct(stats.get("Win Rate", 0)) / 100 if stats.get("Win Rate") else None,
            total_trades=int(stats.get("Total Orders", 0)) if stats.get("Total Orders") else None,
            benchmark_cagr=0.10,
            raw_output=raw_output,
        )

        # Flag zero-trade backtests as failure
        if result.success and result.total_trades == 0:
            result.success = False
            result.error = "Zero trades executed - strategy logic may not match specification"

        return result

    def _parse_lean_output_table(self, stdout: str) -> BacktestResult:
        """Parse LEAN table output as fallback."""
        cagr = self._extract_table_metric(stdout, "Compounding Annual", None)
        sharpe = self._extract_table_metric(stdout, "Sharpe Ratio", None)
        drawdown = self._extract_table_metric(stdout, "Drawdown", None)
        alpha = self._extract_table_metric(stdout, "Alpha", None)
        total_return = self._extract_table_metric(stdout, "Return", None)

        if cagr is None or sharpe is None:
            return BacktestResult(
                success=False,
                error="Could not parse backtest results from output",
                raw_output=stdout,
            )

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
            raw_output=stdout,
        )

    def _extract_table_metric(self, output: str, metric_name: str, default: float | None) -> float | None:
        """Extract a metric value from LEAN table format."""
        patterns = [
            rf"│\s*{re.escape(metric_name)}\s*│\s*([+-]?\d+\.?\d*)\s*%",
            rf"│\s*{re.escape(metric_name)}\s*│\s*([+-]?\d+\.?\d*)\s*│",
            rf"{re.escape(metric_name)}\s*│\s*([+-]?\d+\.?\d*)\s*%?",
            rf"{re.escape(metric_name)}[:\s]+([+-]?\d+\.?\d*)\s*%?",
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
            if match:
                value = float(match.group(1))
                matched_text = output[match.start() : match.end() + 5]
                if "%" in matched_text:
                    value /= 100
                return value

        return default

    # =========================================================================
    # QC API Methods
    # =========================================================================

    def _get_qc_credentials(self) -> tuple[str, str] | None:
        """Load QC API credentials from ~/.lean/credentials."""
        creds_file = Path.home() / ".lean" / "credentials"
        if not creds_file.exists():
            return None

        try:
            creds = json.loads(creds_file.read_text())
            user_id = creds.get("user-id")
            api_token = creds.get("api-token")
            if user_id and api_token:
                return (user_id, api_token)
        except Exception:
            pass
        return None

    def _qc_api_request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        method: str = "GET",
    ) -> dict[str, Any] | None:
        """Make authenticated request to QC API."""
        creds = self._get_qc_credentials()
        if not creds:
            return None

        user_id, api_token = creds

        try:
            timestamp = str(int(time.time()))
            hash_data = f"{api_token}:{timestamp}"
            hash_value = hashlib.sha256(hash_data.encode()).hexdigest()

            if params:
                query_string = urllib.parse.urlencode(params)
                url = f"https://www.quantconnect.com/api/v2/{endpoint}?{query_string}"
            else:
                url = f"https://www.quantconnect.com/api/v2/{endpoint}"

            auth_string = f"{user_id}:{hash_value}"
            auth_bytes = base64.b64encode(auth_string.encode()).decode()

            request = urllib.request.Request(url, method=method)
            request.add_header("Authorization", f"Basic {auth_bytes}")
            request.add_header("Timestamp", timestamp)

            response = urllib.request.urlopen(request, timeout=30)
            return json.loads(response.read().decode())
        except Exception as e:
            logger.debug(f"QC API request failed: {e}")
            return None

    def _extract_backtest_ids(self, stdout: str) -> tuple[str | None, str | None]:
        """Extract project ID and backtest ID from LEAN output."""
        project_match = re.search(r"Project ID:\s*(\d+)", stdout)
        backtest_match = re.search(r"Backtest id:\s*([a-f0-9]+)", stdout)

        project_id = project_match.group(1) if project_match else None
        backtest_id = backtest_match.group(1) if backtest_match else None

        return project_id, backtest_id

    def _get_backtest_status(self, project_id: str, backtest_id: str) -> str | None:
        """Get backtest status from QC API."""
        data = self._qc_api_request("backtests/read", {"projectId": project_id, "backtestId": backtest_id})
        if data and data.get("success"):
            backtest = data.get("backtest", {})
            if backtest.get("completed"):
                return "Completed"
            elif backtest.get("error"):
                return "RuntimeError"
            else:
                return "Running"
        return None

    def _wait_for_backtest_completion(
        self,
        project_id: str,
        backtest_id: str,
        timeout: int = 600,
    ) -> str | None:
        """Poll QC API until backtest completes or times out."""
        start_time = time.time()
        poll_interval = 10
        dots_printed = 0

        while time.time() - start_time < timeout:
            status = self._get_backtest_status(project_id, backtest_id)
            if status == "Completed":
                return "Completed"
            elif status == "RuntimeError":
                return "RuntimeError"
            elif status == "Running":
                # Print progress dot every 30 seconds
                elapsed = int(time.time() - start_time)
                if elapsed > 0 and elapsed % 30 == 0 and elapsed // 30 > dots_printed:
                    print(".", end="", flush=True)
                    dots_printed = elapsed // 30
                time.sleep(poll_interval)
            else:
                time.sleep(poll_interval)

        return "Timeout"

    def _delete_backtest(self, project_id: str, backtest_id: str) -> bool:
        """Delete/cancel a backtest."""
        data = self._qc_api_request(
            "backtests/delete",
            {"projectId": project_id, "backtestId": backtest_id},
            method="POST",
        )
        return bool(data and data.get("success"))

    def _fetch_backtest_stats(self, project_id: str, backtest_id: str) -> dict[str, Any] | None:
        """Fetch backtest statistics from QC API."""
        data = self._qc_api_request("backtests/read", {"projectId": project_id, "backtestId": backtest_id})
        if data and data.get("success"):
            return data.get("backtest", {}).get("statistics", {})
        return None

    def _list_project_backtests(self, project_id: str) -> list[dict[str, Any]]:
        """List all backtests for a project."""
        data = self._qc_api_request("backtests/list", {"projectId": project_id})
        if data and data.get("success"):
            return data.get("backtests", [])
        return []

    def _cleanup_all_stuck_backtests(self, max_age_seconds: int = 600, max_projects: int = 20) -> int:
        """Clean up stuck backtests across recent projects."""
        logger.info("Checking for stuck backtests...")
        total_cleaned = 0

        data = self._qc_api_request("projects/read")
        if not data or not data.get("success"):
            return 0

        projects = data.get("projects", [])
        try:
            projects = sorted(projects, key=lambda p: p.get("modified", ""), reverse=True)
        except Exception:
            pass

        projects = projects[:max_projects]

        for proj in projects:
            proj_id = str(proj.get("projectId", ""))
            if proj_id:
                cleaned = self._cleanup_stuck_backtests(proj_id, max_age_seconds)
                total_cleaned += cleaned

        if total_cleaned > 0:
            logger.info(f"Cleaned up {total_cleaned} stuck backtests")
            time.sleep(10)

        return total_cleaned

    def _cleanup_all_running_backtests(self, min_age_seconds: int = 60) -> int:
        """Aggressively clean up any running backtests."""
        total_cleaned = 0

        data = self._qc_api_request("projects/read")
        if not data or not data.get("success"):
            return 0

        projects = data.get("projects", [])
        current_time = time.time()

        for proj in projects:
            proj_id = str(proj.get("projectId", ""))
            if not proj_id:
                continue

            backtests = self._list_project_backtests(proj_id)
            for bt in backtests:
                bt_id = bt.get("backtestId")
                node_name = bt.get("nodeName", "")
                is_completed = bt.get("completed", False)

                is_consuming_node = bool(node_name) or not is_completed

                if is_consuming_node:
                    created_str = bt.get("created", "")
                    try:
                        if "T" in created_str:
                            created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        else:
                            created_dt = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S")
                            created_dt = created_dt.replace(tzinfo=timezone.utc)
                        age = current_time - created_dt.timestamp()

                        if age > min_age_seconds:
                            if self._delete_backtest(proj_id, bt_id):
                                total_cleaned += 1
                    except Exception:
                        if self._delete_backtest(proj_id, bt_id):
                            total_cleaned += 1

        return total_cleaned

    def _cleanup_stuck_backtests(self, project_id: str, max_age_seconds: int = 1800) -> int:
        """Clean up stuck backtests for a specific project."""
        cleaned = 0
        backtests = self._list_project_backtests(project_id)
        current_time = time.time()

        for bt in backtests:
            bt_id = bt.get("backtestId")
            node_name = bt.get("nodeName", "")
            is_completed = bt.get("completed", False)

            is_consuming_node = bool(node_name) or not is_completed

            if is_consuming_node:
                created_str = bt.get("created", "")
                try:
                    if "T" in created_str:
                        created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    else:
                        created_dt = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S")
                        created_dt = created_dt.replace(tzinfo=timezone.utc)
                    age = current_time - created_dt.timestamp()

                    if age > max_age_seconds:
                        if self._delete_backtest(project_id, bt_id):
                            cleaned += 1
                except Exception:
                    pass

        return cleaned

    def _cleanup_project(self, project_dir: Path) -> None:
        """Clean up temporary project directory."""
        try:
            shutil.rmtree(project_dir)
        except Exception:
            pass
