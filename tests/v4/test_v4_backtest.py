"""Tests for V4 backtest infrastructure.

This module tests:
1. Date injection into algorithm code
2. LEAN output parsing
3. Rate limit detection
4. Walk-forward window calculation
5. Result aggregation
"""

import pytest

from research_system.validation.backtest import (
    BacktestExecutor,
    BacktestResult,
    WalkForwardResult,
    WalkForwardWindow,
)


# =============================================================================
# TEST DATE INJECTION
# =============================================================================


class TestDateInjection:
    """Test date injection into algorithm code."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create a backtest executor with temp workspace."""
        return BacktestExecutor(workspace_path=tmp_path, use_local=True, cleanup_on_start=False)

    def test_inject_snake_case_dates(self, executor):
        """Test injection of snake_case date methods."""
        code = """
class MyAlgo(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2023, 12, 31)
"""
        result = executor._inject_dates(code, "2015-01-01", "2019-12-31")

        assert "set_start_date(2015, 1, 1)" in result
        assert "set_end_date(2019, 12, 31)" in result
        assert "2020" not in result
        assert "2023" not in result

    def test_inject_pascal_case_dates(self, executor):
        """Test injection of PascalCase date methods."""
        code = """
class MyAlgo(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2023, 12, 31)
"""
        result = executor._inject_dates(code, "2015-01-01", "2019-12-31")

        assert "SetStartDate(2015, 1, 1)" in result
        assert "SetEndDate(2019, 12, 31)" in result

    def test_inject_mixed_case_dates(self, executor):
        """Test injection handles mixed case correctly."""
        code = """
self.set_start_date(2020, 1, 1)
self.SetEndDate(2023, 12, 31)
"""
        result = executor._inject_dates(code, "2018-06-15", "2022-03-20")

        assert "set_start_date(2018, 6, 15)" in result
        assert "SetEndDate(2022, 3, 20)" in result


# =============================================================================
# TEST LEAN OUTPUT PARSING
# =============================================================================


class TestLeanOutputParsing:
    """Test parsing of LEAN CLI output."""

    @pytest.fixture
    def executor(self, tmp_path):
        return BacktestExecutor(workspace_path=tmp_path, use_local=True, cleanup_on_start=False)

    def test_parse_engine_crash(self, executor):
        """Test detection of LEAN engine crashes."""
        stdout = "Some output\nPAL_SEHException occurred\nMore output"
        stderr = ""

        result = executor._parse_lean_output(stdout, stderr, 0)

        assert not result.success
        assert result.engine_crash
        assert "LEAN engine crash" in result.error

    def test_parse_rate_limit(self, executor):
        """Test detection of rate limiting."""
        stdout = "Backtest failed\nno spare nodes available\nPlease try again"
        stderr = ""

        result = executor._parse_lean_output(stdout, stderr, 1)

        assert not result.success
        assert result.rate_limited
        assert "Rate limited" in result.error or "no spare nodes" in result.error.lower()

    def test_parse_runtime_error(self, executor):
        """Test detection of backtest runtime errors."""
        stdout = "Backtest started\nAn error occurred during this backtest: KeyError 'price'\nBacktest failed"
        stderr = ""

        result = executor._parse_lean_output(stdout, stderr, 0)

        assert not result.success
        assert "runtime error" in result.error.lower()

    def test_parse_table_metrics(self, executor):
        """Test parsing of table metrics."""
        # Simulate LEAN table output format
        stdout = """
│ Compounding Annual        │ 15.50%  │
│ Sharpe Ratio              │ 1.25    │
│ Drawdown                  │ -12.30% │
│ Alpha                     │ 0.08    │
"""
        result = executor._parse_lean_output_table(stdout)

        assert result.success
        assert result.cagr == pytest.approx(0.155, rel=0.01)
        assert result.sharpe == pytest.approx(1.25, rel=0.01)
        # Note: drawdown is stored as positive
        assert result.max_drawdown == pytest.approx(0.123, rel=0.01)


