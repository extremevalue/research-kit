"""Tests for parameter optimizer.

This module tests:
1. Parameter value generation
2. Grid search combinations
3. Random search combinations
4. Optimization result handling
"""

import pytest
from unittest.mock import MagicMock, patch

from research_system.optimization import (
    OptimizationMethod,
    OptimizationResult,
    ParameterOptimizer,
)
from research_system.optimization.optimizer import ParameterEvaluation
from research_system.schemas.v4 import (
    ParameterType,
    TunableParameter,
    TunableParameters,
)


# =============================================================================
# TEST PARAMETER VALUE GENERATION
# =============================================================================


class TestParameterValueGeneration:
    """Test generation of parameter values."""

    @pytest.fixture
    def optimizer(self):
        """Create optimizer without dependencies."""
        return ParameterOptimizer()

    def test_int_parameter_values(self, optimizer):
        """Test integer parameter value generation."""
        param = TunableParameter(
            type=ParameterType.INT,
            default=10,
            min=5,
            max=20,
            step=5,
        )
        values = optimizer._get_parameter_values(param)
        assert values == [5, 10, 15, 20]

    def test_float_parameter_values(self, optimizer):
        """Test float parameter value generation."""
        param = TunableParameter(
            type=ParameterType.FLOAT,
            default=0.5,
            min=0.0,
            max=1.0,
            step=0.5,
        )
        values = optimizer._get_parameter_values(param)
        assert len(values) == 3
        assert 0.0 in values
        assert 0.5 in values
        assert 1.0 in values

    def test_bool_parameter_values(self, optimizer):
        """Test boolean parameter value generation."""
        param = TunableParameter(
            type=ParameterType.BOOL,
            default=True,
        )
        values = optimizer._get_parameter_values(param)
        assert values == [True, False]

    def test_choice_parameter_values(self, optimizer):
        """Test choice parameter value generation."""
        param = TunableParameter(
            type=ParameterType.CHOICE,
            default="sma",
            choices=["sma", "ema", "wma"],
        )
        values = optimizer._get_parameter_values(param)
        assert values == ["sma", "ema", "wma"]

    def test_fixed_parameter_values(self, optimizer):
        """Test fixed parameter (no range) value generation."""
        param = TunableParameter(
            type=ParameterType.INT,
            default=42,
        )
        values = optimizer._get_parameter_values(param)
        assert values == [42]


# =============================================================================
# TEST GRID SEARCH
# =============================================================================


class TestGridSearch:
    """Test grid search combination generation."""

    @pytest.fixture
    def optimizer(self):
        return ParameterOptimizer()

    def test_grid_single_parameter(self, optimizer):
        """Test grid search with single parameter."""
        tunable = TunableParameters(
            parameters={
                "period": TunableParameter(
                    type=ParameterType.INT,
                    default=10,
                    min=5,
                    max=15,
                    step=5,
                ),
            }
        )
        combinations = optimizer._generate_grid_combinations(tunable, 100)
        assert len(combinations) == 3
        assert {"period": 5} in combinations
        assert {"period": 10} in combinations
        assert {"period": 15} in combinations

    def test_grid_multiple_parameters(self, optimizer):
        """Test grid search with multiple parameters."""
        tunable = TunableParameters(
            parameters={
                "fast": TunableParameter(
                    type=ParameterType.INT,
                    default=10,
                    min=5,
                    max=10,
                    step=5,  # 2 values
                ),
                "slow": TunableParameter(
                    type=ParameterType.INT,
                    default=50,
                    min=40,
                    max=60,
                    step=10,  # 3 values
                ),
            }
        )
        combinations = optimizer._generate_grid_combinations(tunable, 100)
        # 2 * 3 = 6 combinations
        assert len(combinations) == 6

    def test_grid_respects_max_evaluations(self, optimizer):
        """Test that grid search respects max_evaluations limit."""
        tunable = TunableParameters(
            parameters={
                "param1": TunableParameter(
                    type=ParameterType.INT,
                    default=50,
                    min=1,
                    max=100,
                    step=1,  # 100 values
                ),
            }
        )
        combinations = optimizer._generate_grid_combinations(tunable, 10)
        assert len(combinations) == 10


# =============================================================================
# TEST RANDOM SEARCH
# =============================================================================


class TestRandomSearch:
    """Test random search combination generation."""

    @pytest.fixture
    def optimizer(self):
        return ParameterOptimizer()

    def test_random_generates_correct_count(self, optimizer):
        """Test random search generates requested number of combinations."""
        tunable = TunableParameters(
            parameters={
                "param": TunableParameter(
                    type=ParameterType.INT,
                    default=50,
                    min=1,
                    max=1000,
                    step=1,
                ),
            }
        )
        combinations = optimizer._generate_random_combinations(tunable, 50)
        assert len(combinations) == 50

    def test_random_falls_back_to_grid_for_small_space(self, optimizer):
        """Test random search uses grid when space is small."""
        tunable = TunableParameters(
            parameters={
                "param": TunableParameter(
                    type=ParameterType.INT,
                    default=10,
                    min=5,
                    max=15,
                    step=5,  # Only 3 values
                ),
            }
        )
        combinations = optimizer._generate_random_combinations(tunable, 50)
        # Should return all 3, not 50
        assert len(combinations) == 3

    def test_random_generates_unique_combinations(self, optimizer):
        """Test random search generates unique combinations."""
        tunable = TunableParameters(
            parameters={
                "param": TunableParameter(
                    type=ParameterType.INT,
                    default=50,
                    min=1,
                    max=100,
                    step=1,
                ),
            }
        )
        combinations = optimizer._generate_random_combinations(tunable, 20)

        # Check uniqueness
        param_values = [c["param"] for c in combinations]
        assert len(param_values) == len(set(param_values))


