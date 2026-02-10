"""
Backtest execution module.

Provides functionality for generating and running QuantConnect backtests.

Components:
    - run_backtest: Main entry point for running backtests
    - generate_algorithm: Generate QC algorithms from templates
    - BacktestConfig: Configuration for backtest runs
    - BacktestResult: Results from backtest execution

Usage:
    from research_system.scripts.backtest import run_backtest, BacktestResult
    result = run_backtest("IND-002", hypothesis, test_type="is")
"""

from .run_backtest import (
    run_backtest,
    generate_algorithm,
    run_local_backtest,
    run_cloud_backtest,
    prepare_data_sources,
    extract_metrics,
    BacktestConfig,
    BacktestResult,
)

__all__ = [
    "run_backtest",
    "generate_algorithm",
    "run_local_backtest",
    "run_cloud_backtest",
    "prepare_data_sources",
    "extract_metrics",
    "BacktestConfig",
    "BacktestResult",
]
