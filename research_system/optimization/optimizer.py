"""Parameter optimizer for walk-forward validation.

This module provides parameter optimization capabilities:
- Grid search: Exhaustive search over all parameter combinations
- Random search: Sample N random combinations from parameter space

The optimizer integrates with BacktestExecutor to evaluate each
parameter combination via backtesting.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import logging

from research_system.schemas.v4 import (
    ParameterType,
    TunableParameter,
    TunableParameters,
)

logger = logging.getLogger(__name__)


class OptimizationMethod(str, Enum):
    """Optimization search method."""

    GRID = "grid"
    RANDOM = "random"


@dataclass
class ParameterEvaluation:
    """Result of evaluating a single parameter combination."""

    params: dict[str, Any]
    sharpe: float | None = None
    cagr: float | None = None
    max_drawdown: float | None = None
    success: bool = False
    error: str | None = None


@dataclass
class OptimizationResult:
    """Result of parameter optimization."""

    success: bool
    best_params: dict[str, Any] | None = None
    best_sharpe: float | None = None
    best_cagr: float | None = None
    evaluations: list[ParameterEvaluation] = field(default_factory=list)
    total_evaluated: int = 0
    total_successful: int = 0
    method: OptimizationMethod = OptimizationMethod.RANDOM
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "best_params": self.best_params,
            "best_sharpe": self.best_sharpe,
            "best_cagr": self.best_cagr,
            "total_evaluated": self.total_evaluated,
            "total_successful": self.total_successful,
            "method": self.method.value,
            "error": self.error,
            "evaluations": [
                {
                    "params": e.params,
                    "sharpe": e.sharpe,
                    "cagr": e.cagr,
                    "max_drawdown": e.max_drawdown,
                    "success": e.success,
                    "error": e.error,
                }
                for e in self.evaluations
            ],
        }


class ParameterOptimizer:
    """Optimize strategy parameters via backtesting.

    Supports grid search and random search methods.
    Grid search is exhaustive but expensive for large parameter spaces.
    Random search samples N combinations and is often as effective.

    Example:
        optimizer = ParameterOptimizer(backtest_executor, code_generator)
        result = optimizer.optimize(
            strategy=strategy_doc,
            start_date="2012-01-01",
            end_date="2017-12-31",
            max_evaluations=50,
            method=OptimizationMethod.RANDOM,
        )
        print(f"Best params: {result.best_params}")
        print(f"Best Sharpe: {result.best_sharpe}")
    """

    def __init__(
        self,
        backtest_executor=None,
        code_generator=None,
    ):
        """Initialize the optimizer.

        Args:
            backtest_executor: BacktestExecutor for running backtests
            code_generator: V4CodeGenerator for generating code
        """
        self.backtest_executor = backtest_executor
        self.code_generator = code_generator

    def optimize(
        self,
        strategy: dict[str, Any],
        start_date: str,
        end_date: str,
        max_evaluations: int = 50,
        method: OptimizationMethod = OptimizationMethod.RANDOM,
        objective: str = "sharpe",
    ) -> OptimizationResult:
        """Optimize parameters for a strategy.

        Args:
            strategy: Strategy document with tunable_parameters
            start_date: Backtest start date
            end_date: Backtest end date
            max_evaluations: Maximum number of parameter combinations to evaluate
            method: Search method (grid or random)
            objective: Metric to optimize ("sharpe" or "cagr")

        Returns:
            OptimizationResult with best parameters found
        """
        # Extract tunable parameters
        tunable = self._get_tunable_parameters(strategy)
        if not tunable or not tunable.parameters:
            return OptimizationResult(
                success=False,
                error="Strategy has no tunable parameters",
                method=method,
            )

        # Generate parameter combinations
        if method == OptimizationMethod.GRID:
            combinations = self._generate_grid_combinations(tunable, max_evaluations)
        else:
            combinations = self._generate_random_combinations(tunable, max_evaluations)

        if not combinations:
            return OptimizationResult(
                success=False,
                error="No parameter combinations generated",
                method=method,
            )

        logger.info(f"Evaluating {len(combinations)} parameter combinations")

        # Evaluate each combination
        evaluations = []
        best_result: ParameterEvaluation | None = None

        for i, params in enumerate(combinations):
            logger.debug(f"Evaluating combination {i + 1}/{len(combinations)}: {params}")

            eval_result = self._evaluate_parameters(
                strategy, params, start_date, end_date
            )
            evaluations.append(eval_result)

            if eval_result.success:
                # Check if this is the best so far
                if best_result is None:
                    best_result = eval_result
                elif objective == "sharpe":
                    if (eval_result.sharpe or 0) > (best_result.sharpe or 0):
                        best_result = eval_result
                elif objective == "cagr":
                    if (eval_result.cagr or 0) > (best_result.cagr or 0):
                        best_result = eval_result

        # Compile results
        total_successful = sum(1 for e in evaluations if e.success)

        if best_result is None:
            return OptimizationResult(
                success=False,
                evaluations=evaluations,
                total_evaluated=len(evaluations),
                total_successful=total_successful,
                method=method,
                error="All parameter combinations failed",
            )

        return OptimizationResult(
            success=True,
            best_params=best_result.params,
            best_sharpe=best_result.sharpe,
            best_cagr=best_result.cagr,
            evaluations=evaluations,
            total_evaluated=len(evaluations),
            total_successful=total_successful,
            method=method,
        )

    def _get_tunable_parameters(
        self, strategy: dict[str, Any]
    ) -> TunableParameters | None:
        """Extract tunable parameters from strategy."""
        tunable_data = strategy.get("tunable_parameters")
        if not tunable_data:
            return None

        try:
            return TunableParameters(**tunable_data)
        except Exception as e:
            logger.error(f"Failed to parse tunable parameters: {e}")
            return None

    def _generate_grid_combinations(
        self,
        tunable: TunableParameters,
        max_evaluations: int,
    ) -> list[dict[str, Any]]:
        """Generate all grid combinations up to max_evaluations.

        Args:
            tunable: Tunable parameters configuration
            max_evaluations: Maximum combinations to return

        Returns:
            List of parameter dictionaries
        """
        # Generate all possible values for each parameter
        param_values: dict[str, list[Any]] = {}

        for name, param in tunable.parameters.items():
            param_values[name] = self._get_parameter_values(param)

        # Generate cartesian product
        if not param_values:
            return []

        keys = list(param_values.keys())
        value_lists = [param_values[k] for k in keys]

        combinations = []
        for values in itertools.product(*value_lists):
            if len(combinations) >= max_evaluations:
                break
            combinations.append(dict(zip(keys, values)))

        return combinations

    def _generate_random_combinations(
        self,
        tunable: TunableParameters,
        max_evaluations: int,
    ) -> list[dict[str, Any]]:
        """Generate random parameter combinations.

        Args:
            tunable: Tunable parameters configuration
            max_evaluations: Number of combinations to generate

        Returns:
            List of parameter dictionaries
        """
        # Get all possible values for each parameter
        param_values: dict[str, list[Any]] = {}

        for name, param in tunable.parameters.items():
            param_values[name] = self._get_parameter_values(param)

        if not param_values:
            return []

        # Calculate total search space
        total_space = tunable.get_total_search_space_size()

        # If search space is small, just return all combinations
        if total_space <= max_evaluations:
            return self._generate_grid_combinations(tunable, total_space)

        # Generate random combinations (avoiding duplicates)
        keys = list(param_values.keys())
        combinations = set()

        attempts = 0
        max_attempts = max_evaluations * 10  # Prevent infinite loop

        while len(combinations) < max_evaluations and attempts < max_attempts:
            combo = tuple(random.choice(param_values[k]) for k in keys)
            combinations.add(combo)
            attempts += 1

        return [dict(zip(keys, combo)) for combo in combinations]

    def _get_parameter_values(self, param: TunableParameter) -> list[Any]:
        """Get all possible values for a parameter.

        Args:
            param: Tunable parameter definition

        Returns:
            List of possible values
        """
        if param.type == ParameterType.BOOL:
            return [True, False]

        elif param.type == ParameterType.CHOICE:
            return list(param.choices) if param.choices else [param.default]

        elif param.type in (ParameterType.INT, ParameterType.FLOAT):
            if param.min is None or param.max is None or param.step is None:
                return [param.default]

            values = []
            current = param.min
            while current <= param.max:
                if param.type == ParameterType.INT:
                    values.append(int(current))
                else:
                    values.append(round(current, 10))  # Avoid float precision issues
                current += param.step

            return values if values else [param.default]

        return [param.default]

    def _evaluate_parameters(
        self,
        strategy: dict[str, Any],
        params: dict[str, Any],
        start_date: str,
        end_date: str,
    ) -> ParameterEvaluation:
        """Evaluate a single parameter combination.

        Args:
            strategy: Strategy document
            params: Parameter values to use
            start_date: Backtest start date
            end_date: Backtest end date

        Returns:
            ParameterEvaluation with results
        """
        if not self.backtest_executor or not self.code_generator:
            return ParameterEvaluation(
                params=params,
                success=False,
                error="No backtest executor or code generator configured",
            )

        try:
            # Create strategy copy with injected parameters
            strategy_with_params = self._inject_parameters(strategy, params)

            # Generate code
            code_result = self.code_generator.generate(strategy_with_params)
            if not code_result.success:
                return ParameterEvaluation(
                    params=params,
                    success=False,
                    error=f"Code generation failed: {code_result.error}",
                )

            # Run backtest
            result = self.backtest_executor.run_single(
                code=code_result.code,
                start_date=start_date,
                end_date=end_date,
                strategy_id=f"{strategy.get('id', 'opt')}_eval",
            )

            if not result.success:
                return ParameterEvaluation(
                    params=params,
                    success=False,
                    error=result.error,
                )

            return ParameterEvaluation(
                params=params,
                sharpe=result.sharpe,
                cagr=result.cagr,
                max_drawdown=result.max_drawdown,
                success=True,
            )

        except Exception as e:
            logger.error(f"Error evaluating parameters {params}: {e}")
            return ParameterEvaluation(
                params=params,
                success=False,
                error=str(e),
            )

    def _inject_parameters(
        self,
        strategy: dict[str, Any],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Inject parameter values into strategy document.

        Creates a copy of the strategy with parameter values set
        in the appropriate locations for code generation.

        Args:
            strategy: Original strategy document
            params: Parameter values to inject

        Returns:
            Strategy document with injected parameters
        """
        import copy

        strategy_copy = copy.deepcopy(strategy)

        # Store the resolved parameter values for template access
        if "parameters" not in strategy_copy:
            strategy_copy["parameters"] = {}

        strategy_copy["parameters"]["_optimized"] = params

        # Also set them as top-level for easier template access
        for name, value in params.items():
            strategy_copy["parameters"][name] = value

        return strategy_copy
