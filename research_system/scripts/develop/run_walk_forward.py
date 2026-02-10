"""
Walk-Forward Validation for Rotation Strategy Variants

Since DBMF only has data from 2019, we use a modified walk-forward:
- 4 windows: 2020, 2021, 2022, 2023, 2024 test years
- 1-year training before each test period
- This tests true out-of-sample performance

Uses QuantConnect API to set backtest dates directly, bypassing the cloud
project's default date settings which override SetStartDate/SetEndDate in code.
"""

import hashlib
import json
import subprocess
import re
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


class QCApi:
    """QuantConnect API client with proper authentication."""

    BASE_URL = "https://www.quantconnect.com/api/v2"

    def __init__(self, credentials_path: Path = None):
        """Initialize with credentials from lean config."""
        if credentials_path is None:
            credentials_path = Path.home() / ".lean" / "credentials"

        with open(credentials_path) as f:
            creds = json.load(f)

        self.user_id = creds["user-id"]
        self.api_token = creds["api-token"]

    def _get_auth(self):
        """Generate timestamped authentication."""
        timestamp = str(int(time.time()))
        token_hash = hashlib.sha256(
            f"{self.api_token}:{timestamp}".encode()
        ).hexdigest()
        return (self.user_id, token_hash), {"Timestamp": timestamp}

    def _request(self, method: str, endpoint: str, **kwargs):
        """Make authenticated API request."""
        auth, headers = self._get_auth()
        url = f"{self.BASE_URL}/{endpoint}"
        resp = requests.request(method, url, auth=auth, headers=headers, **kwargs)
        return resp.json()

    def list_projects(self) -> List[Dict]:
        """List all projects."""
        data = self._request("GET", "projects/read")
        if data.get("success"):
            return data.get("projects", [])
        return []

    def get_project_by_name(self, name: str) -> Optional[Dict]:
        """Find project by name."""
        projects = self.list_projects()
        for p in projects:
            if p.get("name") == name:
                return p
        return None

    def compile_project(self, project_id: int) -> Optional[str]:
        """Compile a project and return compile ID."""
        data = self._request("POST", "compile/create", data={"projectId": project_id})
        if data.get("success"):
            return data.get("compileId")
        return None

    def create_backtest(
        self,
        project_id: int,
        compile_id: str,
        name: str,
        start_date: str,
        end_date: str,
    ) -> Optional[str]:
        """Create a backtest with explicit date range. Returns backtest ID."""
        data = self._request(
            "POST",
            "backtests/create",
            data={
                "projectId": project_id,
                "compileId": compile_id,
                "backtestName": name,
                "startDate": f"{start_date} 00:00:00",
                "endDate": f"{end_date} 23:59:59",
            },
        )
        if data.get("success"):
            return data.get("backtest", {}).get("backtestId")
        return None

    def get_backtest(self, project_id: int, backtest_id: str) -> Optional[Dict]:
        """Get backtest details."""
        data = self._request(
            "POST",
            "backtests/read",
            data={"projectId": project_id, "backtestId": backtest_id},
        )
        if data.get("success"):
            return data.get("backtest")
        return None

    def wait_for_backtest(
        self,
        project_id: int,
        backtest_id: str,
        timeout: int = 300,
        poll_interval: int = 3,
    ) -> Optional[Dict]:
        """Wait for backtest completion and return results."""
        start = time.time()
        while time.time() - start < timeout:
            bt = self.get_backtest(project_id, backtest_id)
            if bt and bt.get("completed"):
                return bt
            time.sleep(poll_interval)
        return None


# Global API client (initialized on first use)
_api_client: Optional[QCApi] = None


def get_api() -> QCApi:
    """Get or create API client."""
    global _api_client
    if _api_client is None:
        _api_client = QCApi()
    return _api_client


@dataclass
class WindowResult:
    """Results from a single test window."""
    window_id: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    test_year: int
    success: bool
    total_return: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    error: Optional[str] = None


@dataclass
class WalkForwardResult:
    """Aggregate walk-forward results."""
    variant_id: str
    n_windows: int
    windows: List[WindowResult]
    median_return: float
    consistency: float  # % profitable windows
    aggregate_sharpe: float
    max_drawdown: float
    passed: bool
    determination: str


