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


# =============================================================================
# TEST REUSE PROJECT MODE
# =============================================================================


class TestOOSAggregation:
    """Test OOS-specific aggregation for IS/OOS mode."""

    @pytest.fixture
    def executor(self, tmp_path):
        return BacktestExecutor(workspace_path=tmp_path, use_local=True, cleanup_on_start=False)

    def test_oos_aggregation_uses_last_window(self, executor):
        """Test that OOS aggregation uses only the last window for gates."""
        wf_result = WalkForwardResult(strategy_id="TEST-OOS-1")
        wf_result.windows = [
            WalkForwardWindow(
                window_id=1,
                start_date="2012-01-01",
                end_date="2017-12-31",
                result=BacktestResult(success=True, cagr=0.25, sharpe=2.0, max_drawdown=0.10),
            ),
            WalkForwardWindow(
                window_id=2,
                start_date="2018-01-01",
                end_date="2023-12-31",
                result=BacktestResult(success=True, cagr=0.08, sharpe=0.5, max_drawdown=0.30),
            ),
        ]

        executor._aggregate_oos_results(wf_result)

        # Gates should be based on OOS (window 2) only
        assert wf_result.aggregate_sharpe == pytest.approx(0.5)
        assert wf_result.aggregate_cagr == pytest.approx(0.08)
        assert wf_result.max_drawdown == pytest.approx(0.30)
        # Mean return uses both windows
        assert wf_result.mean_return == pytest.approx(0.165, rel=0.01)

    def test_oos_aggregation_failed_oos_window(self, executor):
        """Test that failed OOS window marks result as BLOCKED."""
        wf_result = WalkForwardResult(strategy_id="TEST-OOS-2")
        wf_result.windows = [
            WalkForwardWindow(
                window_id=1,
                start_date="2012-01-01",
                end_date="2017-12-31",
                result=BacktestResult(success=True, cagr=0.20, sharpe=1.5, max_drawdown=0.10),
            ),
            WalkForwardWindow(
                window_id=2,
                start_date="2018-01-01",
                end_date="2023-12-31",
                result=BacktestResult(success=False, error="Runtime error"),
            ),
        ]

        executor._aggregate_oos_results(wf_result)

        assert wf_result.determination == "BLOCKED"
        assert "OOS window failed" in wf_result.determination_reason

    def test_oos_aggregation_single_window_falls_back(self, executor):
        """Test that single-window mode falls back to standard aggregation."""
        wf_result = WalkForwardResult(strategy_id="TEST-OOS-3")
        wf_result.windows = [
            WalkForwardWindow(
                window_id=1,
                start_date="2012-01-01",
                end_date="2023-12-31",
                result=BacktestResult(success=True, cagr=0.15, sharpe=1.2, max_drawdown=0.12),
            ),
        ]

        executor._aggregate_oos_results(wf_result)

        # Should fall back to standard aggregation
        assert wf_result.aggregate_sharpe == pytest.approx(1.2)
        assert wf_result.aggregate_cagr == pytest.approx(0.15)

    def test_oos_consistency_uses_all_windows(self, executor):
        """Test consistency calculation uses all windows, not just OOS."""
        wf_result = WalkForwardResult(strategy_id="TEST-OOS-4")
        wf_result.windows = [
            WalkForwardWindow(
                window_id=1,
                start_date="2012-01-01",
                end_date="2017-12-31",
                result=BacktestResult(success=True, cagr=-0.05, sharpe=-0.3, max_drawdown=0.25),
            ),
            WalkForwardWindow(
                window_id=2,
                start_date="2018-01-01",
                end_date="2023-12-31",
                result=BacktestResult(success=True, cagr=0.10, sharpe=0.8, max_drawdown=0.15),
            ),
        ]

        executor._aggregate_oos_results(wf_result)

        # Consistency = 1/2 = 0.5 (one window negative)
        assert wf_result.consistency == pytest.approx(0.5)


class TestDefaultWindows:
    """Test that default window configuration is IS/OOS."""

    def test_default_is_two_windows(self, tmp_path):
        """Executor with num_windows=2 uses IS/OOS windows."""
        executor = BacktestExecutor(
            workspace_path=tmp_path, use_local=True, cleanup_on_start=False,
            num_windows=2,
        )
        assert len(executor.windows) == 2
        assert executor.windows[0] == ("2012-01-01", "2017-12-31")
        assert executor.windows[1] == ("2018-01-01", "2023-12-31")

    def test_one_window_explicit(self, tmp_path):
        """Explicit --windows 1 uses single full period."""
        executor = BacktestExecutor(
            workspace_path=tmp_path, use_local=True, cleanup_on_start=False,
            num_windows=1,
        )
        assert len(executor.windows) == 1
        assert executor.windows[0] == ("2012-01-01", "2023-12-31")

    def test_five_windows(self, tmp_path):
        """--windows 5 uses all rolling windows."""
        executor = BacktestExecutor(
            workspace_path=tmp_path, use_local=True, cleanup_on_start=False,
            num_windows=5,
        )
        assert len(executor.windows) == 5


