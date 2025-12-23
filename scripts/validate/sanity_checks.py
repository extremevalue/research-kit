"""
Sanity checks for backtest results.

Flags exceptional results that require manual review. This catches
results that are "too good to be true" and may indicate:
- Data errors (wrong column, look-ahead bias that slipped through)
- Overfitting to specific market conditions
- Implementation bugs in the algorithm

Usage:
    from scripts.validate.sanity_checks import check_backtest_sanity
    flags = check_backtest_sanity(backtest_results)
    if flags:
        # Results need manual review
        for flag in flags:
            print(f"WARNING: {flag.code} - {flag.message}")
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from scripts.utils.logging_config import get_logger

logger = get_logger("sanity-checks")


class FlagSeverity(Enum):
    """Severity of sanity flags."""
    CRITICAL = "critical"  # Almost certainly an error, block until reviewed
    HIGH = "high"          # Likely an issue, require review
    MEDIUM = "medium"      # Unusual but possible, flag for awareness
    LOW = "low"            # Minor concern, informational


@dataclass
class SanityFlag:
    """A sanity check flag indicating unusual results."""
    code: str
    message: str
    severity: FlagSeverity
    metric_name: str
    actual_value: float
    threshold: float
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "metric_name": self.metric_name,
            "actual_value": self.actual_value,
            "threshold": self.threshold,
            "details": self.details
        }


@dataclass
class SanityCheckResult:
    """Complete sanity check result."""
    component_id: str
    test_type: str  # "is" or "oos"
    passed: bool  # True if no critical flags
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    flags: List[SanityFlag] = field(default_factory=list)
    metrics_reviewed: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "test_type": self.test_type,
            "passed": self.passed,
            "timestamp": self.timestamp,
            "flags": [f.to_dict() for f in self.flags],
            "metrics_reviewed": self.metrics_reviewed
        }

    @property
    def has_critical_flags(self) -> bool:
        return any(f.severity == FlagSeverity.CRITICAL for f in self.flags)

    @property
    def has_high_flags(self) -> bool:
        return any(f.severity == FlagSeverity.HIGH for f in self.flags)


# Threshold definitions
THRESHOLDS = {
    # Sharpe ratio thresholds
    "sharpe_exceptional": 2.0,      # Sharpe > 2.0 is exceptional
    "sharpe_suspicious": 3.0,       # Sharpe > 3.0 is suspicious
    "sharpe_impossible": 5.0,       # Sharpe > 5.0 is almost certainly wrong

    # Alpha thresholds (annualized %)
    "alpha_exceptional": 5.0,       # Alpha > 5% is exceptional
    "alpha_suspicious": 10.0,       # Alpha > 10% is suspicious
    "alpha_impossible": 20.0,       # Alpha > 20% is almost certainly wrong

    # Return thresholds (CAGR %)
    "cagr_exceptional": 20.0,       # CAGR > 20% is exceptional
    "cagr_suspicious": 30.0,        # CAGR > 30% is suspicious
    "cagr_impossible": 50.0,        # CAGR > 50% is almost certainly wrong

    # Drawdown thresholds (%)
    "drawdown_too_low": 5.0,        # Max DD < 5% with high returns is suspicious
    "drawdown_extreme": 50.0,       # Max DD > 50% needs review

    # Win rate thresholds (%)
    "win_rate_exceptional": 65.0,   # Win rate > 65% is exceptional
    "win_rate_suspicious": 75.0,    # Win rate > 75% is suspicious
    "win_rate_impossible": 85.0,    # Win rate > 85% is almost certainly wrong

    # Trade count thresholds
    "trades_too_few": 30,           # Less than 30 trades is statistically weak
    "trades_suspicious_pnl": 95.0,  # > 95% profitable trades is suspicious

    # Improvement thresholds (for filter tests)
    "improvement_exceptional": 50.0,  # 50% improvement is exceptional
    "improvement_suspicious": 100.0,  # 100% improvement is suspicious
}


def check_sharpe_ratio(results: Dict[str, Any]) -> List[SanityFlag]:
    """Check Sharpe ratio for anomalies."""
    flags = []
    sharpe = results.get("sharpe_ratio") or results.get("sharpe", 0)

    if sharpe is None:
        return flags

    if sharpe > THRESHOLDS["sharpe_impossible"]:
        flags.append(SanityFlag(
            code="SHARPE_IMPOSSIBLE",
            message=f"Sharpe ratio {sharpe:.2f} > {THRESHOLDS['sharpe_impossible']} is almost certainly an error",
            severity=FlagSeverity.CRITICAL,
            metric_name="sharpe_ratio",
            actual_value=sharpe,
            threshold=THRESHOLDS["sharpe_impossible"]
        ))
    elif sharpe > THRESHOLDS["sharpe_suspicious"]:
        flags.append(SanityFlag(
            code="SHARPE_SUSPICIOUS",
            message=f"Sharpe ratio {sharpe:.2f} > {THRESHOLDS['sharpe_suspicious']} is suspicious - verify data",
            severity=FlagSeverity.HIGH,
            metric_name="sharpe_ratio",
            actual_value=sharpe,
            threshold=THRESHOLDS["sharpe_suspicious"]
        ))
    elif sharpe > THRESHOLDS["sharpe_exceptional"]:
        flags.append(SanityFlag(
            code="SHARPE_EXCEPTIONAL",
            message=f"Sharpe ratio {sharpe:.2f} > {THRESHOLDS['sharpe_exceptional']} is exceptional - review recommended",
            severity=FlagSeverity.MEDIUM,
            metric_name="sharpe_ratio",
            actual_value=sharpe,
            threshold=THRESHOLDS["sharpe_exceptional"]
        ))

    return flags


def check_alpha(results: Dict[str, Any]) -> List[SanityFlag]:
    """Check alpha for anomalies."""
    flags = []
    alpha = results.get("alpha") or results.get("annual_alpha", 0)

    if alpha is None:
        return flags

    # Convert to percentage if in decimal form
    if abs(alpha) < 1:
        alpha = alpha * 100

    if alpha > THRESHOLDS["alpha_impossible"]:
        flags.append(SanityFlag(
            code="ALPHA_IMPOSSIBLE",
            message=f"Alpha {alpha:.1f}% > {THRESHOLDS['alpha_impossible']}% is almost certainly an error",
            severity=FlagSeverity.CRITICAL,
            metric_name="alpha",
            actual_value=alpha,
            threshold=THRESHOLDS["alpha_impossible"]
        ))
    elif alpha > THRESHOLDS["alpha_suspicious"]:
        flags.append(SanityFlag(
            code="ALPHA_SUSPICIOUS",
            message=f"Alpha {alpha:.1f}% > {THRESHOLDS['alpha_suspicious']}% is suspicious - verify data",
            severity=FlagSeverity.HIGH,
            metric_name="alpha",
            actual_value=alpha,
            threshold=THRESHOLDS["alpha_suspicious"]
        ))
    elif alpha > THRESHOLDS["alpha_exceptional"]:
        flags.append(SanityFlag(
            code="ALPHA_EXCEPTIONAL",
            message=f"Alpha {alpha:.1f}% > {THRESHOLDS['alpha_exceptional']}% is exceptional - review recommended",
            severity=FlagSeverity.MEDIUM,
            metric_name="alpha",
            actual_value=alpha,
            threshold=THRESHOLDS["alpha_exceptional"]
        ))

    return flags


def check_returns(results: Dict[str, Any]) -> List[SanityFlag]:
    """Check CAGR for anomalies."""
    flags = []
    cagr = results.get("cagr") or results.get("compound_annual_return", 0)

    if cagr is None:
        return flags

    # Convert to percentage if in decimal form
    if abs(cagr) < 1:
        cagr = cagr * 100

    if cagr > THRESHOLDS["cagr_impossible"]:
        flags.append(SanityFlag(
            code="CAGR_IMPOSSIBLE",
            message=f"CAGR {cagr:.1f}% > {THRESHOLDS['cagr_impossible']}% is almost certainly an error",
            severity=FlagSeverity.CRITICAL,
            metric_name="cagr",
            actual_value=cagr,
            threshold=THRESHOLDS["cagr_impossible"]
        ))
    elif cagr > THRESHOLDS["cagr_suspicious"]:
        flags.append(SanityFlag(
            code="CAGR_SUSPICIOUS",
            message=f"CAGR {cagr:.1f}% > {THRESHOLDS['cagr_suspicious']}% is suspicious - verify data",
            severity=FlagSeverity.HIGH,
            metric_name="cagr",
            actual_value=cagr,
            threshold=THRESHOLDS["cagr_suspicious"]
        ))
    elif cagr > THRESHOLDS["cagr_exceptional"]:
        flags.append(SanityFlag(
            code="CAGR_EXCEPTIONAL",
            message=f"CAGR {cagr:.1f}% > {THRESHOLDS['cagr_exceptional']}% is exceptional - review recommended",
            severity=FlagSeverity.MEDIUM,
            metric_name="cagr",
            actual_value=cagr,
            threshold=THRESHOLDS["cagr_exceptional"]
        ))

    return flags


def check_drawdown(results: Dict[str, Any]) -> List[SanityFlag]:
    """Check drawdown for anomalies."""
    flags = []
    max_dd = results.get("max_drawdown") or results.get("maximum_drawdown", 0)
    cagr = results.get("cagr") or results.get("compound_annual_return", 0)

    if max_dd is None:
        return flags

    # Ensure positive value for comparison
    max_dd = abs(max_dd)

    # Convert to percentage if in decimal form
    if max_dd < 1:
        max_dd = max_dd * 100
    if cagr and abs(cagr) < 1:
        cagr = cagr * 100

    # Check for suspiciously low drawdown with high returns
    if cagr and cagr > 15 and max_dd < THRESHOLDS["drawdown_too_low"]:
        flags.append(SanityFlag(
            code="DRAWDOWN_TOO_LOW",
            message=f"Max drawdown {max_dd:.1f}% with CAGR {cagr:.1f}% is suspicious - verify data",
            severity=FlagSeverity.HIGH,
            metric_name="max_drawdown",
            actual_value=max_dd,
            threshold=THRESHOLDS["drawdown_too_low"],
            details={"cagr": cagr}
        ))

    # Check for extreme drawdown
    if max_dd > THRESHOLDS["drawdown_extreme"]:
        flags.append(SanityFlag(
            code="DRAWDOWN_EXTREME",
            message=f"Max drawdown {max_dd:.1f}% > {THRESHOLDS['drawdown_extreme']}% - review risk management",
            severity=FlagSeverity.MEDIUM,
            metric_name="max_drawdown",
            actual_value=max_dd,
            threshold=THRESHOLDS["drawdown_extreme"]
        ))

    return flags


def check_win_rate(results: Dict[str, Any]) -> List[SanityFlag]:
    """Check win rate for anomalies."""
    flags = []
    win_rate = results.get("win_rate") or results.get("winning_percentage", 0)

    if win_rate is None:
        return flags

    # Convert to percentage if in decimal form
    if win_rate < 1:
        win_rate = win_rate * 100

    if win_rate > THRESHOLDS["win_rate_impossible"]:
        flags.append(SanityFlag(
            code="WIN_RATE_IMPOSSIBLE",
            message=f"Win rate {win_rate:.1f}% > {THRESHOLDS['win_rate_impossible']}% is almost certainly an error",
            severity=FlagSeverity.CRITICAL,
            metric_name="win_rate",
            actual_value=win_rate,
            threshold=THRESHOLDS["win_rate_impossible"]
        ))
    elif win_rate > THRESHOLDS["win_rate_suspicious"]:
        flags.append(SanityFlag(
            code="WIN_RATE_SUSPICIOUS",
            message=f"Win rate {win_rate:.1f}% > {THRESHOLDS['win_rate_suspicious']}% is suspicious - verify data",
            severity=FlagSeverity.HIGH,
            metric_name="win_rate",
            actual_value=win_rate,
            threshold=THRESHOLDS["win_rate_suspicious"]
        ))
    elif win_rate > THRESHOLDS["win_rate_exceptional"]:
        flags.append(SanityFlag(
            code="WIN_RATE_EXCEPTIONAL",
            message=f"Win rate {win_rate:.1f}% > {THRESHOLDS['win_rate_exceptional']}% is exceptional - review recommended",
            severity=FlagSeverity.MEDIUM,
            metric_name="win_rate",
            actual_value=win_rate,
            threshold=THRESHOLDS["win_rate_exceptional"]
        ))

    return flags


def check_trade_count(results: Dict[str, Any]) -> List[SanityFlag]:
    """Check trade statistics for anomalies."""
    flags = []
    total_trades = results.get("total_trades") or results.get("trade_count", 0)
    winning_trades = results.get("winning_trades", 0)

    if total_trades is None or total_trades == 0:
        flags.append(SanityFlag(
            code="NO_TRADES",
            message="No trades executed - strategy may not be generating signals",
            severity=FlagSeverity.HIGH,
            metric_name="total_trades",
            actual_value=0,
            threshold=1
        ))
        return flags

    if total_trades < THRESHOLDS["trades_too_few"]:
        flags.append(SanityFlag(
            code="INSUFFICIENT_TRADES",
            message=f"Only {total_trades} trades < {THRESHOLDS['trades_too_few']} minimum for statistical significance",
            severity=FlagSeverity.MEDIUM,
            metric_name="total_trades",
            actual_value=total_trades,
            threshold=THRESHOLDS["trades_too_few"]
        ))

    # Check for suspiciously high profitable trade percentage
    if winning_trades and total_trades:
        profitable_pct = (winning_trades / total_trades) * 100
        if profitable_pct > THRESHOLDS["trades_suspicious_pnl"]:
            flags.append(SanityFlag(
                code="TRADES_TOO_PROFITABLE",
                message=f"{profitable_pct:.1f}% profitable trades is suspicious - verify trade logic",
                severity=FlagSeverity.HIGH,
                metric_name="profitable_trade_pct",
                actual_value=profitable_pct,
                threshold=THRESHOLDS["trades_suspicious_pnl"]
            ))

    return flags


def check_improvement(
    strategy_results: Dict[str, Any],
    baseline_results: Dict[str, Any]
) -> List[SanityFlag]:
    """Check improvement over baseline for filter tests."""
    flags = []

    baseline_sharpe = baseline_results.get("sharpe_ratio", 0) or 0
    strategy_sharpe = strategy_results.get("sharpe_ratio", 0) or 0

    if baseline_sharpe == 0:
        return flags

    improvement_pct = ((strategy_sharpe - baseline_sharpe) / abs(baseline_sharpe)) * 100

    if improvement_pct > THRESHOLDS["improvement_suspicious"]:
        flags.append(SanityFlag(
            code="IMPROVEMENT_SUSPICIOUS",
            message=f"Sharpe improvement {improvement_pct:.1f}% > {THRESHOLDS['improvement_suspicious']}% is suspicious",
            severity=FlagSeverity.HIGH,
            metric_name="sharpe_improvement",
            actual_value=improvement_pct,
            threshold=THRESHOLDS["improvement_suspicious"],
            details={
                "baseline_sharpe": baseline_sharpe,
                "strategy_sharpe": strategy_sharpe
            }
        ))
    elif improvement_pct > THRESHOLDS["improvement_exceptional"]:
        flags.append(SanityFlag(
            code="IMPROVEMENT_EXCEPTIONAL",
            message=f"Sharpe improvement {improvement_pct:.1f}% > {THRESHOLDS['improvement_exceptional']}% is exceptional",
            severity=FlagSeverity.MEDIUM,
            metric_name="sharpe_improvement",
            actual_value=improvement_pct,
            threshold=THRESHOLDS["improvement_exceptional"],
            details={
                "baseline_sharpe": baseline_sharpe,
                "strategy_sharpe": strategy_sharpe
            }
        ))

    return flags


def check_backtest_sanity(
    component_id: str,
    results: Dict[str, Any],
    test_type: str = "is",
    baseline_results: Optional[Dict[str, Any]] = None
) -> SanityCheckResult:
    """
    Run all sanity checks on backtest results.

    Args:
        component_id: Catalog entry ID
        results: Backtest results dict with metrics
        test_type: "is" for in-sample, "oos" for out-of-sample
        baseline_results: Optional baseline for comparison (filter tests)

    Returns:
        SanityCheckResult with all flags and pass/fail status
    """
    logger.info(f"Running sanity checks for {component_id} ({test_type})")

    all_flags = []

    # Run individual checks
    all_flags.extend(check_sharpe_ratio(results))
    all_flags.extend(check_alpha(results))
    all_flags.extend(check_returns(results))
    all_flags.extend(check_drawdown(results))
    all_flags.extend(check_win_rate(results))
    all_flags.extend(check_trade_count(results))

    # Improvement checks if baseline provided
    if baseline_results:
        all_flags.extend(check_improvement(results, baseline_results))

    # Extract metrics that were reviewed
    metrics_reviewed = {
        "sharpe_ratio": results.get("sharpe_ratio") or results.get("sharpe"),
        "alpha": results.get("alpha") or results.get("annual_alpha"),
        "cagr": results.get("cagr") or results.get("compound_annual_return"),
        "max_drawdown": results.get("max_drawdown") or results.get("maximum_drawdown"),
        "win_rate": results.get("win_rate") or results.get("winning_percentage"),
        "total_trades": results.get("total_trades") or results.get("trade_count"),
    }
    # Remove None values
    metrics_reviewed = {k: v for k, v in metrics_reviewed.items() if v is not None}

    # Determine pass/fail (passed if no critical flags)
    passed = not any(f.severity == FlagSeverity.CRITICAL for f in all_flags)

    result = SanityCheckResult(
        component_id=component_id,
        test_type=test_type,
        passed=passed,
        flags=all_flags,
        metrics_reviewed=metrics_reviewed
    )

    # Log results
    if all_flags:
        for flag in all_flags:
            log_level = "error" if flag.severity == FlagSeverity.CRITICAL else "warning"
            getattr(logger, log_level)(f"  {flag.code}: {flag.message}")
    else:
        logger.info(f"  All sanity checks passed for {component_id}")

    return result


def save_sanity_result(result: SanityCheckResult, output_dir: Path) -> Path:
    """Save sanity check result to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"sanity_check_{result.test_type}.json"

    with open(output_file, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)

    logger.info(f"Saved sanity check result to {output_file}")
    return output_file


if __name__ == "__main__":
    # Example usage
    example_results = {
        "sharpe_ratio": 2.5,
        "alpha": 0.08,
        "cagr": 0.25,
        "max_drawdown": -0.12,
        "win_rate": 0.58,
        "total_trades": 150,
        "winning_trades": 87
    }

    result = check_backtest_sanity("IND-002", example_results, "is")

    print(f"\nSanity Check Result: {'PASSED' if result.passed else 'FAILED'}")
    print(f"Timestamp: {result.timestamp}")
    print(f"Flags: {len(result.flags)}")

    if result.flags:
        print("\nFlags:")
        for flag in result.flags:
            print(f"  [{flag.severity.value.upper()}] {flag.code}: {flag.message}")

    print("\nMetrics Reviewed:")
    for name, value in result.metrics_reviewed.items():
        print(f"  {name}: {value}")