# Walk-forward windows (adjusted for DBMF availability)
# Using 2yr train / 1yr test to maximize windows
WALK_FORWARD_WINDOWS = [
    {"id": 1, "train_start": "2019-01-01", "train_end": "2020-12-31", "test_start": "2021-01-01", "test_end": "2021-12-31", "test_year": 2021},
    {"id": 2, "train_start": "2020-01-01", "train_end": "2021-12-31", "test_start": "2022-01-01", "test_end": "2022-12-31", "test_year": 2022},
    {"id": 3, "train_start": "2021-01-01", "train_end": "2022-12-31", "test_start": "2023-01-01", "test_end": "2023-12-31", "test_year": 2023},
    {"id": 4, "train_start": "2022-01-01", "train_end": "2023-12-31", "test_start": "2024-01-01", "test_end": "2024-12-31", "test_year": 2024},
]

# Gates (from ARCHITECTURE.md)
# All values in percentage form where applicable
GATES = {
    "median_return_min": 0.0,     # > 0% return
    "consistency_min": 0.50,      # >= 50% profitable windows (as decimal ratio)
    "sharpe_min": 0.3,            # > 0.3 Sharpe ratio
    "max_drawdown_max": 50.0,     # < 50% max drawdown (in percentage form)
}


def create_window_project(
    source_project: Path,
    output_dir: Path,
    window: Dict,
) -> Path:
    """Create a copy of the project for a walk-forward window.

    Note: Dates are NOT injected into code - they're set via the API
    when creating the backtest. This is because QuantConnect cloud
    ignores SetStartDate/SetEndDate in code.
    """
    window_id = window["id"]
    test_year = window["test_year"]

    # Create output directory
    project_name = f"{source_project.name}_w{window_id}"
    project_dir = output_dir / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Copy main.py unchanged (dates set via API, not code)
    main_py = source_project / "main.py"
    (project_dir / "main.py").write_text(main_py.read_text())

    # Copy config.json WITHOUT cloud-id (forces new cloud project creation)
    config_src = source_project / "config.json"
    if config_src.exists():
        config = json.loads(config_src.read_text())
        config["description"] = f"{config.get('description', '')} - Window {window_id} (Test {test_year})"
        config.pop("cloud-id", None)
        (project_dir / "config.json").write_text(json.dumps(config, indent=2))

    return project_dir


def run_window_backtest(project_path: Path) -> WindowResult:
    """Run backtest for a single window using QuantConnect API.

    Uses the API to set explicit date ranges, which bypasses the cloud
    project's default date settings that would otherwise override code dates.
    """
    window_id = int(project_path.name.split("_w")[-1])
    window = WALK_FORWARD_WINDOWS[window_id - 1]

    def make_result(success: bool, error: str = None, **kwargs):
        return WindowResult(
            window_id=window_id,
            train_start=window["train_start"],
            train_end=window["train_end"],
            test_start=window["test_start"],
            test_end=window["test_end"],
            test_year=window["test_year"],
            success=success,
            error=error,
            **kwargs,
        )

    try:
        api = get_api()

        # Step 1: Push project to cloud (creates project if needed)
        cmd = ["lean", "cloud", "push", "--project", project_path.name]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_path.parent,
        )
        if result.returncode != 0:
            return make_result(False, f"Push failed: {result.stderr[:100]}")

        # Step 2: Get project ID from cloud
        project = api.get_project_by_name(project_path.name)
        if not project:
            return make_result(False, "Project not found in cloud after push")
        project_id = project["projectId"]

        # Step 3: Compile project
        compile_id = api.compile_project(project_id)
        if not compile_id:
            return make_result(False, "Compilation failed")

        # Small delay for compilation
        time.sleep(2)

        # Step 4: Create backtest with explicit date range
        ts = int(time.time())
        backtest_name = f"wf_w{window_id}_{window['test_year']}_{ts}"
        backtest_id = api.create_backtest(
            project_id=project_id,
            compile_id=compile_id,
            name=backtest_name,
            start_date=window["test_start"],
            end_date=window["test_end"],
        )
        if not backtest_id:
            return make_result(False, "Backtest creation failed")

        # Step 5: Wait for completion
        bt = api.wait_for_backtest(project_id, backtest_id, timeout=300)
        if not bt:
            return make_result(False, "Backtest timed out")

        if bt.get("error"):
            return make_result(False, f"Backtest error: {bt['error'][:100]}")

        # Step 6: Extract metrics from API response
        stats = bt.get("statistics", {})
        metrics = _parse_api_metrics(stats)

        return make_result(
            True,
            total_return=metrics.get("total_return", 0.0),
            sharpe=metrics.get("sharpe", 0.0),
            max_drawdown=metrics.get("max_drawdown", 0.0),
        )

    except Exception as e:
        return make_result(False, str(e)[:200])


