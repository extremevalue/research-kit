"""Tests for walk-forward reporting and analysis.

This module tests:
1. Terminal summary formatting
2. JSON output formatting
3. Parameter evolution display
4. Verdict generation
"""

import json
import pytest

from research_system.optimization import (
    WalkForwardConfig,
    WalkForwardPeriod,
    WalkForwardResult,
    format_terminal_summary,
    format_json_output,
    format_parameter_evolution,
)


# =============================================================================
# TEST TERMINAL SUMMARY
# =============================================================================


class TestTerminalSummary:
    """Test terminal summary formatting."""

    @pytest.fixture
    def successful_result(self):
        """Create a successful walk-forward result."""
        return WalkForwardResult(
            strategy_id="TEST-001",
            config=WalkForwardConfig(
                start_year=2015,
                end_year=2020,
                initial_train_years=3,
                test_years=1,
            ),
            periods=[
                WalkForwardPeriod(
                    period_id=1,
                    opt_start="2015-01-01",
                    opt_end="2017-12-31",
                    test_start="2018-01-01",
                    test_end="2018-12-31",
                    optimization_sharpe=1.8,
                    oos_sharpe=1.5,
                    oos_cagr=0.12,
                    optimized_params={"period": 20},
                    success=True,
                ),
                WalkForwardPeriod(
                    period_id=2,
                    opt_start="2015-01-01",
                    opt_end="2018-12-31",
                    test_start="2019-01-01",
                    test_end="2019-12-31",
                    optimization_sharpe=1.6,
                    oos_sharpe=1.2,
                    oos_cagr=0.10,
                    optimized_params={"period": 25},
                    success=True,
                ),
            ],
            avg_oos_sharpe=1.35,
            avg_oos_cagr=0.11,
            worst_oos_sharpe=1.2,
            consistency=1.0,
            is_vs_oos_degradation=0.21,
            parameter_stability=0.85,
            success=True,
        )

    def test_summary_contains_strategy_id(self, successful_result):
        """Test summary includes strategy ID."""
        summary = format_terminal_summary(successful_result)
        assert "TEST-001" in summary

    def test_summary_contains_period_count(self, successful_result):
        """Test summary includes period count."""
        summary = format_terminal_summary(successful_result)
        assert "Periods:  2" in summary

    def test_summary_contains_config_info(self, successful_result):
        """Test summary includes configuration details."""
        summary = format_terminal_summary(successful_result)
        assert "2015 - 2020" in summary
        assert "3 years" in summary
        assert "1 year" in summary

    def test_summary_contains_period_details(self, successful_result):
        """Test summary includes individual period details."""
        summary = format_terminal_summary(successful_result)
        assert "Period 1:" in summary
        assert "Period 2:" in summary
        assert "IS Sharpe:" in summary
        assert "OOS Sharpe:" in summary

    def test_summary_contains_aggregate_metrics(self, successful_result):
        """Test summary includes aggregate metrics."""
        summary = format_terminal_summary(successful_result)
        assert "Avg OOS Sharpe:" in summary
        assert "1.35" in summary
        assert "Worst OOS Sharpe:" in summary

    def test_summary_contains_quality_metrics(self, successful_result):
        """Test summary includes quality metrics."""
        summary = format_terminal_summary(successful_result)
        assert "Consistency:" in summary
        assert "100%" in summary
        assert "Parameter Stability:" in summary

    def test_summary_contains_verdict(self, successful_result):
        """Test summary includes verdict."""
        summary = format_terminal_summary(successful_result)
        assert "Verdict:" in summary

    def test_summary_failed_period(self):
        """Test summary handles failed periods."""
        result = WalkForwardResult(
            strategy_id="TEST-002",
            config=WalkForwardConfig(),
            periods=[
                WalkForwardPeriod(
                    period_id=1,
                    opt_start="2012-01-01",
                    opt_end="2014-12-31",
                    test_start="2015-01-01",
                    test_end="2015-12-31",
                    success=False,
                    error="Backtest timeout",
                ),
            ],
            success=False,
            error="No successful periods",
        )

        summary = format_terminal_summary(result)
        assert "✗" in summary  # Failed indicator
        assert "Backtest timeout" in summary


# =============================================================================
# TEST JSON OUTPUT
# =============================================================================


