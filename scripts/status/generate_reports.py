"""
Status Report Generator

Scans validation results and generates dashboard reports.
"""

import json
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


def scan_strategies(workspace: Path) -> List[Dict[str, Any]]:
    """
    Scan workspace for all strategies and their validation results.

    Returns list of strategy records with:
    - entry_id, status, strategy_type, name, summary
    - metrics (sharpe, return, consistency, drawdown, etc.)
    - timestamps
    - file paths
    """
    strategies = []

    validations_dir = workspace / "validations"
    catalog_dir = workspace / "catalog" / "entries"

    if not validations_dir.exists():
        logger.warning(f"Validations directory not found: {validations_dir}")
        return strategies

    # Find all STRAT-XXX directories (not window dirs like STRAT-001_w1)
    strat_dirs = [
        d for d in validations_dir.iterdir()
        if d.is_dir() and d.name.startswith("STRAT-") and "_w" not in d.name
    ]

    for strat_dir in sorted(strat_dirs):
        entry_id = strat_dir.name
        record = _build_strategy_record(entry_id, strat_dir, catalog_dir)
        if record:
            strategies.append(record)

    return strategies


def _build_strategy_record(
    entry_id: str,
    validation_dir: Path,
    catalog_dir: Path
) -> Optional[Dict[str, Any]]:
    """Build a complete strategy record from validation and catalog data."""

    record = {
        "entry_id": entry_id,
        "status": "UNKNOWN",
        "strategy_type": "unknown",
        "name": entry_id,
        "summary": "",
        "sharpe": None,
        "median_return": None,
        "consistency": None,
        "max_drawdown": None,
        "sharpe_ci_lower": None,
        "sharpe_ci_upper": None,
        "total_windows": None,
        "profitable_windows": None,
        "determination_reason": "",
        "timestamp": None,
        "validation_path": str(validation_dir),
        "catalog_path": None,
        "error": None,
    }

    # Load determination.json
    determination_file = validation_dir / "determination.json"
    if determination_file.exists():
        try:
            with open(determination_file) as f:
                det = json.load(f)
            record["status"] = det.get("determination", "UNKNOWN")
            record["determination_reason"] = det.get("reason", "")
            record["timestamp"] = det.get("timestamp")
        except Exception as e:
            record["error"] = f"Failed to read determination: {e}"

    # Load walk_forward_results.json
    wf_file = validation_dir / "walk_forward_results.json"
    if wf_file.exists():
        try:
            with open(wf_file) as f:
                wf = json.load(f)

            agg = wf.get("aggregate_metrics", {})
            record["sharpe"] = agg.get("aggregate_sharpe")
            record["median_return"] = agg.get("median_return")
            record["consistency"] = agg.get("consistency")
            record["max_drawdown"] = agg.get("max_drawdown")
            record["sharpe_ci_lower"] = agg.get("sharpe_ci_lower")
            record["sharpe_ci_upper"] = agg.get("sharpe_ci_upper")
            record["total_windows"] = wf.get("n_windows")

            # Count profitable windows
            windows = wf.get("windows", [])
            profitable = sum(1 for w in windows if w.get("total_return", 0) > 0)
            record["profitable_windows"] = profitable

        except Exception as e:
            if not record["error"]:
                record["error"] = f"Failed to read walk_forward_results: {e}"

    # Load catalog entry for metadata
    catalog_file = catalog_dir / f"{entry_id}.json"
    if catalog_file.exists():
        try:
            with open(catalog_file) as f:
                cat = json.load(f)
            record["name"] = cat.get("name", entry_id)
            record["summary"] = cat.get("summary", "")
            record["catalog_path"] = str(catalog_file)

            # Extract strategy type from tags
            tags = cat.get("tags", [])
            strategy_types = [
                "trend_following", "mean_reversion", "momentum_rotation",
                "dual_momentum", "breakout", "volatility", "pairs"
            ]
            for tag in tags:
                if tag in strategy_types:
                    record["strategy_type"] = tag
                    break
        except Exception as e:
            if not record["error"]:
                record["error"] = f"Failed to read catalog: {e}"

    return record


