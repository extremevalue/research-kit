"""
QuantConnect API client for the Research Validation System.

Wraps the LEAN CLI to:
- Push projects to QC cloud
- Run backtests
- Retrieve results
- Manage Object Store data

Requires: lean-cli (pip install lean)
"""

import json
import subprocess
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .logging_config import get_logger

logger = get_logger("qc-client")


@dataclass
class BacktestResult:
    """Parsed backtest result from QC."""
    backtest_id: str
    project_id: str
    name: str
    status: str
    cagr: float
    sharpe: float
    max_drawdown: float
    total_trades: int
    win_rate: float
    alpha: Optional[float] = None
    beta: Optional[float] = None
    sortino: Optional[float] = None
    raw_response: Optional[Dict] = None


class QCClient:
    """Client for interacting with QuantConnect via LEAN CLI."""

    def __init__(self, project_prefix: str = "rv_"):
        """
        Initialize QC client.

        Args:
            project_prefix: Prefix for QC project names (default: rv_ for research validation)
        """
        self.project_prefix = project_prefix
        self._verify_lean_cli()

    def _verify_lean_cli(self):
        """Verify LEAN CLI is installed and authenticated."""
        try:
            result = subprocess.run(
                ["lean", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError("LEAN CLI not properly installed")
            logger.debug(f"LEAN CLI version: {result.stdout.strip()}")
        except FileNotFoundError:
            raise RuntimeError("LEAN CLI not found. Install with: pip install lean")

    def _run_command(self, args: List[str], cwd: Optional[Path] = None) -> Tuple[bool, str, str]:
        """
        Run a lean CLI command.

        Returns:
            Tuple of (success, stdout, stderr)
        """
        cmd = ["lean"] + args
        logger.debug(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd
        )

        return result.returncode == 0, result.stdout, result.stderr

    def push_project(self, project_path: Path) -> bool:
        """
        Push a local project to QC cloud.

        Args:
            project_path: Path to project directory containing main.py

        Returns:
            True if successful
        """
        if not project_path.exists():
            raise FileNotFoundError(f"Project path not found: {project_path}")

        if not (project_path / "main.py").exists():
            raise FileNotFoundError(f"No main.py found in: {project_path}")

        success, stdout, stderr = self._run_command(
            ["cloud", "push", "--project", str(project_path)]
        )

        if success:
            logger.info(f"Pushed project: {project_path.name}")
        else:
            logger.error(f"Failed to push project: {stderr}")

        return success

    def run_backtest(
        self,
        project_path: Path,
        name: Optional[str] = None
    ) -> Optional[str]:
        """
        Run a backtest on QC cloud.

        Args:
            project_path: Path to project directory
            name: Optional backtest name

        Returns:
            Backtest ID if successful, None otherwise
        """
        # First push the project
        if not self.push_project(project_path):
            return None

        # Build command
        args = ["cloud", "backtest", str(project_path)]
        if name:
            args.extend(["--name", name])

        success, stdout, stderr = self._run_command(args)

        if not success:
            logger.error(f"Backtest failed: {stderr}")
            return None

        # Parse backtest ID from output
        # Output format: "Backtest id: xxxxxxxx"
        match = re.search(r"Backtest id:\s*(\S+)", stdout)
        if match:
            backtest_id = match.group(1)
            logger.info(f"Backtest started: {backtest_id}")
            return backtest_id

        logger.error("Could not parse backtest ID from output")
        return None

    def get_backtest_results(
        self,
        project_path: Path,
        backtest_id: str
    ) -> Optional[BacktestResult]:
        """
        Get results from a completed backtest.

        Args:
            project_path: Path to project directory
            backtest_id: Backtest ID to retrieve

        Returns:
            BacktestResult if successful
        """
        args = ["cloud", "backtest", str(project_path), "--backtest", backtest_id]

        success, stdout, stderr = self._run_command(args)

        if not success:
            logger.error(f"Failed to get backtest results: {stderr}")
            return None

        # Parse the JSON output
        try:
            # The lean CLI outputs JSON with results
            # Extract JSON from output (it may have other text around it)
            json_match = re.search(r'\{.*\}', stdout, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return self._parse_backtest_result(data, backtest_id)
        except json.JSONDecodeError:
            logger.error("Failed to parse backtest results JSON")

        return None

    def _parse_backtest_result(self, data: Dict[str, Any], backtest_id: str) -> BacktestResult:
        """Parse raw QC response into BacktestResult."""
        stats = data.get("Statistics", {})

        def parse_pct(value: str) -> float:
            """Parse percentage string like '12.34%' to 12.34"""
            if isinstance(value, (int, float)):
                return float(value)
            return float(value.replace("%", "").replace(",", ""))

        def parse_num(value: str) -> float:
            """Parse number string"""
            if isinstance(value, (int, float)):
                return float(value)
            return float(value.replace(",", ""))

        return BacktestResult(
            backtest_id=backtest_id,
            project_id=data.get("ProjectId", ""),
            name=data.get("Name", ""),
            status=data.get("Status", ""),
            cagr=parse_pct(stats.get("Compounding Annual Return", "0%")),
            sharpe=parse_num(stats.get("Sharpe Ratio", "0")),
            max_drawdown=parse_pct(stats.get("Drawdown", "0%")),
            total_trades=int(parse_num(stats.get("Total Orders", "0"))),
            win_rate=parse_pct(stats.get("Win Rate", "0%")) / 100,  # Convert to 0-1
            alpha=parse_num(stats.get("Alpha", "0")) if "Alpha" in stats else None,
            beta=parse_num(stats.get("Beta", "0")) if "Beta" in stats else None,
            raw_response=data
        )

    def upload_to_object_store(
        self,
        local_path: Path,
        object_key: str
    ) -> bool:
        """
        Upload a file to QC Object Store.

        Args:
            local_path: Path to local file
            object_key: Key in object store (e.g., 'mcclellan/mcclellan_osc.csv')

        Returns:
            True if successful
        """
        if not local_path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")

        success, stdout, stderr = self._run_command([
            "cloud", "object-store", "set",
            object_key, str(local_path)
        ])

        if success:
            logger.info(f"Uploaded to Object Store: {object_key}")
        else:
            logger.error(f"Failed to upload: {stderr}")

        return success

    def download_from_object_store(
        self,
        object_key: str,
        local_path: Path
    ) -> bool:
        """
        Download a file from QC Object Store.

        Args:
            object_key: Key in object store
            local_path: Where to save locally

        Returns:
            True if successful
        """
        success, stdout, stderr = self._run_command([
            "cloud", "object-store", "get",
            object_key, str(local_path)
        ])

        if success:
            logger.info(f"Downloaded from Object Store: {object_key} -> {local_path}")
        else:
            logger.error(f"Failed to download: {stderr}")

        return success

    def list_projects(self) -> List[Dict[str, str]]:
        """
        List all QC cloud projects.

        Returns:
            List of project info dicts
        """
        success, stdout, stderr = self._run_command(["cloud", "project", "list"])

        if not success:
            logger.error(f"Failed to list projects: {stderr}")
            return []

        # Parse project list (format varies, this is simplified)
        projects = []
        for line in stdout.strip().split("\n"):
            if line.strip():
                projects.append({"name": line.strip()})

        return projects


def run_backtest_and_wait(
    project_path: Path,
    name: Optional[str] = None,
    timeout_seconds: int = 300
) -> Optional[BacktestResult]:
    """
    Convenience function to run backtest and wait for results.

    Args:
        project_path: Path to project
        name: Optional backtest name
        timeout_seconds: Max time to wait for completion

    Returns:
        BacktestResult if successful
    """
    import time

    client = QCClient()
    backtest_id = client.run_backtest(project_path, name)

    if not backtest_id:
        return None

    # Poll for completion
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        result = client.get_backtest_results(project_path, backtest_id)
        if result and result.status == "Completed":
            return result

        logger.debug(f"Waiting for backtest completion... ({int(time.time() - start_time)}s)")
        time.sleep(10)

    logger.error(f"Backtest timed out after {timeout_seconds}s")
    return None


if __name__ == "__main__":
    # Self-test (requires authenticated lean CLI)
    print("QC Client self-test")
    print("=" * 40)

    try:
        client = QCClient()
        print("LEAN CLI verified")

        # List projects
        projects = client.list_projects()
        print(f"Found {len(projects)} projects")

    except RuntimeError as e:
        print(f"Error: {e}")
        print("Make sure lean CLI is installed: pip install lean")
        print("And authenticated: lean login")
