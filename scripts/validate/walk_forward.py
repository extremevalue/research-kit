"""
Walk-Forward Validation Module

Implements rolling window validation as specified in ARCHITECTURE.md:
- 12 test windows from 2008-2024
- 5-year training, 1-year testing per window
- Aggregate metrics across windows
- Bootstrap Sharpe confidence intervals

Usage:
    from scripts.validate.walk_forward import WalkForwardValidator

    validator = WalkForwardValidator(workspace, backtest_runner)
    result = validator.validate(entry_id, backtest_code)
"""

import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import json

from scripts.utils.logging_config import get_logger

logger = get_logger("walk_forward")


# Walk-forward configuration (from ARCHITECTURE.md)
WALK_FORWARD_CONFIG = {
    "train_years": 5,
    "test_years": 1,
    "start_year": 2008,
    "end_year": 2024,
}

# Gate thresholds (from ARCHITECTURE.md section 4.6)
WALK_FORWARD_GATES = {
    "median_return_min": 0.0,      # Median test-window return > 0%
    "consistency_min": 0.60,        # % of windows profitable >= 60%
    "sharpe_min": 0.3,              # Aggregate Sharpe > 0.3
    "max_drawdown_max": 0.30,       # Max drawdown (any window) < 30%
    "sharpe_ci_lower_min": 0.0,     # Sharpe 95% CI lower bound > 0
}


@dataclass
class WindowResult:
    """Results from a single test window."""
    window_id: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    test_year: int

    # Metrics
    success: bool
    total_return: Optional[float] = None
    cagr: Optional[float] = None
    sharpe: Optional[float] = None
    max_drawdown: Optional[float] = None
    alpha: Optional[float] = None

    # Regime tags (to be filled by regime analysis)
    regime_tags: Dict[str, str] = field(default_factory=dict)

    # Error info
    error: Optional[str] = None


@dataclass
class WalkForwardResult:
    """Aggregate results from walk-forward validation."""
    entry_id: str
    n_windows: int
    windows: List[WindowResult]

    # Aggregate metrics
    median_return: float
    mean_return: float
    consistency: float  # % of windows with positive return
    aggregate_sharpe: float
    max_drawdown: float  # Worst drawdown across all windows

    # Statistical metrics
    sharpe_ci_lower: float
    sharpe_ci_upper: float
    returns_std: float

    # Gate results
    gates_passed: bool
    gate_results: Dict[str, Tuple[bool, str]]

    # Determination
    determination: str  # VALIDATED, INVALIDATED
    determination_reason: str

    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


def generate_walk_forward_windows() -> List[Dict[str, Any]]:
    """
    Generate the 12 walk-forward windows as specified in ARCHITECTURE.md.

    Returns:
        List of window definitions with train/test periods
    """
    windows = []
    config = WALK_FORWARD_CONFIG

    # Window 1: Train [2008-2012] -> Test [2013]
    # Window 2: Train [2009-2013] -> Test [2014]
    # ...
    # Window 12: Train [2019-2023] -> Test [2024]

    for i in range(12):
        train_start_year = config["start_year"] + i
        train_end_year = train_start_year + config["train_years"] - 1
        test_year = train_end_year + 1

        windows.append({
            "window_id": i + 1,
            "train_start": f"{train_start_year}-01-01",
            "train_end": f"{train_end_year}-12-31",
            "test_start": f"{test_year}-01-01",
            "test_end": f"{test_year}-12-31",
            "test_year": test_year,
        })

    return windows