# =============================================================================
# TEST OPTIMIZATION RESULT
# =============================================================================


class TestOptimizationResult:
    """Test OptimizationResult dataclass."""

    def test_result_to_dict(self):
        """Test result serialization."""
        result = OptimizationResult(
            success=True,
            best_params={"period": 20},
            best_sharpe=1.5,
            best_cagr=0.12,
            total_evaluated=10,
            total_successful=8,
            method=OptimizationMethod.RANDOM,
        )
        data = result.to_dict()
        assert data["success"] is True
        assert data["best_params"] == {"period": 20}
        assert data["best_sharpe"] == 1.5
        assert data["method"] == "random"

    def test_failed_result(self):
        """Test failed optimization result."""
        result = OptimizationResult(
            success=False,
            error="No tunable parameters",
            method=OptimizationMethod.GRID,
        )
        assert result.success is False
        assert result.best_params is None
        assert "tunable" in result.error.lower()


# =============================================================================
# TEST OPTIMIZATION FLOW
# =============================================================================


class TestOptimizationFlow:
    """Test full optimization flow."""

    def test_optimize_no_parameters_returns_error(self):
        """Test optimization fails gracefully with no parameters."""
        optimizer = ParameterOptimizer()
        strategy = {"id": "TEST-001", "name": "Test"}

        result = optimizer.optimize(
            strategy=strategy,
            start_date="2020-01-01",
            end_date="2020-12-31",
        )

        assert result.success is False
        assert "no tunable parameters" in result.error.lower()

    def test_optimize_extracts_tunable_parameters(self):
        """Test that optimizer extracts tunable parameters."""
        optimizer = ParameterOptimizer()

        strategy = {
            "id": "TEST-001",
            "tunable_parameters": {
                "parameters": {
                    "period": {
                        "type": "int",
                        "default": 20,
                        "min": 10,
                        "max": 30,
                        "step": 5,
                    }
                }
            },
        }

        tunable = optimizer._get_tunable_parameters(strategy)
        assert tunable is not None
        assert "period" in tunable.parameters


# =============================================================================
# TEST PARAMETER INJECTION
# =============================================================================


class TestParameterInjection:
    """Test parameter injection into strategy."""

    @pytest.fixture
    def optimizer(self):
        return ParameterOptimizer()

    def test_inject_parameters_creates_copy(self, optimizer):
        """Test that injection creates a new dict."""
        strategy = {"id": "TEST", "parameters": {"existing": 100}}
        params = {"new_param": 42}

        result = optimizer._inject_parameters(strategy, params)

        # Original unchanged
        assert "new_param" not in strategy["parameters"]
        # Result has new param
        assert result["parameters"]["new_param"] == 42
        # Result preserves existing
        assert result["parameters"]["existing"] == 100

    def test_inject_parameters_adds_optimized_dict(self, optimizer):
        """Test that injection adds _optimized dict."""
        strategy = {"id": "TEST"}
        params = {"p1": 10, "p2": 20}

        result = optimizer._inject_parameters(strategy, params)

        assert result["parameters"]["_optimized"] == params


# =============================================================================
# TEST WITH MOCKED BACKTEST
# =============================================================================


class TestOptimizationWithMockedBacktest:
    """Test optimization with mocked backtest executor."""

    def test_optimize_finds_best_sharpe(self):
        """Test optimization finds params with best Sharpe."""
        # Mock backtest executor
        mock_executor = MagicMock()
        mock_generator = MagicMock()

        # Configure mock to return different Sharpe for different params
        def mock_run_single(code, start_date, end_date, strategy_id):
            result = MagicMock()
            result.success = True
            # Simulate: period=20 has best Sharpe
            if "period" in code and "20" in code:
                result.sharpe = 2.0
                result.cagr = 0.15
            else:
                result.sharpe = 1.0
                result.cagr = 0.10
            result.max_drawdown = 0.1
            result.error = None
            return result

        mock_executor.run_single = mock_run_single

        # Configure mock generator
        def mock_generate(strategy):
            result = MagicMock()
            result.success = True
            result.code = f"# period = {strategy.get('parameters', {}).get('period', 'unknown')}"
            result.error = None
            return result

        mock_generator.generate = mock_generate

        optimizer = ParameterOptimizer(
            backtest_executor=mock_executor,
            code_generator=mock_generator,
        )

        strategy = {
            "id": "TEST-001",
            "tunable_parameters": {
                "parameters": {
                    "period": {
                        "type": "int",
                        "default": 15,
                        "min": 10,
                        "max": 20,
                        "step": 5,  # 3 values: 10, 15, 20
                    }
                }
            },
        }

        result = optimizer.optimize(
            strategy=strategy,
            start_date="2020-01-01",
            end_date="2020-12-31",
            method=OptimizationMethod.GRID,
        )

        assert result.success is True
        assert result.best_params == {"period": 20}
        assert result.best_sharpe == 2.0
        assert result.total_evaluated == 3
