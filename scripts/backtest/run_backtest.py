"""
Run backtests on QuantConnect using LEAN CLI.

This script:
1. Generates QC algorithm from template
2. Pushes to QC cloud
3. Runs backtest
4. Extracts results

Usage:
    from scripts.backtest.run_backtest import run_backtest
    result = run_backtest("IND-002", hypothesis, test_type="is")
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging_config import get_logger
from utils.qc_client import QCClient
from data.check_availability import check_data_requirements, DataRegistry

logger = get_logger("run-backtest")

# Paths
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
VALIDATIONS_DIR = Path(__file__).parent.parent.parent / "validations"


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""
    component_id: str
    name: str
    test_type: str  # "is" or "oos"
    start_date: str
    end_date: str
    template: str  # Template name (base_algorithm, filter_test, etc.)
    data_sources: List[Dict[str, Any]]
    parameters: Dict[str, Any]
    initial_capital: int = 100000
    benchmark: str = "SPY"

    # Filter-specific settings
    filter_indicator: Optional[str] = None
    filter_column: Optional[str] = None
    filter_threshold: Optional[float] = None
    filter_direction: Optional[str] = None
    filter_role: Optional[str] = None
    base_strategy: Optional[str] = None


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    component_id: str
    test_type: str
    success: bool
    backtest_id: Optional[str] = None
    project_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    # Performance metrics
    sharpe_ratio: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None
    cagr: Optional[float] = None
    max_drawdown: Optional[float] = None
    total_trades: Optional[int] = None
    win_rate: Optional[float] = None
    total_days: Optional[int] = None

    # Raw results
    raw_results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "test_type": self.test_type,
            "success": self.success,
            "backtest_id": self.backtest_id,
            "project_id": self.project_id,
            "timestamp": self.timestamp,
            "sharpe_ratio": self.sharpe_ratio,
            "alpha": self.alpha,
            "beta": self.beta,
            "cagr": self.cagr,
            "max_drawdown": self.max_drawdown,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "total_days": self.total_days,
            "raw_results": self.raw_results,
            "error": self.error
        }


def generate_algorithm(config: BacktestConfig, output_dir: Path) -> Path:
    """
    Generate QC algorithm from template.

    Args:
        config: Backtest configuration
        output_dir: Where to write the algorithm

    Returns:
        Path to generated main.py
    """
    # Setup Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True
    )

    template_file = f"{config.template}.py.j2"
    template = env.get_template(template_file)

    # Prepare template context
    context = {
        "component_id": config.component_id,
        "name": config.name,
        "test_type": config.test_type,
        "start_date": config.start_date,
        "end_date": config.end_date,
        "initial_capital": config.initial_capital,
        "benchmark": config.benchmark,
        "data_sources": config.data_sources,
        "parameters": config.parameters,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    # Add filter-specific context if applicable
    if config.filter_indicator:
        context.update({
            "filter_indicator": config.filter_indicator,
            "filter_column": config.filter_column,
            "filter_threshold": config.filter_threshold,
            "filter_direction": config.filter_direction,
            "filter_role": config.filter_role,
            "base_strategy": config.base_strategy,
        })

    # Render template
    algorithm_code = template.render(**context)

    # Write to output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    main_py = output_dir / "main.py"

    with open(main_py, 'w') as f:
        f.write(algorithm_code)

    logger.info(f"Generated algorithm at {main_py}")

    # Also save config
    config_file = output_dir / "config.json"
    with open(config_file, 'w') as f:
        json.dump({
            "component_id": config.component_id,
            "test_type": config.test_type,
            "template": config.template,
            "start_date": config.start_date,
            "end_date": config.end_date,
            "parameters": config.parameters,
            "data_sources": [{"id": ds["id"], "source": ds["source"]} for ds in config.data_sources],
            "generated_at": context["generated_at"]
        }, f, indent=2)

    return main_py


def prepare_data_sources(data_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Prepare data source configs from registry.

    Args:
        data_ids: List of data source IDs

    Returns:
        List of data source configs for template
    """
    registry = DataRegistry()
    data_check = check_data_requirements(data_ids)

    sources = []
    for check in data_check.checks:
        if not check.available:
            logger.warning(f"Data source not available: {check.data_id}")
            continue

        source = registry.get_source(check.data_id)
        if not source:
            continue

        source_config = {
            "id": check.data_id,
            "name": source.get("name", check.data_id),
            "source": check.source,
            "key": check.key_or_path,
            "column_indices": source.get("column_indices", {}),
            "date_format": source.get("date_format", "%Y-%m-%d"),
            "min_columns": len(source.get("columns", [])),
        }
        sources.append(source_config)

    return sources