# =============================================================================
# TEST BACKTEST ID EXTRACTION
# =============================================================================


class TestBacktestIdExtraction:
    """Test extraction of project/backtest IDs from output."""

    @pytest.fixture
    def executor(self, tmp_path):
        return BacktestExecutor(workspace_path=tmp_path, use_local=True, cleanup_on_start=False)

    def test_extract_ids_from_output(self, executor):
        """Test extraction of project and backtest IDs."""
        stdout = """
Uploading project...
Project ID: 27018367
Starting backtest...
Backtest id: 205d98ce63238f18187f9da04186e199
Running...
"""
        project_id, backtest_id = executor._extract_backtest_ids(stdout)

        assert project_id == "27018367"
        assert backtest_id == "205d98ce63238f18187f9da04186e199"

    def test_extract_ids_missing_project(self, executor):
        """Test handling when project ID is missing."""
        stdout = "Backtest id: abc123"
        project_id, backtest_id = executor._extract_backtest_ids(stdout)

        assert project_id is None
        assert backtest_id == "abc123"

    def test_extract_ids_missing_backtest(self, executor):
        """Test handling when backtest ID is missing."""
        stdout = "Project ID: 12345"
        project_id, backtest_id = executor._extract_backtest_ids(stdout)

        assert project_id == "12345"
        assert backtest_id is None


# =============================================================================
# TEST WALK-FORWARD AGGREGATION
# =============================================================================


class TestWalkForwardAggregation:
    """Test walk-forward result aggregation."""

    @pytest.fixture
    def executor(self, tmp_path):
        return BacktestExecutor(workspace_path=tmp_path, use_local=True, cleanup_on_start=False)

    def test_aggregate_all_successful_windows(self, executor):
        """Test aggregation when all windows succeed."""
        wf_result = WalkForwardResult(strategy_id="TEST-001")
        wf_result.windows = [
            WalkForwardWindow(
                window_id=1,
                start_date="2012-01-01",
                end_date="2015-12-31",
                result=BacktestResult(success=True, cagr=0.15, sharpe=1.2, max_drawdown=0.10),
            ),
            WalkForwardWindow(
                window_id=2,
                start_date="2014-01-01",
                end_date="2017-12-31",
                result=BacktestResult(success=True, cagr=0.12, sharpe=1.0, max_drawdown=0.15),
            ),
            WalkForwardWindow(
                window_id=3,
                start_date="2016-01-01",
                end_date="2019-12-31",
                result=BacktestResult(success=True, cagr=0.10, sharpe=0.8, max_drawdown=0.20),
            ),
        ]

        executor._aggregate_walk_forward_results(wf_result)

        # Mean return should be average of 0.15, 0.12, 0.10 = 0.1233
        assert wf_result.mean_return == pytest.approx(0.1233, rel=0.01)
        # Median of 0.10, 0.12, 0.15 = 0.12
        assert wf_result.median_return == pytest.approx(0.12, rel=0.01)
        # Aggregate Sharpe = mean of 1.2, 1.0, 0.8 = 1.0
        assert wf_result.aggregate_sharpe == pytest.approx(1.0, rel=0.01)
        # Max drawdown = worst = 0.20
        assert wf_result.max_drawdown == pytest.approx(0.20, rel=0.01)
        # Consistency = 3/3 = 1.0 (all positive CAGR)
        assert wf_result.consistency == pytest.approx(1.0, rel=0.01)

    def test_aggregate_with_failed_windows(self, executor):
        """Test aggregation excludes failed windows."""
        wf_result = WalkForwardResult(strategy_id="TEST-002")
        wf_result.windows = [
            WalkForwardWindow(
                window_id=1,
                start_date="2012-01-01",
                end_date="2015-12-31",
                result=BacktestResult(success=True, cagr=0.15, sharpe=1.2, max_drawdown=0.10),
            ),
            WalkForwardWindow(
                window_id=2,
                start_date="2014-01-01",
                end_date="2017-12-31",
                result=BacktestResult(success=False, error="Runtime error"),
            ),
            WalkForwardWindow(
                window_id=3,
                start_date="2016-01-01",
                end_date="2019-12-31",
                result=BacktestResult(success=True, cagr=0.10, sharpe=0.8, max_drawdown=0.20),
            ),
        ]

        executor._aggregate_walk_forward_results(wf_result)

        # Should only use 2 successful windows
        assert wf_result.mean_return == pytest.approx(0.125, rel=0.01)  # (0.15 + 0.10) / 2

    def test_aggregate_no_successful_windows(self, executor):
        """Test aggregation when no windows succeed."""
        wf_result = WalkForwardResult(strategy_id="TEST-003")
        wf_result.windows = [
            WalkForwardWindow(
                window_id=1,
                start_date="2012-01-01",
                end_date="2015-12-31",
                result=BacktestResult(success=False, error="Error 1"),
            ),
            WalkForwardWindow(
                window_id=2,
                start_date="2014-01-01",
                end_date="2017-12-31",
                result=BacktestResult(success=False, error="Error 2"),
            ),
        ]

        executor._aggregate_walk_forward_results(wf_result)

        assert wf_result.determination == "BLOCKED"
        assert "No successful" in wf_result.determination_reason

    def test_consistency_with_negative_returns(self, executor):
        """Test consistency calculation with negative CAGR windows."""
        wf_result = WalkForwardResult(strategy_id="TEST-004")
        wf_result.windows = [
            WalkForwardWindow(
                window_id=1,
                start_date="2012-01-01",
                end_date="2015-12-31",
                result=BacktestResult(success=True, cagr=0.15, sharpe=1.2, max_drawdown=0.10),
            ),
            WalkForwardWindow(
                window_id=2,
                start_date="2014-01-01",
                end_date="2017-12-31",
                result=BacktestResult(success=True, cagr=-0.05, sharpe=-0.3, max_drawdown=0.25),
            ),
            WalkForwardWindow(
                window_id=3,
                start_date="2016-01-01",
                end_date="2019-12-31",
                result=BacktestResult(success=True, cagr=0.10, sharpe=0.8, max_drawdown=0.15),
            ),
        ]

        executor._aggregate_walk_forward_results(wf_result)

        # Consistency = 2/3 (only 2 windows with positive CAGR)
        assert wf_result.consistency == pytest.approx(0.6667, rel=0.01)