def generate_dashboard(
    strategies: List[Dict[str, Any]],
    output_dir: Path,
    top_n: int = 5
) -> Path:
    """Generate the main dashboard.md file."""

    output_dir.mkdir(parents=True, exist_ok=True)
    dashboard_file = output_dir / "dashboard.md"

    # Calculate stats
    total = len(strategies)
    validated = [s for s in strategies if s["status"] == "VALIDATED"]
    invalidated = [s for s in strategies if s["status"] == "INVALIDATED"]
    pending = [s for s in strategies if s["status"] not in ["VALIDATED", "INVALIDATED"]]

    # Sort validated by Sharpe for leaderboard
    validated_sorted = sorted(
        validated,
        key=lambda x: x.get("sharpe") or 0,
        reverse=True
    )

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Research Kit Dashboard",
        "",
        f"*Last updated: {now}*",
        "",
        "## Quick Stats",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Strategies | {total} |",
        f"| Validated | {len(validated)} ({_pct(len(validated), total)}) |",
        f"| Invalidated | {len(invalidated)} ({_pct(len(invalidated), total)}) |",
        f"| Pending | {len(pending)} |",
        "",
    ]

    # Top N strategies
    if validated_sorted:
        lines.extend([
            f"## Top {min(top_n, len(validated_sorted))} Strategies",
            "",
            "| Rank | Entry | Type | Sharpe | Median Return | MaxDD | Consistency |",
            "|------|-------|------|--------|---------------|-------|-------------|",
        ])

        for i, s in enumerate(validated_sorted[:top_n], 1):
            sharpe = _fmt_num(s.get("sharpe"), 2)
            ret = _fmt_pct(s.get("median_return"))
            dd = _fmt_pct(s.get("max_drawdown"))
            cons = _fmt_pct(s.get("consistency"))
            entry_link = f"[{s['entry_id']}](../validations/{s['entry_id']}/)"
            lines.append(
                f"| {i} | {entry_link} | {s['strategy_type']} | {sharpe} | {ret} | {dd} | {cons} |"
            )

        lines.extend([
            "",
            "[Full leaderboard →](leaderboard.md) | [Export CSV →](exports/validated.csv)",
            "",
        ])

    # Funnel visualization
    lines.extend([
        "## Pipeline Funnel",
        "",
        "```",
        _ascii_bar("Total", total, total),
        _ascii_bar("Validated", len(validated), total),
        _ascii_bar("Invalidated", len(invalidated), total),
        _ascii_bar("Pending", len(pending), total),
        "```",
        "",
        "[View funnel details →](funnel.md)",
        "",
    ])

    # Blockers summary
    blockers = _detect_blockers(strategies)
    if blockers:
        lines.extend([
            "## Blockers",
            "",
            "| Issue | Strategies Affected |",
            "|-------|---------------------|",
        ])
        for issue, affected in blockers[:5]:
            affected_links = ", ".join(
                f"[{e}](../validations/{e}/)" for e in affected[:3]
            )
            if len(affected) > 3:
                affected_links += f" (+{len(affected)-3} more)"
            lines.append(f"| {issue} | {affected_links} |")
        lines.extend([
            "",
            "[View all blockers →](blockers.md)",
            "",
        ])
    else:
        lines.extend([
            "## Blockers",
            "",
            "No blockers detected.",
            "",
        ])

    # Recent activity
    recent = sorted(
        [s for s in strategies if s.get("timestamp")],
        key=lambda x: x["timestamp"],
        reverse=True
    )[:5]

    if recent:
        lines.extend([
            "## Recent Activity",
            "",
            "| Time | Entry | Status |",
            "|------|-------|--------|",
        ])
        for s in recent:
            ts = s["timestamp"][:16].replace("T", " ") if s["timestamp"] else "?"
            icon = "✅" if s["status"] == "VALIDATED" else "❌" if s["status"] == "INVALIDATED" else "⏳"
            entry_link = f"[{s['entry_id']}](../validations/{s['entry_id']}/)"
            lines.append(f"| {ts} | {entry_link} | {icon} {s['status']} |")
        lines.append("")

    lines.extend([
        "---",
        "*Generated by `research status --refresh`*",
    ])

    content = "\n".join(lines)
    dashboard_file.write_text(content)
    logger.info(f"Generated {dashboard_file}")

    return dashboard_file


