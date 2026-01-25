"""Tests for walk-forward validation runner.

This module tests:
1. WalkForwardConfig period generation
2. WalkForwardRunner execution flow
3. Result aggregation
4. Parameter stability calculation
"""

import pytest
from unittest.mock import MagicMock

from research_system.optimization import (
    OptimizationMethod,
    WalkForwardConfig,
    WalkForwardPeriod,
    WalkForwardResult,
    WalkForwardRunner,
)


# =============================================================================
# TEST WALK-FORWARD CONFIG
# =============================================================================


class TestWalkForwardConfig:
    """Test walk-forward configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = WalkForwardConfig()
        assert config.start_year == 2012
        assert config.end_year == 2023
        assert config.initial_train_years == 3
        assert config.test_years == 1

    def test_get_periods_default(self):
        """Test period generation with default config."""
        config = WalkForwardConfig(
            start_year=2012,
            end_year=2020,
            initial_train_years=3,
            test_years=1,
        )
        periods = config.get_periods()

        # 2012-2014 train, 2015 test
        # 2012-2015 train, 2016 test
        # ...
        # 2012-2019 train, 2020 test
        assert len(periods) == 6

        # First period
        assert periods[0] == ("2012-01-01", "2014-12-31", "2015-01-01", "2015-12-31")

        # Last period
        assert periods[-1] == ("2012-01-01", "2019-12-31", "2020-01-01", "2020-12-31")

    def test_get_periods_rolling_window(self):
        """Test period generation with rolling (non-expanding) window."""
        config = WalkForwardConfig(
            start_year=2015,
            end_year=2020,
            initial_train_years=2,
            test_years=1,
            expanding_window=False,
        )
        periods = config.get_periods()

        # With rolling window, optimization always uses 2 years
        assert len(periods) == 4

        # First period: 2015-2016 train, 2017 test
        assert periods[0] == ("2015-01-01", "2016-12-31", "2017-01-01", "2017-12-31")

        # Second period: 2016-2017 train, 2018 test
        assert periods[1] == ("2016-01-01", "2017-12-31", "2018-01-01", "2018-12-31")

    def test_get_periods_multi_year_test(self):
        """Test period generation with multi-year test periods."""
        config = WalkForwardConfig(
            start_year=2012,
            end_year=2020,
            initial_train_years=3,
            test_years=2,
        )
        periods = config.get_periods()

        # First period
        assert periods[0] == ("2012-01-01", "2014-12-31", "2015-01-01", "2016-12-31")


# =============================================================================
# TEST WALK-FORWARD RUNNER
# =============================================================================


class TestWalkForwardRunner:
    """Test walk-forward runner."""

    def test_run_no_tunable_parameters(self):
        """Test run fails gracefully with no tunable parameters."""
        runner = WalkForwardRunner()
        strategy = {"id": "TEST-001", "name": "Test Strategy"}

        result = runner.run(strategy)

        assert result.success is False
        assert "no tunable parameters" in result.error.lower()

    def test_run_returns_result_with_config(self):
        """Test run returns result with config."""
        runner = WalkForwardRunner()
        strategy = {
            "id": "TEST-001",
            "tunable_parameters": {
                "parameters": {
                    "period": {"type": "int", "default": 20, "min": 10, "max": 30, "step": 10}
                }
            },
        }
        config = WalkForwardConfig(
            start_year=2015,
            end_year=2017,
            initial_train_years=1,
            test_years=1,
        )

        result = runner.run(strategy, config)

        assert result.strategy_id == "TEST-001"
        assert result.config == config


# =============================================================================
# TEST RESULT AGGREGATION
# =============================================================================


class TestResultAggregation:
    """Test result aggregation."""

    @pytest.fixture
    def runner(self):
        return WalkForwardRunner()

    def test_aggregate_oos_sharpe(self, runner):
        """Test OOS Sharpe aggregation."""
        result = WalkForwardResult(
            strategy_id="TEST",
            config=WalkForwardConfig(),
            periods=[
                WalkForwardPeriod(
                    period_id=1,
                    opt_start="2012-01-01",
                    opt_end="2014-12-31",
                    test_start="2015-01-01",
                    test_end="2015-12-31",
                    oos_sharpe=1.5,
                    oos_cagr=0.12,
                    success=True,
                ),
                WalkForwardPeriod(
                    period_id=2,
                    opt_start="2012-01-01",
                    opt_end="2015-12-31",
                    test_start="2016-01-01",
                    test_end="2016-12-31",
                    oos_sharpe=0.8,
                    oos_cagr=0.08,
                    success=True,
                ),
            ],
        )

        runner._aggregate_results(result)

        assert result.avg_oos_sharpe == pytest.approx(1.15, 0.01)
        assert result.worst_oos_sharpe == pytest.approx(0.8, 0.01)
        assert result.consistency == 1.0  # Both profitable

    def test_aggregate_consistency(self, runner):
        """Test consistency calculation."""
        result = WalkForwardResult(
            strategy_id="TEST",
            config=WalkForwardConfig(),
            periods=[
                WalkForwardPeriod(
                    period_id=1,
                    opt_start="2012-01-01",
                    opt_end="2014-12-31",
                    test_start="2015-01-01",
                    test_end="2015-12-31",
                    oos_cagr=0.10,
                    success=True,
                ),
                WalkForwardPeriod(
                    period_id=2,
                    opt_start="2012-01-01",
                    opt_end="2015-12-31",
                    test_start="2016-01-01",
                    test_end="2016-12-31",
                    oos_cagr=-0.05,  # Negative
                    success=True,
                ),
                WalkForwardPeriod(
                    period_id=3,
                    opt_start="2012-01-01",
                    opt_end="2016-12-31",
                    test_start="2017-01-01",
                    test_end="2017-12-31",
                    oos_cagr=0.08,
                    success=True,
                ),
            ],
        )

        runner._aggregate_results(result)

        # 2 out of 3 profitable
        assert result.consistency == pytest.approx(2 / 3, 0.01)

    def test_aggregate_is_vs_oos_degradation(self, runner):
        """Test IS vs OOS degradation calculation."""
        result = WalkForwardResult(
            strategy_id="TEST",
            config=WalkForwardConfig(),
            periods=[
                WalkForwardPeriod(
                    period_id=1,
                    opt_start="2012-01-01",
                    opt_end="2014-12-31",
                    test_start="2015-01-01",
                    test_end="2015-12-31",
                    optimization_sharpe=2.0,  # IS
                    oos_sharpe=1.5,  # OOS
                    success=True,
                ),
                WalkForwardPeriod(
                    period_id=2,
                    opt_start="2012-01-01",
                    opt_end="2015-12-31",
                    test_start="2016-01-01",
                    test_end="2016-12-31",
                    optimization_sharpe=1.8,  # IS
                    oos_sharpe=1.2,  # OOS
                    success=True,
                ),
            ],
        )

        runner._aggregate_results(result)

        # Avg IS = 1.9, Avg OOS = 1.35
        # Degradation = (1.9 - 1.35) / 1.9 = 0.289
        assert result.is_vs_oos_degradation == pytest.approx(0.289, 0.01)


# =============================================================================
# TEST PARAMETER STABILITY
# =============================================================================


class TestParameterStability:
    """Test parameter stability calculation."""

    @pytest.fixture
    def runner(self):
        return WalkForwardRunner()

    def test_perfect_stability(self, runner):
        """Test perfect stability when params don't change."""
        result = WalkForwardResult(
            strategy_id="TEST",
            config=WalkForwardConfig(),
            periods=[
                WalkForwardPeriod(
                    period_id=1,
                    opt_start="2012-01-01",
                    opt_end="2014-12-31",
                    test_start="2015-01-01",
                    test_end="2015-12-31",
                    optimized_params={"period": 20},
                    success=True,
                ),
                WalkForwardPeriod(
                    period_id=2,
                    opt_start="2012-01-01",
                    opt_end="2015-12-31",
                    test_start="2016-01-01",
                    test_end="2016-12-31",
                    optimized_params={"period": 20},
                    success=True,
                ),
            ],
        )

        runner._calculate_parameter_stability(result)

        assert result.parameter_stability == 1.0

    def test_varying_params(self, runner):
        """Test stability with varying params."""
        result = WalkForwardResult(
            strategy_id="TEST",
            config=WalkForwardConfig(),
            periods=[
                WalkForwardPeriod(
                    period_id=1,
                    opt_start="2012-01-01",
                    opt_end="2014-12-31",
                    test_start="2015-01-01",
                    test_end="2015-12-31",
                    optimized_params={"period": 10},
                    success=True,
                ),
                WalkForwardPeriod(
                    period_id=2,
                    opt_start="2012-01-01",
                    opt_end="2015-12-31",
                    test_start="2016-01-01",
                    test_end="2016-12-31",
                    optimized_params={"period": 30},
                    success=True,
                ),
                WalkForwardPeriod(
                    period_id=3,
                    opt_start="2012-01-01",
                    opt_end="2016-12-31",
                    test_start="2017-01-01",
                    test_end="2017-12-31",
                    optimized_params={"period": 50},
                    success=True,
                ),
            ],
        )

        runner._calculate_parameter_stability(result)

        # Params vary significantly, stability should be lower
        assert result.parameter_stability is not None
        assert result.parameter_stability < 1.0


# =============================================================================
# TEST WALK-FORWARD RESULT
# =============================================================================


class TestWalkForwardResultSerialization:
    """Test WalkForwardResult serialization."""

    def test_to_dict(self):
        """Test result serialization."""
        result = WalkForwardResult(
            strategy_id="TEST-001",
            config=WalkForwardConfig(start_year=2015, end_year=2020),
            periods=[
                WalkForwardPeriod(
                    period_id=1,
                    opt_start="2015-01-01",
                    opt_end="2017-12-31",
                    test_start="2018-01-01",
                    test_end="2018-12-31",
                    optimized_params={"period": 20},
                    oos_sharpe=1.5,
                    success=True,
                ),
            ],
            avg_oos_sharpe=1.5,
            consistency=1.0,
            success=True,
        )

        data = result.to_dict()

        assert data["strategy_id"] == "TEST-001"
        assert data["config"]["start_year"] == 2015
        assert len(data["periods"]) == 1
        assert data["periods"][0]["oos_sharpe"] == 1.5
        assert data["avg_oos_sharpe"] == 1.5
        assert data["success"] is True