def bootstrap_sharpe_ci(
    returns: List[float],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: int = 42
) -> Tuple[float, float]:
    """
    Calculate bootstrap confidence interval for Sharpe ratio.

    Args:
        returns: List of period returns (can be window returns or daily returns)
        n_bootstrap: Number of bootstrap samples
        confidence: Confidence level (default 95%)
        seed: Random seed for reproducibility (default 42)

    Returns:
        Tuple of (lower_bound, upper_bound) for Sharpe ratio
    """
    if len(returns) < 2:
        return (0.0, 0.0)

    # Set random seed for reproducibility
    rng = np.random.default_rng(seed)

    returns_arr = np.array(returns)
    sharpes = []

    for _ in range(n_bootstrap):
        # Resample with replacement
        sample = rng.choice(returns_arr, size=len(returns_arr), replace=True)

        # Calculate Sharpe for this sample
        if np.std(sample) > 0:
            # Annualize assuming these are window (annual) returns
            sharpe = np.mean(sample) / np.std(sample)
            sharpes.append(sharpe)

    if not sharpes:
        return (0.0, 0.0)

    # Calculate confidence interval
    alpha = 1 - confidence
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100

    return (
        float(np.percentile(sharpes, lower_percentile)),
        float(np.percentile(sharpes, upper_percentile))
    )


def calculate_aggregate_metrics(windows: List[WindowResult]) -> Dict[str, float]:
    """
    Calculate aggregate metrics across all windows.

    Args:
        windows: List of WindowResult objects

    Returns:
        Dict with aggregate metrics
    """
    successful_windows = [w for w in windows if w.success and w.total_return is not None]

    if not successful_windows:
        return {
            "median_return": 0.0,
            "mean_return": 0.0,
            "consistency": 0.0,
            "aggregate_sharpe": 0.0,
            "max_drawdown": 1.0,
            "returns_std": 0.0,
        }

    returns = [w.total_return for w in successful_windows]
    sharpes = [w.sharpe for w in successful_windows if w.sharpe is not None]
    drawdowns = [w.max_drawdown for w in successful_windows if w.max_drawdown is not None]

    # Median return across windows
    median_return = float(np.median(returns))

    # Mean return
    mean_return = float(np.mean(returns))

    # Consistency: % of windows with positive return
    n_profitable = len([r for r in returns if r > 0])
    consistency = n_profitable / len(returns) if returns else 0.0

    # Aggregate Sharpe (mean of window Sharpes)
    aggregate_sharpe = float(np.mean(sharpes)) if sharpes else 0.0

    # Max drawdown (worst across all windows)
    max_drawdown = float(max(drawdowns)) if drawdowns else 1.0

    # Return standard deviation
    returns_std = float(np.std(returns)) if len(returns) > 1 else 0.0

    return {
        "median_return": median_return,
        "mean_return": mean_return,
        "consistency": consistency,
        "aggregate_sharpe": aggregate_sharpe,
        "max_drawdown": max_drawdown,
        "returns_std": returns_std,
    }


def check_walk_forward_gates(
    metrics: Dict[str, float],
    sharpe_ci_lower: float
) -> Tuple[bool, Dict[str, Tuple[bool, str]]]:
    """
    Check if walk-forward results pass all gates.

    Args:
        metrics: Aggregate metrics dict
        sharpe_ci_lower: Lower bound of Sharpe CI

    Returns:
        Tuple of (all_passed, gate_results_dict)
    """
    gates = WALK_FORWARD_GATES
    results = {}

    # Gate 1: Profitability - Median return > 0%
    passed = metrics["median_return"] > gates["median_return_min"]
    results["profitability"] = (
        passed,
        f"Median return {metrics['median_return']*100:.1f}% {'>' if passed else '<='} {gates['median_return_min']*100:.0f}%"
    )

    # Gate 2: Consistency - % windows profitable >= 60%
    passed = metrics["consistency"] >= gates["consistency_min"]
    results["consistency"] = (
        passed,
        f"Consistency {metrics['consistency']*100:.0f}% {'>=' if passed else '<'} {gates['consistency_min']*100:.0f}%"
    )

    # Gate 3: Risk-Adjusted - Aggregate Sharpe > 0.3
    passed = metrics["aggregate_sharpe"] > gates["sharpe_min"]
    results["risk_adjusted"] = (
        passed,
        f"Sharpe {metrics['aggregate_sharpe']:.2f} {'>' if passed else '<='} {gates['sharpe_min']}"
    )

    # Gate 4: Drawdown - Max DD < 30%
    passed = metrics["max_drawdown"] < gates["max_drawdown_max"]
    results["drawdown"] = (
        passed,
        f"Max DD {metrics['max_drawdown']*100:.1f}% {'<' if passed else '>='} {gates['max_drawdown_max']*100:.0f}%"
    )

    # Gate 5: Statistical - Sharpe CI lower bound > 0
    passed = sharpe_ci_lower > gates["sharpe_ci_lower_min"]
    results["statistical"] = (
        passed,
        f"Sharpe CI lower {sharpe_ci_lower:.2f} {'>' if passed else '<='} {gates['sharpe_ci_lower_min']}"
    )

    all_passed = all(r[0] for r in results.values())

    return all_passed, results


