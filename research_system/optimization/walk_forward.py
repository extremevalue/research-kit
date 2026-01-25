"""Walk-forward validation runner.

This module implements true walk-forward optimization:
1. Optimize parameters on in-sample period
2. Test optimized params on out-of-sample period
3. Advance window forward
4. Repeat until end of data
5. Aggregate out-of-sample results

The key insight: parameters are re-optimized at each step using
only data available at that point in time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import logging

from research_system.optimization.optimizer import (
    OptimizationMethod,
    OptimizationResult,
    ParameterOptimizer,
)

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward validation.

    Example with 3-year optimization and 1-year test:
    - Period 1: Optimize 2012-2014, test 2015
    - Period 2: Optimize 2012-2015, test 2016
    - Period 3: Optimize 2012-2016, test 2017
    - ...

    The optimization window expands to include all historical data,
    while the test window always moves forward.
    """

    start_year: int = 2012
    end_year: int = 2023
    initial_train_years: int = 3  # Years for first optimization
    test_years: int = 1  # Years for each out-of-sample test
    expanding_window: bool = True  # If True, include all past data in optimization
    max_evaluations: int = 50  # Max parameter combinations per optimization
    optimization_method: OptimizationMethod = OptimizationMethod.RANDOM
    objective: str = "sharpe"  # Metric to optimize

    def get_periods(self) -> list[tuple[str, str, str, str]]:
        """Generate (opt_start, opt_end, test_start, test_end) periods.

        Returns:
            List of tuples with optimization and test date ranges.
        """
        periods = []
        first_test_year = self.start_year + self.initial_train_years

        for test_year in range(first_test_year, self.end_year + 1):
            if self.expanding_window:
                opt_start = f"{self.start_year}-01-01"
            else:
                opt_start = f"{test_year - self.initial_train_years}-01-01"

            opt_end = f"{test_year - 1}-12-31"

            test_start = f"{test_year}-01-01"
            test_end_year = min(test_year + self.test_years - 1, self.end_year)
            test_end = f"{test_end_year}-12-31"

            # Don't create period if test would go past end year
            if test_year > self.end_year:
                break

            periods.append((opt_start, opt_end, test_start, test_end))

        return periods


@dataclass
class WalkForwardPeriod:
    """Result from a single walk-forward period."""

    period_id: int
    opt_start: str
    opt_end: str
    test_start: str
    test_end: str

    # Optimization results
    optimized_params: dict[str, Any] | None = None
    optimization_sharpe: float | None = None  # Best in-sample Sharpe

    # Out-of-sample results
    oos_sharpe: float | None = None
    oos_cagr: float | None = None
    oos_max_drawdown: float | None = None

    success: bool = False
    error: str | None = None