def run_local_backtest(project_dir: Path) -> BacktestResult:
    """
    Run backtest locally using LEAN CLI.

    Args:
        project_dir: Directory containing main.py

    Returns:
        BacktestResult
    """
    config_file = project_dir / "config.json"
    with open(config_file, 'r') as f:
        config = json.load(f)

    result = BacktestResult(
        component_id=config["component_id"],
        test_type=config["test_type"],
        success=False
    )

    try:
        # Run LEAN backtest
        cmd = ["lean", "backtest", str(project_dir)]
        logger.info(f"Running: {' '.join(cmd)}")

        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if process.returncode != 0:
            result.error = f"Backtest failed: {process.stderr}"
            logger.error(result.error)
            return result

        # Parse results from output directory
        results_dir = project_dir / "backtests"
        if results_dir.exists():
            # Find most recent backtest
            backtest_dirs = sorted(results_dir.iterdir(), reverse=True)
            if backtest_dirs:
                latest = backtest_dirs[0]
                results_file = latest / "results.json"

                if results_file.exists():
                    with open(results_file, 'r') as f:
                        raw_results = json.load(f)

                    result = extract_metrics(raw_results, result)
                    result.success = True
                    result.raw_results = raw_results

    except subprocess.TimeoutExpired:
        result.error = "Backtest timed out after 10 minutes"
        logger.error(result.error)
    except Exception as e:
        result.error = f"Error running backtest: {e}"
        logger.error(result.error)

    return result


def run_cloud_backtest(
    project_dir: Path,
    qc_client: QCClient,
    wait_for_completion: bool = True
) -> BacktestResult:
    """
    Run backtest on QuantConnect cloud.

    Args:
        project_dir: Directory containing main.py
        qc_client: QC API client
        wait_for_completion: Wait for backtest to complete

    Returns:
        BacktestResult
    """
    config_file = project_dir / "config.json"
    with open(config_file, 'r') as f:
        config = json.load(f)

    result = BacktestResult(
        component_id=config["component_id"],
        test_type=config["test_type"],
        success=False
    )

    try:
        # Push project to cloud
        project_name = f"{config['component_id']}_{config['test_type']}"
        project_id = qc_client.create_or_get_project(project_name)

        if not project_id:
            result.error = "Failed to create/get QC project"
            return result

        result.project_id = project_id

        # Push files
        main_py = project_dir / "main.py"
        if not qc_client.push_file(project_id, main_py):
            result.error = "Failed to push algorithm file"
            return result

        # Run backtest
        backtest_id = qc_client.run_backtest(project_id, project_name)
        if not backtest_id:
            result.error = "Failed to start backtest"
            return result

        result.backtest_id = backtest_id

        if wait_for_completion:
            # Poll for completion
            max_wait = 600  # 10 minutes
            poll_interval = 10
            elapsed = 0

            while elapsed < max_wait:
                status = qc_client.get_backtest_status(project_id, backtest_id)

                if status == "completed":
                    break
                elif status == "error":
                    result.error = "Backtest failed on QC cloud"
                    return result

                time.sleep(poll_interval)
                elapsed += poll_interval

            if elapsed >= max_wait:
                result.error = "Backtest timed out"
                return result

            # Get results
            raw_results = qc_client.get_backtest_results(project_id, backtest_id)
            if raw_results:
                result = extract_metrics(raw_results, result)
                result.success = True
                result.raw_results = raw_results

    except Exception as e:
        result.error = f"Error running cloud backtest: {e}"
        logger.error(result.error)

    return result


def extract_metrics(raw_results: Dict[str, Any], result: BacktestResult) -> BacktestResult:
    """
    Extract key metrics from raw backtest results.

    Args:
        raw_results: Raw results from QC
        result: BacktestResult to populate

    Returns:
        Updated BacktestResult
    """
    stats = raw_results.get("Statistics", {})

    # Extract metrics
    result.sharpe_ratio = _parse_float(stats.get("Sharpe Ratio"))
    result.alpha = _parse_float(stats.get("Alpha"))
    result.beta = _parse_float(stats.get("Beta"))
    result.cagr = _parse_percentage(stats.get("Compounding Annual Return"))
    result.max_drawdown = _parse_percentage(stats.get("Drawdown"))
    result.total_trades = _parse_int(stats.get("Total Trades"))
    result.win_rate = _parse_percentage(stats.get("Win Rate"))

    # Calculate total days
    runtime = raw_results.get("RuntimeStatistics", {})
    if runtime.get("Runtime"):
        # Parse runtime to estimate trading days
        pass

    return result