def _parse_api_metrics(stats: Dict) -> Dict[str, float]:
    """Parse metrics from QuantConnect API backtest statistics.

    Note: All values are returned as percentages for consistency with display.
    Gates are also defined in percentage form.
    """
    metrics = {}

    # Net Profit (API returns as "14.306%" string) - keep as percentage
    net_profit = stats.get("Net Profit", "0%")
    if isinstance(net_profit, str):
        net_profit = net_profit.replace("%", "").strip()
    try:
        metrics["total_return"] = float(net_profit)
    except (ValueError, TypeError):
        pass

    # Sharpe Ratio
    sharpe = stats.get("Sharpe Ratio", "0")
    try:
        metrics["sharpe"] = float(sharpe)
    except (ValueError, TypeError):
        pass

    # Drawdown (API returns as "16.800%" string) - keep as percentage
    drawdown = stats.get("Drawdown", "0%")
    if isinstance(drawdown, str):
        drawdown = drawdown.replace("%", "").strip()
    try:
        metrics["max_drawdown"] = abs(float(drawdown))
    except (ValueError, TypeError):
        pass

    return metrics


def _parse_metrics(output: str) -> Dict[str, float]:
    """Parse metrics from lean CLI output (legacy, kept for compatibility)."""
    metrics = {}

    # Sharpe
    match = re.search(r"Sharpe Ratio\s*│\s*([-\d.]+)", output)
    if match:
        try:
            metrics["sharpe"] = float(match.group(1))
        except:
            pass

    # Total Return
    match = re.search(r"Net Profit\s*│\s*([-\d.]+)%", output)
    if match:
        try:
            metrics["total_return"] = float(match.group(1))
        except:
            pass

    # Max Drawdown
    match = re.search(r"Drawdown\s*│\s*([-\d.]+)%", output)
    if match:
        try:
            metrics["max_drawdown"] = abs(float(match.group(1)))
        except:
            pass

    return metrics