@dataclass
class WalkForwardResult:
    """Aggregated results from walk-forward validation."""

    strategy_id: str
    config: WalkForwardConfig
    periods: list[WalkForwardPeriod] = field(default_factory=list)

    # Aggregated out-of-sample metrics
    avg_oos_sharpe: float | None = None
    avg_oos_cagr: float | None = None
    worst_oos_sharpe: float | None = None
    worst_oos_drawdown: float | None = None

    # Consistency metrics
    consistency: float | None = None  # % of profitable OOS periods
    is_vs_oos_degradation: float | None = None  # Avg IS Sharpe vs Avg OOS Sharpe

    # Parameter stability
    parameter_stability: float | None = None  # 0-1, how stable params are across periods

    success: bool = False
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "strategy_id": self.strategy_id,
            "config": {
                "start_year": self.config.start_year,
                "end_year": self.config.end_year,
                "initial_train_years": self.config.initial_train_years,
                "test_years": self.config.test_years,
                "expanding_window": self.config.expanding_window,
                "max_evaluations": self.config.max_evaluations,
            },
            "periods": [
                {
                    "period_id": p.period_id,
                    "opt_start": p.opt_start,
                    "opt_end": p.opt_end,
                    "test_start": p.test_start,
                    "test_end": p.test_end,
                    "optimized_params": p.optimized_params,
                    "optimization_sharpe": p.optimization_sharpe,
                    "oos_sharpe": p.oos_sharpe,
                    "oos_cagr": p.oos_cagr,
                    "oos_max_drawdown": p.oos_max_drawdown,
                    "success": p.success,
                    "error": p.error,
                }
                for p in self.periods
            ],
            "avg_oos_sharpe": self.avg_oos_sharpe,
            "avg_oos_cagr": self.avg_oos_cagr,
            "worst_oos_sharpe": self.worst_oos_sharpe,
            "worst_oos_drawdown": self.worst_oos_drawdown,
            "consistency": self.consistency,
            "is_vs_oos_degradation": self.is_vs_oos_degradation,
            "parameter_stability": self.parameter_stability,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class WalkForwardRunner:
    """Run true walk-forward optimization.

    Walk-forward validation:
    1. For each period:
       a. Optimize parameters on in-sample data (historical)
       b. Test optimized params on out-of-sample data (future)
       c. Record OOS results
    2. Aggregate all OOS results
    3. Calculate parameter stability

    This simulates what would happen in live trading where you
    periodically re-optimize parameters using only available data.

    Example:
        runner = WalkForwardRunner(backtest_executor, code_generator)
        result = runner.run(
            strategy=strategy_doc,
            config=WalkForwardConfig(
                start_year=2012,
                end_year=2023,
                initial_train_years=3,
                test_years=1,
            ),
        )
        print(f"Avg OOS Sharpe: {result.avg_oos_sharpe}")
        print(f"Consistency: {result.consistency}")
    """

    def __init__(
        self,
        backtest_executor=None,
        code_generator=None,
    ):
        """Initialize walk-forward runner.

        Args:
            backtest_executor: BacktestExecutor for running backtests
            code_generator: V4CodeGenerator for generating code
        """
        self.backtest_executor = backtest_executor
        self.code_generator = code_generator
        self.optimizer = ParameterOptimizer(backtest_executor, code_generator)

    def run(
        self,
        strategy: dict[str, Any],
        config: WalkForwardConfig | None = None,
    ) -> WalkForwardResult:
        """Run walk-forward validation.

        Args:
            strategy: Strategy document with tunable_parameters
            config: Walk-forward configuration (uses defaults if None)

        Returns:
            WalkForwardResult with aggregated OOS performance
        """
        if config is None:
            config = WalkForwardConfig()

        strategy_id = strategy.get("id", "unknown")
        result = WalkForwardResult(strategy_id=strategy_id, config=config)

        # Check for tunable parameters
        if not strategy.get("tunable_parameters"):
            result.error = "Strategy has no tunable parameters"
            return result

        # Get periods
        periods = config.get_periods()
        if not periods:
            result.error = "No valid walk-forward periods"
            return result

        logger.info(f"Running walk-forward with {len(periods)} periods")

        # Run each period
        for i, (opt_start, opt_end, test_start, test_end) in enumerate(periods):
            period_id = i + 1
            logger.info(
                f"Period {period_id}: Optimize {opt_start} to {opt_end}, "
                f"Test {test_start} to {test_end}"
            )

            period_result = self._run_period(
                strategy=strategy,
                period_id=period_id,
                opt_start=opt_start,
                opt_end=opt_end,
                test_start=test_start,
                test_end=test_end,
                config=config,
            )
            result.periods.append(period_result)

        # Aggregate results
        self._aggregate_results(result)

        # Calculate parameter stability
        self._calculate_parameter_stability(result)

        return result

    def _run_period(
        self,
        strategy: dict[str, Any],
        period_id: int,
        opt_start: str,
        opt_end: str,
        test_start: str,
        test_end: str,
        config: WalkForwardConfig,
    ) -> WalkForwardPeriod:
        """Run a single walk-forward period.

        Args:
            strategy: Strategy document
            period_id: Period number
            opt_start: Optimization start date
            opt_end: Optimization end date
            test_start: Test start date
            test_end: Test end date
            config: Walk-forward config

        Returns:
            WalkForwardPeriod with results
        """
        period = WalkForwardPeriod(
            period_id=period_id,
            opt_start=opt_start,
            opt_end=opt_end,
            test_start=test_start,
            test_end=test_end,
        )

        # Step 1: Optimize parameters on in-sample period
        opt_result = self.optimizer.optimize(
            strategy=strategy,
            start_date=opt_start,
            end_date=opt_end,
            max_evaluations=config.max_evaluations,
            method=config.optimization_method,
            objective=config.objective,
        )

        if not opt_result.success:
            period.error = f"Optimization failed: {opt_result.error}"
            return period

        period.optimized_params = opt_result.best_params
        period.optimization_sharpe = opt_result.best_sharpe

        # Step 2: Test optimized params on out-of-sample period
        oos_result = self._test_parameters(
            strategy=strategy,
            params=opt_result.best_params,
            start_date=test_start,
            end_date=test_end,
        )

        if not oos_result.success:
            period.error = f"OOS test failed: {oos_result.error}"
            return period

        period.oos_sharpe = oos_result.sharpe
        period.oos_cagr = oos_result.cagr
        period.oos_max_drawdown = oos_result.max_drawdown
        period.success = True

        return period

    def _test_parameters(
        self,
        strategy: dict[str, Any],
        params: dict[str, Any],
        start_date: str,
        end_date: str,
    ):
        """Test specific parameters on a period.

        Args:
            strategy: Strategy document
            params: Parameter values to test
            start_date: Test start date
            end_date: Test end date

        Returns:
            Backtest result (or mock for testing)
        """
        if not self.backtest_executor or not self.code_generator:
            # Return mock result for testing
            @dataclass
            class MockResult:
                success: bool = False
                sharpe: float | None = None
                cagr: float | None = None
                max_drawdown: float | None = None
                error: str = "No executor configured"

            return MockResult()

        # Inject parameters into strategy
        import copy

        strategy_copy = copy.deepcopy(strategy)
        if "parameters" not in strategy_copy:
            strategy_copy["parameters"] = {}
        strategy_copy["parameters"].update(params)
        strategy_copy["parameters"]["_optimized"] = params

        # Generate code
        code_result = self.code_generator.generate(strategy_copy)
        if not code_result.success:
            @dataclass
            class FailedResult:
                success: bool = False
                sharpe: float | None = None
                cagr: float | None = None
                max_drawdown: float | None = None
                error: str = ""

            return FailedResult(error=f"Code generation failed: {code_result.error}")

        # Run backtest
        return self.backtest_executor.run_single(
            code=code_result.code,
            start_date=start_date,
            end_date=end_date,
            strategy_id=f"{strategy.get('id', 'wf')}_oos",
        )

    def _aggregate_results(self, result: WalkForwardResult) -> None:
        """Aggregate period results into summary metrics.

        Args:
            result: WalkForwardResult to update in place
        """
        successful_periods = [p for p in result.periods if p.success]

        if not successful_periods:
            result.error = "No successful periods"
            return

        # Calculate averages
        oos_sharpes = [p.oos_sharpe for p in successful_periods if p.oos_sharpe is not None]
        oos_cagrs = [p.oos_cagr for p in successful_periods if p.oos_cagr is not None]
        oos_drawdowns = [
            p.oos_max_drawdown for p in successful_periods if p.oos_max_drawdown is not None
        ]
        is_sharpes = [
            p.optimization_sharpe for p in successful_periods if p.optimization_sharpe is not None
        ]

        if oos_sharpes:
            result.avg_oos_sharpe = sum(oos_sharpes) / len(oos_sharpes)
            result.worst_oos_sharpe = min(oos_sharpes)

        if oos_cagrs:
            result.avg_oos_cagr = sum(oos_cagrs) / len(oos_cagrs)

        if oos_drawdowns:
            result.worst_oos_drawdown = max(oos_drawdowns)

        # Calculate consistency (% of profitable periods)
        if oos_cagrs:
            profitable = sum(1 for c in oos_cagrs if c > 0)
            result.consistency = profitable / len(oos_cagrs)

        # Calculate IS vs OOS degradation
        if is_sharpes and oos_sharpes and len(is_sharpes) == len(oos_sharpes):
            avg_is = sum(is_sharpes) / len(is_sharpes)
            avg_oos = sum(oos_sharpes) / len(oos_sharpes)
            if avg_is > 0:
                result.is_vs_oos_degradation = (avg_is - avg_oos) / avg_is

        result.success = True

    def _calculate_parameter_stability(self, result: WalkForwardResult) -> None:
        """Calculate how stable parameters are across periods.

        Low stability (params change a lot) suggests overfitting.
        High stability (params consistent) suggests robust strategy.

        Args:
            result: WalkForwardResult to update in place
        """
        params_by_period = [
            p.optimized_params for p in result.periods
            if p.success and p.optimized_params
        ]

        if len(params_by_period) < 2:
            return

        # Get all parameter names
        all_params = set()
        for params in params_by_period:
            all_params.update(params.keys())

        # Calculate stability for each parameter
        stabilities = []

        for param_name in all_params:
            values = [
                params.get(param_name) for params in params_by_period
                if param_name in params
            ]

            if not values or not all(isinstance(v, (int, float)) for v in values):
                continue

            # Stability = 1 - (std / range), normalized to 0-1
            if len(values) < 2:
                continue

            min_val = min(values)
            max_val = max(values)
            val_range = max_val - min_val

            if val_range == 0:
                # All same value = perfect stability
                stabilities.append(1.0)
            else:
                mean_val = sum(values) / len(values)
                variance = sum((v - mean_val) ** 2 for v in values) / len(values)
                std = variance ** 0.5
                stability = max(0, 1 - (std / val_range))
                stabilities.append(stability)

        if stabilities:
            result.parameter_stability = sum(stabilities) / len(stabilities)
