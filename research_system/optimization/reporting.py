"""Walk-forward results reporting and analysis.

This module provides reporting capabilities for walk-forward validation:
- Terminal summary output
- JSON export
- Parameter evolution analysis
"""

from __future__ import annotations

import json
from typing import Any

from research_system.optimization.walk_forward import WalkForwardResult


def format_terminal_summary(result: WalkForwardResult) -> str:
    """Format walk-forward result as terminal summary.

    Args:
        result: WalkForwardResult to format

    Returns:
        Formatted string for terminal display
    """
    lines = []
    lines.append("=" * 60)
    lines.append("  Walk-Forward Validation Results")
    lines.append("=" * 60)
    lines.append("")

    # Strategy info
    lines.append(f"Strategy: {result.strategy_id}")
    lines.append(f"Periods:  {len(result.periods)}")
    lines.append("")

    # Configuration
    lines.append("Configuration:")
    lines.append(f"  Date range: {result.config.start_year} - {result.config.end_year}")
    lines.append(f"  Initial training: {result.config.initial_train_years} years")
    lines.append(f"  Test period: {result.config.test_years} year(s)")
    lines.append(f"  Window type: {'Expanding' if result.config.expanding_window else 'Rolling'}")
    lines.append("")

    # Period details
    lines.append("-" * 60)
    lines.append("Period Results:")
    lines.append("-" * 60)

    for period in result.periods:
        status = "✓" if period.success else "✗"
        lines.append(f"\n  Period {period.period_id}: {status}")
        lines.append(f"    Optimize: {period.opt_start} to {period.opt_end}")
        lines.append(f"    Test:     {period.test_start} to {period.test_end}")

        if period.success:
            if period.optimization_sharpe is not None:
                lines.append(f"    IS Sharpe:  {period.optimization_sharpe:.2f}")
            if period.oos_sharpe is not None:
                lines.append(f"    OOS Sharpe: {period.oos_sharpe:.2f}")
            if period.oos_cagr is not None:
                lines.append(f"    OOS CAGR:   {period.oos_cagr * 100:.1f}%")
            if period.optimized_params:
                params_str = ", ".join(f"{k}={v}" for k, v in period.optimized_params.items())
                lines.append(f"    Params:     {params_str}")
        else:
            lines.append(f"    Error: {period.error}")

    lines.append("")

    # Aggregate metrics
    lines.append("-" * 60)
    lines.append("Aggregate Metrics:")
    lines.append("-" * 60)

    if result.avg_oos_sharpe is not None:
        lines.append(f"  Avg OOS Sharpe:     {result.avg_oos_sharpe:.2f}")
    if result.worst_oos_sharpe is not None:
        lines.append(f"  Worst OOS Sharpe:   {result.worst_oos_sharpe:.2f}")
    if result.avg_oos_cagr is not None:
        lines.append(f"  Avg OOS CAGR:       {result.avg_oos_cagr * 100:.1f}%")
    if result.worst_oos_drawdown is not None:
        lines.append(f"  Worst OOS Drawdown: {result.worst_oos_drawdown * 100:.1f}%")

    lines.append("")

    # Quality metrics
    lines.append("-" * 60)
    lines.append("Quality Metrics:")
    lines.append("-" * 60)

    if result.consistency is not None:
        profitable = sum(1 for p in result.periods if p.success and p.oos_cagr and p.oos_cagr > 0)
        total = sum(1 for p in result.periods if p.success)
        lines.append(f"  Consistency:        {result.consistency * 100:.0f}% ({profitable}/{total} profitable)")

    if result.is_vs_oos_degradation is not None:
        lines.append(f"  IS→OOS Degradation: {result.is_vs_oos_degradation * 100:.0f}%")
        if result.is_vs_oos_degradation > 0.5:
            lines.append("    ⚠ High degradation suggests overfitting")
        elif result.is_vs_oos_degradation < 0.2:
            lines.append("    ✓ Low degradation indicates robust strategy")

    if result.parameter_stability is not None:
        lines.append(f"  Parameter Stability: {result.parameter_stability * 100:.0f}%")
        if result.parameter_stability < 0.5:
            lines.append("    ⚠ Low stability suggests overfitting")
        elif result.parameter_stability > 0.8:
            lines.append("    ✓ High stability indicates robust parameters")

    lines.append("")

    # Final verdict
    lines.append("=" * 60)
    if result.success:
        verdict = _get_verdict(result)
        lines.append(f"  Verdict: {verdict}")
    else:
        lines.append(f"  Validation Failed: {result.error}")
    lines.append("=" * 60)

    return "\n".join(lines)