def generate_leaderboard(
    strategies: List[Dict[str, Any]],
    output_dir: Path,
    sort_by: str = "sharpe"
) -> Path:
    """Generate the full leaderboard.md file."""

    output_dir.mkdir(parents=True, exist_ok=True)
    leaderboard_file = output_dir / "leaderboard.md"

    validated = [s for s in strategies if s["status"] == "VALIDATED"]

    # Sort by specified metric
    sort_key = {
        "sharpe": lambda x: x.get("sharpe") or 0,
        "return": lambda x: x.get("median_return") or 0,
        "consistency": lambda x: x.get("consistency") or 0,
        "drawdown": lambda x: -(x.get("max_drawdown") or 1),  # Lower is better
    }.get(sort_by, lambda x: x.get("sharpe") or 0)

    validated_sorted = sorted(validated, key=sort_key, reverse=True)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Strategy Leaderboard",
        "",
        f"*Last updated: {now}*",
        "",
        f"**{len(validated)} validated strategies** (sorted by {sort_by})",
        "",
        "| Rank | Entry | Name | Type | Sharpe | Return | Consistency | MaxDD | CI Lower |",
        "|------|-------|------|------|--------|--------|-------------|-------|----------|",
    ]

    for i, s in enumerate(validated_sorted, 1):
        entry_link = f"[{s['entry_id']}](../validations/{s['entry_id']}/)"
        name = s.get("name", "")[:25]
        lines.append(
            f"| {i} | {entry_link} | {name} | {s['strategy_type']} | "
            f"{_fmt_num(s.get('sharpe'), 2)} | {_fmt_pct(s.get('median_return'))} | "
            f"{_fmt_pct(s.get('consistency'))} | {_fmt_pct(s.get('max_drawdown'))} | "
            f"{_fmt_num(s.get('sharpe_ci_lower'), 2)} |"
        )

    lines.extend([
        "",
        "[Export CSV →](exports/validated.csv) | [Back to dashboard →](dashboard.md)",
    ])

    content = "\n".join(lines)
    leaderboard_file.write_text(content)
    logger.info(f"Generated {leaderboard_file}")

    return leaderboard_file


def generate_funnel(
    strategies: List[Dict[str, Any]],
    output_dir: Path
) -> Path:
    """Generate funnel.md with detailed pipeline status."""

    output_dir.mkdir(parents=True, exist_ok=True)
    funnel_file = output_dir / "funnel.md"

    validated = [s for s in strategies if s["status"] == "VALIDATED"]
    invalidated = [s for s in strategies if s["status"] == "INVALIDATED"]
    pending = [s for s in strategies if s["status"] not in ["VALIDATED", "INVALIDATED"]]

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Pipeline Funnel",
        "",
        f"*Last updated: {now}*",
        "",
        "## Summary",
        "",
        f"| Status | Count | Percentage |",
        f"|--------|-------|------------|",
        f"| Validated | {len(validated)} | {_pct(len(validated), len(strategies))} |",
        f"| Invalidated | {len(invalidated)} | {_pct(len(invalidated), len(strategies))} |",
        f"| Pending | {len(pending)} | {_pct(len(pending), len(strategies))} |",
        f"| **Total** | **{len(strategies)}** | 100% |",
        "",
    ]

    # Validated list
    lines.extend([
        "## Validated Strategies",
        "",
    ])
    if validated:
        lines.append("| Entry | Type | Sharpe | Reason |")
        lines.append("|-------|------|--------|--------|")
        for s in sorted(validated, key=lambda x: x.get("sharpe") or 0, reverse=True):
            entry_link = f"[{s['entry_id']}](../validations/{s['entry_id']}/)"
            lines.append(
                f"| {entry_link} | {s['strategy_type']} | "
                f"{_fmt_num(s.get('sharpe'), 2)} | {s.get('determination_reason', '')[:40]} |"
            )
        lines.append("")
    else:
        lines.extend(["*No validated strategies yet.*", ""])

    # Invalidated list
    lines.extend([
        "## Invalidated Strategies",
        "",
    ])
    if invalidated:
        lines.append("| Entry | Type | Reason |")
        lines.append("|-------|------|--------|")
        for s in invalidated:
            entry_link = f"[{s['entry_id']}](../validations/{s['entry_id']}/)"
            lines.append(
                f"| {entry_link} | {s['strategy_type']} | {s.get('determination_reason', '')[:50]} |"
            )
        lines.append("")
    else:
        lines.extend(["*No invalidated strategies.*", ""])

    # Pending list
    lines.extend([
        "## Pending Validation",
        "",
    ])
    if pending:
        lines.append("| Entry | Status | Error |")
        lines.append("|-------|--------|-------|")
        for s in pending:
            entry_link = f"[{s['entry_id']}](../validations/{s['entry_id']}/)"
            error = s.get("error", "")[:40] if s.get("error") else "-"
            lines.append(f"| {entry_link} | {s['status']} | {error} |")
        lines.append("")
    else:
        lines.extend(["*No pending strategies.*", ""])

    lines.extend([
        "[Export all →](exports/all_strategies.csv) | [Back to dashboard →](dashboard.md)",
    ])

    content = "\n".join(lines)
    funnel_file.write_text(content)
    logger.info(f"Generated {funnel_file}")

    return funnel_file