class TestJsonOutput:
    """Test JSON output formatting."""

    @pytest.fixture
    def result(self):
        """Create a walk-forward result."""
        return WalkForwardResult(
            strategy_id="TEST-001",
            config=WalkForwardConfig(start_year=2015, end_year=2020),
            periods=[
                WalkForwardPeriod(
                    period_id=1,
                    opt_start="2015-01-01",
                    opt_end="2017-12-31",
                    test_start="2018-01-01",
                    test_end="2018-12-31",
                    oos_sharpe=1.5,
                    success=True,
                ),
            ],
            avg_oos_sharpe=1.5,
            success=True,
        )

    def test_json_is_valid(self, result):
        """Test output is valid JSON."""
        output = format_json_output(result)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_json_contains_strategy_id(self, result):
        """Test JSON contains strategy ID."""
        output = format_json_output(result)
        parsed = json.loads(output)
        assert parsed["strategy_id"] == "TEST-001"

    def test_json_contains_config(self, result):
        """Test JSON contains configuration."""
        output = format_json_output(result)
        parsed = json.loads(output)
        assert parsed["config"]["start_year"] == 2015
        assert parsed["config"]["end_year"] == 2020

    def test_json_contains_periods(self, result):
        """Test JSON contains period details."""
        output = format_json_output(result)
        parsed = json.loads(output)
        assert len(parsed["periods"]) == 1
        assert parsed["periods"][0]["oos_sharpe"] == 1.5

    def test_json_contains_verdict(self, result):
        """Test JSON contains verdict for successful result."""
        output = format_json_output(result)
        parsed = json.loads(output)
        assert "verdict" in parsed

    def test_json_pretty_formatting(self, result):
        """Test pretty formatting includes indentation."""
        pretty = format_json_output(result, pretty=True)
        compact = format_json_output(result, pretty=False)
        assert len(pretty) > len(compact)  # Pretty has indentation
        assert "\n" in pretty

    def test_json_compact_formatting(self, result):
        """Test compact formatting has no indentation."""
        compact = format_json_output(result, pretty=False)
        assert "\n" not in compact


# =============================================================================
# TEST PARAMETER EVOLUTION
# =============================================================================


class TestParameterEvolution:
    """Test parameter evolution display."""

    def test_evolution_shows_parameter_values(self):
        """Test evolution shows values across periods."""
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
                    optimized_params={"period": 20, "threshold": 0.5},
                    success=True,
                ),
                WalkForwardPeriod(
                    period_id=2,
                    opt_start="2012-01-01",
                    opt_end="2015-12-31",
                    test_start="2016-01-01",
                    test_end="2016-12-31",
                    optimized_params={"period": 25, "threshold": 0.6},
                    success=True,
                ),
            ],
        )

        evolution = format_parameter_evolution(result)
        assert "period:" in evolution
        assert "threshold:" in evolution
        assert "2015" in evolution  # Year from test_start
        assert "2016" in evolution

    def test_evolution_no_params(self):
        """Test evolution handles no parameters."""
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
                    success=True,
                ),
            ],
        )

        evolution = format_parameter_evolution(result)
        assert "No parameters tracked" in evolution


# =============================================================================
# TEST VERDICT GENERATION
# =============================================================================


class TestVerdictGeneration:
    """Test verdict generation logic."""

    def test_strong_verdict(self):
        """Test strong verdict for excellent results."""
        result = WalkForwardResult(
            strategy_id="TEST",
            config=WalkForwardConfig(),
            periods=[],
            avg_oos_sharpe=1.5,
            consistency=0.9,
            is_vs_oos_degradation=0.1,
            parameter_stability=0.9,
            success=True,
        )

        summary = format_terminal_summary(result)
        assert "STRONG" in summary

    def test_weak_verdict_multiple_issues(self):
        """Test weak verdict for multiple issues."""
        result = WalkForwardResult(
            strategy_id="TEST",
            config=WalkForwardConfig(),
            periods=[],
            avg_oos_sharpe=0.3,  # Low Sharpe
            consistency=0.3,  # Inconsistent
            is_vs_oos_degradation=0.6,  # High degradation
            parameter_stability=0.3,  # Unstable
            success=True,
        )

        summary = format_terminal_summary(result)
        assert "WEAK" in summary

    def test_caution_verdict_single_issue(self):
        """Test caution verdict for single issue."""
        result = WalkForwardResult(
            strategy_id="TEST",
            config=WalkForwardConfig(),
            periods=[],
            avg_oos_sharpe=1.2,  # Good
            consistency=0.8,  # Good
            is_vs_oos_degradation=0.55,  # High degradation only
            parameter_stability=0.85,  # Good
            success=True,
        )

        summary = format_terminal_summary(result)
        assert "CAUTION" in summary
        assert "overfitting" in summary.lower()

    def test_failed_verdict(self):
        """Test verdict for failed validation."""
        result = WalkForwardResult(
            strategy_id="TEST",
            config=WalkForwardConfig(),
            periods=[],
            success=False,
            error="No successful periods",
        )

        summary = format_terminal_summary(result)
        assert "Validation Failed" in summary
        assert "No successful periods" in summary
