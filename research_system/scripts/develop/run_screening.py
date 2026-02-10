"""
Phase 1 Screening Runner

Runs quick backtests on all variants and ranks them by performance.
Uses 2019-2024 period (all assets have full data).
"""

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import concurrent.futures
import re


@dataclass
class BacktestResult:
    """Result from a single backtest."""
    variant_id: str
    success: bool
    total_return: float = 0.0
    cagr: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    total_trades: int = 0
    error: Optional[str] = None


def run_single_backtest(
    project_path: Path,
    start_date: str = "2019-01-01",
    end_date: str = "2024-12-31",
) -> BacktestResult:
    """Run a single backtest via lean CLI."""
    variant_id = project_path.name

    try:
        # Run backtest from parent directory
        cmd = [
            "lean", "cloud", "backtest",
            project_path.name,
            "--push",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout
            cwd=project_path.parent,  # Run from parent directory
        )

        # Parse results from output (check stdout regardless of return code)
        output = result.stdout or ""

        # Check for successful completion (Backtest id present)
        if "Backtest id:" not in output:
            # Debug info
            if result.returncode != 0:
                print(f"  DEBUG: returncode={result.returncode}")
                if result.stderr:
                    print(f"  DEBUG stderr: {result.stderr[:200]}")
            if "Error:" in output or "error" in output.lower():
                error_match = re.search(r'Error:?\s*(.{0,100})', output, re.IGNORECASE)
                error_msg = error_match.group(1) if error_match else "Unknown error"
            else:
                error_msg = f"No backtest ID (code={result.returncode})"
            return BacktestResult(
                variant_id=variant_id,
                success=False,
                error=error_msg,
            )

        # Parse metrics from table output
        metrics = _parse_lean_table_output(output)

        return BacktestResult(
            variant_id=variant_id,
            success=True,
            total_return=metrics.get("total_return", 0.0),
            cagr=metrics.get("cagr", 0.0),
            sharpe=metrics.get("sharpe", 0.0),
            max_drawdown=abs(metrics.get("drawdown", 0.0)),
            total_trades=int(metrics.get("total_trades", 0)),
        )

    except subprocess.TimeoutExpired:
        return BacktestResult(
            variant_id=variant_id,
            success=False,
            error="Timeout",
        )
    except Exception as e:
        return BacktestResult(
            variant_id=variant_id,
            success=False,
            error=str(e)[:500],
        )