def run_walk_forward_validation(
    variant_id: str,
    source_project: Path,
    output_dir: Path,
) -> WalkForwardResult:
    """Run walk-forward validation for a single variant."""
    print(f"\nRunning walk-forward for {variant_id}...")

    windows_dir = output_dir / f"{variant_id}_walkforward"
    windows_dir.mkdir(parents=True, exist_ok=True)

    window_results = []

    for window in WALK_FORWARD_WINDOWS:
        print(f"  Window {window['id']}: Test year {window['test_year']}...", end=" ", flush=True)

        # Create window project
        project_path = create_window_project(source_project, windows_dir, window)

        # Run backtest
        result = run_window_backtest(project_path)
        window_results.append(result)

        if result.success:
            print(f"Return: {result.total_return:+.1f}%, Sharpe: {result.sharpe:.2f}")
        else:
            print(f"FAILED: {result.error}")

        time.sleep(2)  # Rate limiting

    # Calculate aggregate metrics
    successful_windows = [w for w in window_results if w.success]

    if not successful_windows:
        return WalkForwardResult(
            variant_id=variant_id,
            n_windows=len(WALK_FORWARD_WINDOWS),
            windows=window_results,
            median_return=0.0,
            consistency=0.0,
            aggregate_sharpe=0.0,
            max_drawdown=100.0,
            passed=False,
            determination="FAILED",
        )

    returns = [w.total_return for w in successful_windows]
    sharpes = [w.sharpe for w in successful_windows]
    drawdowns = [w.max_drawdown for w in successful_windows]

    median_return = sorted(returns)[len(returns) // 2]
    consistency = sum(1 for r in returns if r > 0) / len(returns)
    aggregate_sharpe = sum(sharpes) / len(sharpes)
    max_drawdown = max(drawdowns)

    # Check gates
    passed = (
        median_return > GATES["median_return_min"] and
        consistency >= GATES["consistency_min"] and
        aggregate_sharpe > GATES["sharpe_min"] and
        max_drawdown < GATES["max_drawdown_max"]
    )

    determination = "VALIDATED" if passed else "INVALIDATED"

    return WalkForwardResult(
        variant_id=variant_id,
        n_windows=len(WALK_FORWARD_WINDOWS),
        windows=window_results,
        median_return=median_return,
        consistency=consistency,
        aggregate_sharpe=aggregate_sharpe,
        max_drawdown=max_drawdown,
        passed=passed,
        determination=determination,
    )


def run_top_n_validation(
    screening_results_path: Path,
    variants_dir: Path,
    output_dir: Path,
    n: int = 10,
) -> List[WalkForwardResult]:
    """Run walk-forward on top N variants from screening."""
    # Load screening results
    with open(screening_results_path) as f:
        screening = json.load(f)

    top_n = screening["results"][:n]

    print(f"Running walk-forward validation on top {n} variants...")
    print("=" * 60)

    results = []

    for i, variant_data in enumerate(top_n):
        variant_id = variant_data["variant_id"]
        source_project = variants_dir / variant_id

        if not source_project.exists():
            print(f"[{i+1}/{n}] {variant_id}: Project not found, skipping")
            continue

        result = run_walk_forward_validation(variant_id, source_project, output_dir)
        results.append(result)

        print(f"  --> {result.determination}: "
              f"Median Return {result.median_return:+.1f}%, "
              f"Consistency {result.consistency*100:.0f}%, "
              f"Sharpe {result.aggregate_sharpe:.2f}, "
              f"Max DD {result.max_drawdown:.1f}%")

    # Save results
    results_path = output_dir / "walk_forward_results.json"
    results_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_variants": len(results),
        "validated": sum(1 for r in results if r.passed),
        "results": [
            {
                "variant_id": r.variant_id,
                "determination": r.determination,
                "median_return": r.median_return,
                "consistency": r.consistency,
                "aggregate_sharpe": r.aggregate_sharpe,
                "max_drawdown": r.max_drawdown,
                "windows": [
                    {
                        "window_id": w.window_id,
                        "test_year": w.test_year,
                        "success": w.success,
                        "total_return": w.total_return,
                        "sharpe": w.sharpe,
                        "max_drawdown": w.max_drawdown,
                    }
                    for w in r.windows
                ],
            }
            for r in results
        ],
    }
    results_path.write_text(json.dumps(results_data, indent=2))

    print(f"\nResults saved to: {results_path}")

    # Summary
    print("\n" + "=" * 60)
    print("WALK-FORWARD VALIDATION SUMMARY")
    print("=" * 60)
    validated = [r for r in results if r.passed]
    print(f"Validated: {len(validated)}/{len(results)}")
    if validated:
        print("\nValidated variants:")
        for r in validated:
            print(f"  {r.variant_id}: Sharpe {r.aggregate_sharpe:.2f}, "
                  f"Consistency {r.consistency*100:.0f}%, Max DD {r.max_drawdown:.1f}%")

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python run_walk_forward.py <workspace_path> [--top N]")
        sys.exit(1)

    workspace_path = Path(sys.argv[1])
    n = 10
    if "--top" in sys.argv:
        idx = sys.argv.index("--top")
        if idx + 1 < len(sys.argv):
            n = int(sys.argv[idx + 1])

    screening_results = workspace_path / "validations" / "screening_results_phase1.json"
    variants_dir = workspace_path / "validations" / "rotation_variants"
    output_dir = workspace_path / "validations" / "walk_forward"

    results = run_top_n_validation(screening_results, variants_dir, output_dir, n=n)