def generate_blockers(
    strategies: List[Dict[str, Any]],
    output_dir: Path
) -> Path:
    """Generate blockers.md with data gaps and issues."""

    output_dir.mkdir(parents=True, exist_ok=True)
    blockers_file = output_dir / "blockers.md"

    blockers = _detect_blockers(strategies)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Blockers & Data Gaps",
        "",
        f"*Last updated: {now}*",
        "",
    ]

    if blockers:
        lines.extend([
            "## Issues by Impact",
            "",
            "| Priority | Issue | Strategies Affected | Suggested Action |",
            "|----------|-------|---------------------|------------------|",
        ])

        for i, (issue, affected) in enumerate(blockers, 1):
            affected_links = ", ".join(
                f"[{e}](../validations/{e}/)" for e in affected
            )
            action = _suggest_action(issue)
            lines.append(f"| {i} | {issue} | {affected_links} | {action} |")

        lines.append("")
    else:
        lines.extend([
            "## No Blockers Detected",
            "",
            "All strategies have completed validation or have no known data gaps.",
            "",
        ])

    # Error summary
    errors = [s for s in strategies if s.get("error")]
    if errors:
        lines.extend([
            "## Strategies with Errors",
            "",
            "| Entry | Error |",
            "|-------|-------|",
        ])
        for s in errors:
            entry_link = f"[{s['entry_id']}](../validations/{s['entry_id']}/)"
            lines.append(f"| {entry_link} | {s['error'][:60]} |")
        lines.append("")

    lines.extend([
        "[Back to dashboard →](dashboard.md)",
    ])

    content = "\n".join(lines)
    blockers_file.write_text(content)
    logger.info(f"Generated {blockers_file}")

    return blockers_file


def generate_exports(
    strategies: List[Dict[str, Any]],
    output_dir: Path
) -> Dict[str, Path]:
    """Generate CSV and JSON exports."""

    exports_dir = output_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    files = {}

    # CSV columns
    columns = [
        "entry_id", "status", "strategy_type", "name", "sharpe", "median_return",
        "consistency", "max_drawdown", "sharpe_ci_lower", "sharpe_ci_upper",
        "total_windows", "profitable_windows", "determination_reason", "timestamp"
    ]

    # All strategies CSV
    all_csv = exports_dir / "all_strategies.csv"
    _write_csv(all_csv, strategies, columns)
    files["all_strategies.csv"] = all_csv

    # Validated only
    validated = [s for s in strategies if s["status"] == "VALIDATED"]
    validated_csv = exports_dir / "validated.csv"
    _write_csv(validated_csv, validated, columns)
    files["validated.csv"] = validated_csv

    # Invalidated only
    invalidated = [s for s in strategies if s["status"] == "INVALIDATED"]
    invalidated_csv = exports_dir / "invalidated.csv"
    _write_csv(invalidated_csv, invalidated, columns)
    files["invalidated.csv"] = invalidated_csv

    # Full JSON index
    index_json = exports_dir / "strategy_index.json"
    with open(index_json, "w") as f:
        json.dump({
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_count": len(strategies),
            "validated_count": len(validated),
            "invalidated_count": len(invalidated),
            "strategies": strategies
        }, f, indent=2)
    files["strategy_index.json"] = index_json
    logger.info(f"Generated {index_json}")

    return files


def generate_history_snapshot(
    strategies: List[Dict[str, Any]],
    output_dir: Path
) -> Path:
    """Generate a daily history snapshot."""

    history_dir = output_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    snapshot_file = history_dir / f"{today}.json"

    validated = [s for s in strategies if s["status"] == "VALIDATED"]
    invalidated = [s for s in strategies if s["status"] == "INVALIDATED"]

    # Top 5 by Sharpe
    top5 = sorted(validated, key=lambda x: x.get("sharpe") or 0, reverse=True)[:5]

    snapshot = {
        "date": today,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "counts": {
            "total": len(strategies),
            "validated": len(validated),
            "invalidated": len(invalidated),
        },
        "top_5": [
            {
                "entry_id": s["entry_id"],
                "sharpe": s.get("sharpe"),
                "median_return": s.get("median_return"),
            }
            for s in top5
        ],
    }

    with open(snapshot_file, "w") as f:
        json.dump(snapshot, f, indent=2)

    logger.info(f"Generated history snapshot: {snapshot_file}")
    return snapshot_file