def _extract_metric(text: str, pattern: str) -> Optional[float]:
    """Extract numeric metric from text using regex."""
    match = re.search(pattern, text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _parse_lean_table_output(output: str) -> Dict[str, float]:
    """Parse the table output from lean CLI."""
    metrics = {}

    # Look for metric patterns in table format
    # Format: │ Metric Name │ Value │
    patterns = {
        "sharpe": r"Sharpe Ratio\s*│\s*([-\d.]+)",
        "cagr": r"Compounding Annual\s*│\s*([-\d.]+)%?\s*\n\s*│\s*Return",
        "drawdown": r"Drawdown\s*│\s*([-\d.]+)%",
        "total_return": r"Net Profit\s*│\s*([-\d.]+)%",
        "total_trades": r"Total Orders\s*│\s*(\d+)",
    }

    # Alternative patterns for different output formats
    alt_patterns = {
        "sharpe": r"│\s*Sharpe Ratio\s*│\s*([-\d.]+)\s*│",
        "cagr": r"│\s*Compounding Annual Return\s*│\s*([-\d.]+)%?\s*│",
        "cagr_alt": r"Compounding Annual\s+.*?([-\d.]+)%",
        "drawdown": r"│\s*Drawdown\s*│\s*([-\d.]+)%?\s*│",
        "total_return": r"│\s*Net Profit\s*│\s*([-\d.]+)%?\s*│",
        "total_trades": r"│\s*Total Orders\s*│\s*(\d+)\s*│",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        if match:
            try:
                metrics[key] = float(match.group(1))
            except ValueError:
                pass

    # Try alternative patterns if primary ones failed
    for key in ["sharpe", "cagr", "drawdown", "total_return", "total_trades"]:
        if key not in metrics or metrics[key] == 0:
            alt_key = key if key in alt_patterns else f"{key}_alt"
            if alt_key in alt_patterns:
                match = re.search(alt_patterns[alt_key], output, re.IGNORECASE | re.MULTILINE)
                if match:
                    try:
                        metrics[key] = float(match.group(1))
                    except ValueError:
                        pass

    return metrics


def run_phase1_screening(
    variants_dir: Path,
    max_concurrent: int = 1,  # Run sequentially for reliability
    limit: Optional[int] = None,
) -> List[BacktestResult]:
    """Run Phase 1 screening on all variants.

    Args:
        variants_dir: Directory containing variant projects
        max_concurrent: Max concurrent backtests (1 = sequential)
        limit: Optional limit on number of variants to test

    Returns:
        List of BacktestResult sorted by Sharpe ratio
    """
    # Load variant index
    index_path = variants_dir / "variant_index.json"
    with open(index_path) as f:
        index = json.load(f)

    variants = index["variants"]
    if limit:
        variants = variants[:limit]

    print(f"Running Phase 1 screening on {len(variants)} variants...")
    print(f"Running sequentially for reliability")

    results = []
    failed = []

    # Run backtests sequentially
    for i, variant in enumerate(variants):
        project_path = Path(variant["project_dir"])
        try:
            result = run_single_backtest(project_path)
            if result.success:
                results.append(result)
                print(f"[{i+1}/{len(variants)}] {result.variant_id}: "
                      f"Sharpe={result.sharpe:.2f}, CAGR={result.cagr:.1f}%")
            else:
                failed.append(result)
                print(f"[{i+1}/{len(variants)}] {result.variant_id}: FAILED - {result.error[:80] if result.error else 'Unknown'}")
        except Exception as e:
            print(f"[{i+1}/{len(variants)}] {variant['variant_id']}: ERROR - {e}")

        # Brief pause between backtests
        time.sleep(2)

    print(f"\nCompleted: {len(results)} successful, {len(failed)} failed")

    # Sort by Sharpe ratio
    results.sort(key=lambda x: x.sharpe, reverse=True)

    return results


def save_screening_results(
    results: List[BacktestResult],
    output_path: Path,
    variants_dir: Path,
):
    """Save screening results to JSON."""
    # Load original index for metadata
    index_path = variants_dir / "variant_index.json"
    with open(index_path) as f:
        index = json.load(f)

    variant_meta = {v["variant_id"]: v for v in index["variants"]}

    results_data = {
        "screening_phase": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_variants": len(index["variants"]),
        "successful_backtests": len(results),
        "results": [
            {
                "rank": i + 1,
                "variant_id": r.variant_id,
                "sharpe": r.sharpe,
                "cagr": r.cagr,
                "total_return": r.total_return,
                "max_drawdown": r.max_drawdown,
                "total_trades": r.total_trades,
                **variant_meta.get(r.variant_id, {}),
            }
            for i, r in enumerate(results)
        ],
    }

    output_path.write_text(json.dumps(results_data, indent=2))
    print(f"\nResults saved to: {output_path}")


def print_top_performers(results: List[BacktestResult], n: int = 20):
    """Print top N performers."""
    print(f"\n{'='*60}")
    print(f"TOP {n} PERFORMERS BY SHARPE RATIO")
    print(f"{'='*60}")
    print(f"{'Rank':<5} {'Variant ID':<30} {'Sharpe':>8} {'CAGR':>8} {'MaxDD':>8}")
    print("-" * 60)

    for i, r in enumerate(results[:n]):
        print(f"{i+1:<5} {r.variant_id:<30} {r.sharpe:>8.2f} {r.cagr:>7.1f}% {r.max_drawdown:>7.1f}%")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python run_screening.py <workspace_path> [--limit N]")
        sys.exit(1)

    workspace_path = Path(sys.argv[1])
    variants_dir = workspace_path / "validations" / "rotation_variants"

    limit = None
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    if not variants_dir.exists():
        print(f"Variants directory not found: {variants_dir}")
        print("Run generate_variants.py first")
        sys.exit(1)

    results = run_phase1_screening(variants_dir, max_concurrent=5, limit=limit)

    if results:
        output_path = workspace_path / "validations" / "screening_results_phase1.json"
        save_screening_results(results, output_path, variants_dir)
        print_top_performers(results, n=20)