# =============================================================================
# TEST BACKTEST RESULT SERIALIZATION
# =============================================================================


class TestBacktestResultSerialization:
    """Test BacktestResult serialization."""

    def test_to_dict(self):
        """Test BacktestResult.to_dict() method."""
        result = BacktestResult(
            success=True,
            cagr=0.15,
            sharpe=1.2,
            max_drawdown=0.10,
            alpha=0.05,
            win_rate=0.55,
            total_trades=100,
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["cagr"] == 0.15
        assert d["sharpe"] == 1.2
        assert d["max_drawdown"] == 0.10
        assert d["alpha"] == 0.05
        assert d["win_rate"] == 0.55
        assert d["total_trades"] == 100

    def test_walk_forward_result_to_dict(self):
        """Test WalkForwardResult.to_dict() method."""
        wf_result = WalkForwardResult(
            strategy_id="TEST-001",
            mean_return=0.12,
            consistency=0.8,
            determination="VALIDATED",
        )
        wf_result.windows = [
            WalkForwardWindow(
                window_id=1,
                start_date="2012-01-01",
                end_date="2015-12-31",
                result=BacktestResult(success=True, cagr=0.12),
            ),
        ]

        d = wf_result.to_dict()

        assert d["strategy_id"] == "TEST-001"
        assert d["mean_return"] == 0.12
        assert d["consistency"] == 0.8
        assert d["determination"] == "VALIDATED"
        assert len(d["windows"]) == 1
        assert d["windows"][0]["window_id"] == 1