class TestReuseProject:
    """Test reusable project mode for avoiding QC 100/day project limit."""

    def test_reuse_project_default_true_for_cloud(self, tmp_path):
        """Reuse mode defaults to True for cloud execution."""
        executor = BacktestExecutor(
            workspace_path=tmp_path, use_local=False, cleanup_on_start=False
        )
        assert executor.reuse_project is True

    def test_reuse_project_disabled_for_local(self, tmp_path):
        """Reuse mode is always disabled for local Docker execution."""
        executor = BacktestExecutor(
            workspace_path=tmp_path, use_local=True, cleanup_on_start=False,
            reuse_project=True,
        )
        assert executor.reuse_project is False

    def test_reuse_project_explicit_false(self, tmp_path):
        """Reuse mode can be explicitly disabled."""
        executor = BacktestExecutor(
            workspace_path=tmp_path, use_local=False, cleanup_on_start=False,
            reuse_project=False,
        )
        assert executor.reuse_project is False

    def test_runner_project_dir(self, tmp_path):
        """Runner project dir is at validations/_runner."""
        executor = BacktestExecutor(
            workspace_path=tmp_path, use_local=False, cleanup_on_start=False
        )
        assert executor._runner_project_dir == tmp_path / "validations" / "_runner"

    def test_reuse_creates_fixed_dir(self, tmp_path):
        """Reuse mode creates files in the fixed _runner directory."""
        import json
        from unittest.mock import patch

        executor = BacktestExecutor(
            workspace_path=tmp_path, use_local=False, cleanup_on_start=False,
            reuse_project=True,
        )

        # Mock _execute_backtest to avoid actual lean CLI calls
        mock_result = BacktestResult(success=True, cagr=0.10, sharpe=0.5)
        with patch.object(executor, '_execute_backtest', return_value=mock_result):
            result = executor.run_single(
                "class Algo: pass", "2012-01-01", "2023-12-31", "STRAT-TEST"
            )

        assert result.success is True
        # Check that main.py was written to _runner dir
        runner_main = tmp_path / "validations" / "_runner" / "main.py"
        assert runner_main.exists()
        # Check config.json exists
        runner_config = tmp_path / "validations" / "_runner" / "config.json"
        assert runner_config.exists()

    def test_reuse_does_not_cleanup_dir(self, tmp_path):
        """Reuse mode preserves the _runner directory after backtest."""
        from unittest.mock import patch

        executor = BacktestExecutor(
            workspace_path=tmp_path, use_local=False, cleanup_on_start=False,
            reuse_project=True,
        )

        mock_result = BacktestResult(success=True, cagr=0.10, sharpe=0.5)
        with patch.object(executor, '_execute_backtest', return_value=mock_result):
            executor.run_single("class Algo: pass", "2012-01-01", "2023-12-31", "STRAT-TEST")

        # Directory should still exist
        assert (tmp_path / "validations" / "_runner").exists()
        assert (tmp_path / "validations" / "_runner" / "main.py").exists()

    def test_reuse_overwrites_main_py(self, tmp_path):
        """Reuse mode overwrites main.py on each run."""
        from unittest.mock import patch

        executor = BacktestExecutor(
            workspace_path=tmp_path, use_local=False, cleanup_on_start=False,
            reuse_project=True,
        )

        mock_result = BacktestResult(success=True, cagr=0.10, sharpe=0.5)
        with patch.object(executor, '_execute_backtest', return_value=mock_result):
            # First run
            executor.run_single("class First: pass", "2012-01-01", "2023-12-31", "STRAT-A")
            content1 = (tmp_path / "validations" / "_runner" / "main.py").read_text()

            # Second run — should overwrite
            executor.run_single("class Second: pass", "2012-01-01", "2023-12-31", "STRAT-B")
            content2 = (tmp_path / "validations" / "_runner" / "main.py").read_text()

        assert "First" not in content2
        assert "Second" in content2

    def test_legacy_mode_creates_unique_dirs(self, tmp_path):
        """Legacy mode (reuse_project=False) creates unique project dirs."""
        from unittest.mock import patch

        executor = BacktestExecutor(
            workspace_path=tmp_path, use_local=False, cleanup_on_start=False,
            reuse_project=False,
        )

        mock_result = BacktestResult(success=True, cagr=0.10, sharpe=0.5)
        with patch.object(executor, '_execute_backtest', return_value=mock_result):
            executor.run_single("class Algo: pass", "2012-01-01", "2023-12-31", "STRAT-TEST")

        # _runner dir should NOT exist
        assert not (tmp_path / "validations" / "_runner").exists()