class WalkForwardValidator:
    """
    Runs walk-forward validation for a strategy.

    This validator:
    1. Runs backtests for each of 12 test windows
    2. Calculates aggregate metrics
    3. Computes bootstrap Sharpe CI
    4. Applies gates to determine VALIDATED/INVALIDATED
    """

    def __init__(self, workspace, backtest_runner_func):
        """
        Initialize the walk-forward validator.

        Args:
            workspace: Workspace instance
            backtest_runner_func: Function to run a single backtest
                                  Signature: (code, start_date, end_date, entry_id) -> BacktestResult
        """
        self.workspace = workspace
        self.run_backtest = backtest_runner_func
        self.windows = generate_walk_forward_windows()

    def validate(
        self,
        entry_id: str,
        backtest_code: str,
        save_results: bool = True
    ) -> WalkForwardResult:
        """
        Run walk-forward validation for an entry.

        Args:
            entry_id: Catalog entry ID
            backtest_code: Generated backtest code
            save_results: Whether to save results to disk

        Returns:
            WalkForwardResult with all window results and determination
        """
        logger.info(f"Starting walk-forward validation for {entry_id}")
        print(f"\n  Walk-Forward Validation: {len(self.windows)} windows")

        import time

        window_results = []
        rate_limit_delay = 5  # Seconds between backtests to avoid QC rate limiting

        for i, window in enumerate(self.windows):
            window_id = window["window_id"]
            test_start = window["test_start"]
            test_end = window["test_end"]
            test_year = window["test_year"]

            print(f"    Window {window_id}/12: Test year {test_year}...", end=" ", flush=True)

            # Add delay between backtests to avoid rate limiting (skip first)
            if i > 0:
                time.sleep(rate_limit_delay)

            # Run backtest for this test window with retry on rate limiting
            max_retries = 3
            result = None
            for attempt in range(max_retries):
                result = self.run_backtest(
                    backtest_code,
                    test_start,
                    test_end,
                    f"{entry_id}_w{window_id}"
                )

                # Check for rate limiting
                if hasattr(result, 'rate_limited') and result.rate_limited:
                    if attempt < max_retries - 1:
                        wait_time = 30 * (attempt + 1)  # 30s, 60s, 90s
                        print(f"Rate limited, waiting {wait_time}s...", end=" ", flush=True)
                        time.sleep(wait_time)
                        continue
                break

            if result.success:
                print(f"Return: {result.total_return*100:+.1f}%  Sharpe: {result.sharpe:.2f}")

                window_results.append(WindowResult(
                    window_id=window_id,
                    train_start=window["train_start"],
                    train_end=window["train_end"],
                    test_start=test_start,
                    test_end=test_end,
                    test_year=test_year,
                    success=True,
                    total_return=result.total_return,
                    cagr=result.cagr,
                    sharpe=result.sharpe,
                    max_drawdown=result.max_drawdown,
                    alpha=result.alpha,
                ))
            else:
                print(f"FAILED: {result.error}")

                window_results.append(WindowResult(
                    window_id=window_id,
                    train_start=window["train_start"],
                    train_end=window["train_end"],
                    test_start=test_start,
                    test_end=test_end,
                    test_year=test_year,
                    success=False,
                    error=result.error,
                ))

        # Calculate aggregate metrics
        metrics = calculate_aggregate_metrics(window_results)

        # Calculate bootstrap Sharpe CI
        successful_returns = [
            w.total_return for w in window_results
            if w.success and w.total_return is not None
        ]
        sharpe_ci_lower, sharpe_ci_upper = bootstrap_sharpe_ci(successful_returns)

        # Check gates
        all_passed, gate_results = check_walk_forward_gates(metrics, sharpe_ci_lower)

        # Determine outcome
        if all_passed:
            determination = "VALIDATED"
            determination_reason = "All walk-forward gates passed"
        else:
            determination = "INVALIDATED"
            failed_gates = [name for name, (passed, _) in gate_results.items() if not passed]
            determination_reason = f"Failed gates: {', '.join(failed_gates)}"

        # Print summary
        print(f"\n  Walk-Forward Summary:")
        print(f"    Median Return: {metrics['median_return']*100:+.1f}%")
        print(f"    Consistency: {metrics['consistency']*100:.0f}% windows profitable")
        print(f"    Aggregate Sharpe: {metrics['aggregate_sharpe']:.2f}")
        print(f"    Max Drawdown: {metrics['max_drawdown']*100:.1f}%")
        print(f"    Sharpe 95% CI: [{sharpe_ci_lower:.2f}, {sharpe_ci_upper:.2f}]")
        print(f"\n  Gate Results:")
        for name, (passed, msg) in gate_results.items():
            status = "PASS" if passed else "FAIL"
            print(f"    [{status}] {name}: {msg}")

        result = WalkForwardResult(
            entry_id=entry_id,
            n_windows=len(self.windows),
            windows=window_results,
            median_return=metrics["median_return"],
            mean_return=metrics["mean_return"],
            consistency=metrics["consistency"],
            aggregate_sharpe=metrics["aggregate_sharpe"],
            max_drawdown=metrics["max_drawdown"],
            sharpe_ci_lower=sharpe_ci_lower,
            sharpe_ci_upper=sharpe_ci_upper,
            returns_std=metrics["returns_std"],
            gates_passed=all_passed,
            gate_results=gate_results,
            determination=determination,
            determination_reason=determination_reason,
        )

        if save_results:
            self._save_results(entry_id, result)

        return result

    def _save_results(self, entry_id: str, result: WalkForwardResult):
        """Save walk-forward results to disk."""
        val_dir = self.workspace.validations_path / entry_id
        val_dir.mkdir(parents=True, exist_ok=True)

        # Convert to serializable dict
        result_dict = {
            "entry_id": result.entry_id,
            "n_windows": result.n_windows,
            "windows": [
                {
                    "window_id": w.window_id,
                    "train_start": w.train_start,
                    "train_end": w.train_end,
                    "test_start": w.test_start,
                    "test_end": w.test_end,
                    "test_year": w.test_year,
                    "success": w.success,
                    "total_return": w.total_return,
                    "cagr": w.cagr,
                    "sharpe": w.sharpe,
                    "max_drawdown": w.max_drawdown,
                    "alpha": w.alpha,
                    "regime_tags": w.regime_tags,
                    "error": w.error,
                }
                for w in result.windows
            ],
            "aggregate_metrics": {
                "median_return": result.median_return,
                "mean_return": result.mean_return,
                "consistency": result.consistency,
                "aggregate_sharpe": result.aggregate_sharpe,
                "max_drawdown": result.max_drawdown,
                "sharpe_ci_lower": result.sharpe_ci_lower,
                "sharpe_ci_upper": result.sharpe_ci_upper,
                "returns_std": result.returns_std,
            },
            "gate_results": {
                name: {"passed": passed, "message": msg}
                for name, (passed, msg) in result.gate_results.items()
            },
            "gates_passed": result.gates_passed,
            "determination": result.determination,
            "determination_reason": result.determination_reason,
            "timestamp": result.timestamp,
        }

        results_file = val_dir / "walk_forward_results.json"
        results_file.write_text(json.dumps(result_dict, indent=2))
        logger.info(f"Saved walk-forward results to {results_file}")