def _parse_float(value: str) -> Optional[float]:
    """Parse float from string, handling % signs."""
    if value is None:
        return None
    try:
        return float(str(value).replace("%", "").replace(",", ""))
    except (ValueError, TypeError):
        return None


def _parse_percentage(value: str) -> Optional[float]:
    """Parse percentage to decimal."""
    parsed = _parse_float(value)
    if parsed is not None and "%" in str(value):
        return parsed / 100
    return parsed


def _parse_int(value: str) -> Optional[int]:
    """Parse integer from string."""
    if value is None:
        return None
    try:
        return int(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return None


def run_backtest(
    component_id: str,
    hypothesis: Dict[str, Any],
    test_type: str = "is",
    use_cloud: bool = True
) -> BacktestResult:
    """
    Run a complete backtest for a component.

    Args:
        component_id: Catalog entry ID
        hypothesis: Hypothesis document with data requirements
        test_type: "is" for in-sample, "oos" for out-of-sample
        use_cloud: Use QC cloud (True) or local LEAN (False)

    Returns:
        BacktestResult
    """
    logger.info(f"Running {test_type} backtest for {component_id}")

    # Determine test period
    if test_type == "is":
        period = hypothesis.get("is_period", {})
    else:
        period = hypothesis.get("oos_period", {})

    start_date = period.get("start", "2005-01-01")
    end_date = period.get("end", "2024-12-31")

    # Prepare data sources
    data_ids = hypothesis.get("data_requirements", [])
    data_sources = prepare_data_sources(data_ids)

    if not data_sources:
        return BacktestResult(
            component_id=component_id,
            test_type=test_type,
            success=False,
            error="No data sources available"
        )

    # Determine template
    test_config = hypothesis.get("test_config", {})
    template = test_config.get("template", "base_algorithm")

    # Build config
    config = BacktestConfig(
        component_id=component_id,
        name=hypothesis.get("name", component_id),
        test_type=test_type,
        start_date=start_date,
        end_date=end_date,
        template=template,
        data_sources=data_sources,
        parameters=hypothesis.get("parameters", {}),
    )

    # Add filter config if applicable
    if template == "filter_test":
        filter_config = test_config.get("filter", {})
        config.filter_indicator = filter_config.get("indicator")
        config.filter_column = filter_config.get("column")
        config.filter_threshold = filter_config.get("threshold", 0)
        config.filter_direction = filter_config.get("direction", "above")
        config.filter_role = filter_config.get("role", "both")
        config.base_strategy = filter_config.get("base_strategy", "SMA_CROSSOVER")

    # Generate algorithm
    output_dir = VALIDATIONS_DIR / component_id / f"{test_type}_test"
    generate_algorithm(config, output_dir)

    # Run backtest
    if use_cloud:
        from utils.qc_client import QCClient
        qc_client = QCClient()
        result = run_cloud_backtest(output_dir, qc_client)
    else:
        result = run_local_backtest(output_dir)

    # Save results
    results_file = output_dir / "results.json"
    with open(results_file, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)

    logger.info(f"Backtest complete: success={result.success}, sharpe={result.sharpe_ratio}")

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run backtest")
    parser.add_argument("component_id", help="Component ID")
    parser.add_argument("--hypothesis", type=Path, help="Path to hypothesis.json")
    parser.add_argument("--test-type", choices=["is", "oos"], default="is")
    parser.add_argument("--local", action="store_true", help="Run locally instead of cloud")

    args = parser.parse_args()

    # Load hypothesis
    if args.hypothesis and args.hypothesis.exists():
        with open(args.hypothesis, 'r') as f:
            hypothesis = json.load(f)
    else:
        # Example hypothesis
        hypothesis = {
            "name": "Test Component",
            "data_requirements": ["spy_prices", "mcclellan_oscillator"],
            "is_period": {"start": "2005-01-01", "end": "2019-12-31"},
            "oos_period": {"start": "2020-01-01", "end": "2024-12-31"},
            "parameters": {}
        }

    result = run_backtest(
        args.component_id,
        hypothesis,
        args.test_type,
        use_cloud=not args.local
    )

    print(f"\nBacktest Result: {'SUCCESS' if result.success else 'FAILED'}")
    if result.success:
        print(f"  Sharpe: {result.sharpe_ratio}")
        print(f"  Alpha: {result.alpha}")
        print(f"  CAGR: {result.cagr}")
        print(f"  Max DD: {result.max_drawdown}")
        print(f"  Trades: {result.total_trades}")
    else:
        print(f"  Error: {result.error}")