def _get_verdict(result: WalkForwardResult) -> str:
    """Generate a verdict based on walk-forward results.

    Args:
        result: WalkForwardResult to analyze

    Returns:
        Verdict string
    """
    issues = []

    # Check Sharpe
    if result.avg_oos_sharpe is not None:
        if result.avg_oos_sharpe < 0.5:
            issues.append("low Sharpe")
        elif result.avg_oos_sharpe < 1.0:
            issues.append("marginal Sharpe")

    # Check consistency
    if result.consistency is not None:
        if result.consistency < 0.5:
            issues.append("inconsistent")
        elif result.consistency < 0.7:
            issues.append("partially consistent")

    # Check degradation
    if result.is_vs_oos_degradation is not None:
        if result.is_vs_oos_degradation > 0.5:
            issues.append("significant overfitting")
        elif result.is_vs_oos_degradation > 0.3:
            issues.append("some overfitting")

    # Check stability
    if result.parameter_stability is not None:
        if result.parameter_stability < 0.5:
            issues.append("unstable parameters")

    if not issues:
        if result.avg_oos_sharpe and result.avg_oos_sharpe >= 1.0:
            return "STRONG - Robust strategy with good OOS performance"
        return "ACCEPTABLE - Strategy shows reasonable robustness"
    elif len(issues) >= 3:
        return f"WEAK - Multiple concerns: {', '.join(issues)}"
    else:
        return f"CAUTION - {', '.join(issues)}"


def format_json_output(result: WalkForwardResult, pretty: bool = True) -> str:
    """Format walk-forward result as JSON.

    Args:
        result: WalkForwardResult to format
        pretty: If True, format with indentation

    Returns:
        JSON string
    """
    data = result.to_dict()

    # Add verdict
    if result.success:
        data["verdict"] = _get_verdict(result)

    if pretty:
        return json.dumps(data, indent=2)
    return json.dumps(data)


def format_parameter_evolution(result: WalkForwardResult) -> str:
    """Format parameter evolution across periods.

    Args:
        result: WalkForwardResult to analyze

    Returns:
        Formatted string showing parameter changes
    """
    lines = []
    lines.append("Parameter Evolution:")
    lines.append("-" * 40)

    # Collect all parameter names
    all_params = set()
    for period in result.periods:
        if period.optimized_params:
            all_params.update(period.optimized_params.keys())

    if not all_params:
        lines.append("  No parameters tracked")
        return "\n".join(lines)

    # Show evolution for each parameter
    for param_name in sorted(all_params):
        lines.append(f"\n  {param_name}:")
        for period in result.periods:
            if period.optimized_params and param_name in period.optimized_params:
                value = period.optimized_params[param_name]
                year = period.test_start[:4]
                lines.append(f"    {year}: {value}")

    return "\n".join(lines)


def print_walk_forward_summary(result: WalkForwardResult) -> None:
    """Print walk-forward summary to stdout.

    Args:
        result: WalkForwardResult to display
    """
    print(format_terminal_summary(result))


def print_parameter_evolution(result: WalkForwardResult) -> None:
    """Print parameter evolution to stdout.

    Args:
        result: WalkForwardResult to analyze
    """
    print(format_parameter_evolution(result))