def refresh_all_reports(workspace: Path) -> Dict[str, Path]:
    """
    Refresh all reports from current validation data.

    Main entry point for `research status --refresh`.
    """
    reports_dir = workspace / "reports"

    # Scan all strategies
    logger.info("Scanning strategies...")
    strategies = scan_strategies(workspace)
    logger.info(f"Found {len(strategies)} strategies")

    if not strategies:
        logger.warning("No strategies found. Creating empty reports.")

    files = {}

    # Generate all reports
    files["dashboard"] = generate_dashboard(strategies, reports_dir)
    files["leaderboard"] = generate_leaderboard(strategies, reports_dir)
    files["funnel"] = generate_funnel(strategies, reports_dir)
    files["blockers"] = generate_blockers(strategies, reports_dir)

    # Generate exports
    export_files = generate_exports(strategies, reports_dir)
    files.update(export_files)

    # Generate history snapshot
    files["history"] = generate_history_snapshot(strategies, reports_dir)

    logger.info(f"All reports generated in {reports_dir}")
    return files


# --- Helper functions ---

def _pct(num: int, total: int) -> str:
    """Format as percentage string."""
    if total == 0:
        return "0%"
    return f"{num / total * 100:.0f}%"


def _fmt_num(val: Optional[float], decimals: int = 2) -> str:
    """Format number or return '-'."""
    if val is None:
        return "-"
    return f"{val:.{decimals}f}"


def _fmt_pct(val: Optional[float]) -> str:
    """Format as percentage or return '-'."""
    if val is None:
        return "-"
    return f"{val * 100:.1f}%"


def _ascii_bar(label: str, value: int, max_value: int, width: int = 30) -> str:
    """Create ASCII bar for funnel visualization."""
    if max_value == 0:
        bar_len = 0
    else:
        bar_len = int((value / max_value) * width)
    bar = "█" * bar_len + " " * (width - bar_len)
    return f"{label:15} {bar} {value:3}"


def _write_csv(filepath: Path, data: List[Dict], columns: List[str]):
    """Write data to CSV file."""
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            # Format percentages for readability
            formatted = dict(row)
            for col in ["median_return", "consistency", "max_drawdown"]:
                if formatted.get(col) is not None:
                    formatted[col] = f"{formatted[col] * 100:.2f}%"
            writer.writerow(formatted)
    logger.info(f"Generated {filepath}")


def _detect_blockers(strategies: List[Dict[str, Any]]) -> List[Tuple[str, List[str]]]:
    """
    Detect blockers and data gaps from strategy errors.

    Returns list of (issue, [affected_entry_ids]) sorted by impact.
    """
    # Group by error type
    error_groups: Dict[str, List[str]] = {}

    for s in strategies:
        error = s.get("error")
        if error:
            # Normalize error message
            key = _normalize_error(error)
            if key not in error_groups:
                error_groups[key] = []
            error_groups[key].append(s["entry_id"])

    # Also check for strategies with 0 trades
    zero_trades = [
        s["entry_id"] for s in strategies
        if s.get("status") == "INVALIDATED" and "0 trade" in s.get("determination_reason", "").lower()
    ]
    if zero_trades:
        error_groups["No trades generated"] = zero_trades

    # Sort by number affected (descending)
    sorted_blockers = sorted(error_groups.items(), key=lambda x: len(x[1]), reverse=True)

    return sorted_blockers


def _normalize_error(error: str) -> str:
    """Normalize error message for grouping."""
    error_lower = error.lower()

    if "rate limit" in error_lower or "no spare nodes" in error_lower:
        return "Rate limited by QuantConnect"
    if "data" in error_lower and ("missing" in error_lower or "not found" in error_lower):
        return "Missing data"
    if "vix" in error_lower:
        return "VIX data required"
    if "crypto" in error_lower or "btc" in error_lower:
        return "Crypto data required"
    if "timeout" in error_lower:
        return "Backtest timeout"

    # Return first 50 chars of original if no pattern matched
    return error[:50] if len(error) > 50 else error


def _suggest_action(issue: str) -> str:
    """Suggest action for a blocker."""
    suggestions = {
        "Rate limited by QuantConnect": "Wait and retry, or upgrade QC plan",
        "Missing data": "Check data availability in QC",
        "VIX data required": "Subscribe to CBOE VIX data",
        "Crypto data required": "Add crypto data source",
        "Backtest timeout": "Simplify strategy or increase timeout",
        "No trades generated": "Review strategy logic/signals",
    }
    return suggestions.get(issue, "Investigate error logs")
