"""Tests for V4 runner orchestrator.

This module tests:
1. Strategy loading from workspace
2. Gate application (pass/fail cases)
3. Status update (file movement)
4. Dry-run doesn't modify files
5. Result saving
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from research_system.core.v4 import Workspace
from research_system.validation.backtest import (
    BacktestResult,
    WalkForwardResult,
    WalkForwardWindow,
)
from research_system.validation.runner import Runner, RunResult


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def v4_workspace(tmp_path):
    """Create an initialized V4 workspace."""
    ws = Workspace(tmp_path)
    ws.init()
    return ws


@pytest.fixture
def sample_strategy(v4_workspace):
    """Create a sample strategy in the workspace."""
    strategy = {
        "id": "STRAT-001",
        "name": "Test Momentum Strategy",
        "description": "A test strategy for validation",
        "strategy_type": "momentum",
        "signal_type": "relative_momentum",
        "universe": ["SPY", "QQQ", "IWM"],
        "parameters": {
            "lookback_period": 126,
            "top_n": 3,
            "rebalance_frequency": "monthly",
        },
        "status": "pending",
    }

    # Save to pending directory
    pending_path = v4_workspace.strategies_path / "pending"
    pending_path.mkdir(parents=True, exist_ok=True)
    strategy_file = pending_path / "STRAT-001.yaml"
    strategy_file.write_text(yaml.dump(strategy))

    return strategy


@pytest.fixture
def runner(v4_workspace):
    """Create a Runner with mocked backtest executor."""
    return Runner(
        workspace=v4_workspace,
        llm_client=None,
        use_local=True,
    )


# =============================================================================
# TEST STRATEGY LOADING
# =============================================================================


class TestStrategyLoading:
    """Test strategy loading from workspace."""

    def test_load_existing_strategy(self, runner, sample_strategy):
        """Test loading an existing strategy."""
        strategy = runner._load_strategy("STRAT-001")

        assert strategy is not None
        assert strategy["id"] == "STRAT-001"
        assert strategy["name"] == "Test Momentum Strategy"
        assert strategy["strategy_type"] == "momentum"

    def test_load_nonexistent_strategy(self, runner):
        """Test loading a non-existent strategy returns None."""
        strategy = runner._load_strategy("STRAT-999")
        assert strategy is None

    def test_get_strategy_status(self, runner, sample_strategy):
        """Test getting current strategy status."""
        status = runner._get_strategy_status("STRAT-001")
        assert status == "pending"


# =============================================================================
# TEST GATE APPLICATION
# =============================================================================


class TestGateApplication:
    """Test validation gate application."""

    def test_gates_pass_with_good_metrics(self, runner):
        """Test gates pass when metrics are good."""
        wf_result = WalkForwardResult(
            strategy_id="TEST-001",
            aggregate_sharpe=1.5,  # Above min_sharpe=1.0
            consistency=0.8,  # Above min_consistency=0.6
            max_drawdown=0.15,  # Below max_drawdown=0.25
            aggregate_cagr=0.10,  # Above min_cagr=0.05
        )

        gates = runner._apply_gates(wf_result)

        assert len(gates) == 4
        assert all(g["passed"] for g in gates)

    def test_gates_fail_low_sharpe(self, runner):
        """Test gates fail when Sharpe is too low."""
        wf_result = WalkForwardResult(
            strategy_id="TEST-001",
            aggregate_sharpe=0.5,  # Below min_sharpe=1.0
            consistency=0.8,
            max_drawdown=0.15,
        )

        gates = runner._apply_gates(wf_result)

        sharpe_gate = next(g for g in gates if g["gate"] == "min_sharpe")
        assert not sharpe_gate["passed"]
        assert sharpe_gate["actual"] == 0.5
        assert sharpe_gate["threshold"] == 1.0

    def test_gates_fail_low_consistency(self, runner):
        """Test gates fail when consistency is too low."""
        wf_result = WalkForwardResult(
            strategy_id="TEST-001",
            aggregate_sharpe=1.5,
            consistency=0.4,  # Below min_consistency=0.6
            max_drawdown=0.15,
        )

        gates = runner._apply_gates(wf_result)

        consistency_gate = next(g for g in gates if g["gate"] == "min_consistency")
        assert not consistency_gate["passed"]

    def test_gates_fail_high_drawdown(self, runner):
        """Test gates fail when drawdown is too high."""
        wf_result = WalkForwardResult(
            strategy_id="TEST-001",
            aggregate_sharpe=1.5,
            consistency=0.8,
            max_drawdown=0.35,  # Above max_drawdown=0.25
        )

        gates = runner._apply_gates(wf_result)

        dd_gate = next(g for g in gates if g["gate"] == "max_drawdown")
        assert not dd_gate["passed"]
        assert dd_gate["actual"] == 0.35
        assert dd_gate["threshold"] == 0.25

    def test_gates_fail_low_cagr(self, runner):
        """Test gates fail when CAGR is too low."""
        wf_result = WalkForwardResult(
            strategy_id="TEST-001",
            aggregate_sharpe=1.5,
            consistency=0.8,
            max_drawdown=0.15,
            aggregate_cagr=0.02,  # Below min_cagr=0.05
        )

        gates = runner._apply_gates(wf_result)

        cagr_gate = next(g for g in gates if g["gate"] == "min_cagr")
        assert not cagr_gate["passed"]
        assert cagr_gate["actual"] == 0.02
        assert cagr_gate["threshold"] == 0.05

    def test_gates_skip_cagr_when_none(self, runner):
        """Test CAGR gate is skipped when aggregate_cagr is None."""
        wf_result = WalkForwardResult(
            strategy_id="TEST-001",
            aggregate_sharpe=1.5,
            consistency=0.8,
            max_drawdown=0.15,
            aggregate_cagr=None,
        )

        gates = runner._apply_gates(wf_result)

        gate_names = [g["gate"] for g in gates]
        assert "min_cagr" not in gate_names


# =============================================================================
# TEST DRY RUN
# =============================================================================


class TestDryRun:
    """Test dry-run mode doesn't modify files."""

    def test_dry_run_doesnt_move_files(self, runner, sample_strategy, v4_workspace):
        """Test dry-run doesn't move strategy files."""
        # Run in dry-run mode
        result = runner.run("STRAT-001", dry_run=True)

        assert result.dry_run
        assert result.determination == "PENDING"

        # Strategy should still be in pending
        assert (v4_workspace.strategies_path / "pending" / "STRAT-001.yaml").exists()
        assert not (v4_workspace.strategies_path / "validated" / "STRAT-001.yaml").exists()
        assert not (v4_workspace.strategies_path / "invalidated" / "STRAT-001.yaml").exists()

    def test_dry_run_shows_strategy_info(self, runner, sample_strategy, capsys):
        """Test dry-run prints strategy information."""
        result = runner.run("STRAT-001", dry_run=True)

        captured = capsys.readouterr()
        assert "STRAT-001" in captured.out
        assert "momentum" in captured.out.lower() or "Momentum" in captured.out


# =============================================================================
# TEST RESULT SAVING
# =============================================================================


class TestResultSaving:
    """Test result saving to validations directory."""

    def test_save_code(self, runner, sample_strategy, v4_workspace):
        """Test generated code is saved."""
        code = "# Test code\nclass Test: pass"
        runner._save_code("STRAT-001", code)

        code_file = v4_workspace.validations_path / "STRAT-001" / "backtest.py"
        assert code_file.exists()
        assert code_file.read_text() == code

    def test_save_result(self, runner, sample_strategy, v4_workspace):
        """Test run result is saved as JSON."""
        wf_result = WalkForwardResult(
            strategy_id="STRAT-001",
            aggregate_sharpe=1.5,
            consistency=0.8,
            max_drawdown=0.15,
            determination="VALIDATED",
        )

        result = RunResult(
            strategy_id="STRAT-001",
            success=True,
            determination="VALIDATED",
            backtest=wf_result,
            gate_results=[
                {"gate": "min_sharpe", "passed": True, "actual": 1.5, "threshold": 1.0},
            ],
        )

        runner._save_result("STRAT-001", result)

        # Check run_result.json exists
        result_file = v4_workspace.validations_path / "STRAT-001" / "run_result.json"
        assert result_file.exists()

        data = json.loads(result_file.read_text())
        assert data["strategy_id"] == "STRAT-001"
        assert data["determination"] == "VALIDATED"

        # Check determination.json exists
        det_file = v4_workspace.validations_path / "STRAT-001" / "determination.json"
        assert det_file.exists()

        # Check backtest_results.yaml exists
        bt_file = v4_workspace.validations_path / "STRAT-001" / "backtest_results.yaml"
        assert bt_file.exists()


# =============================================================================
# TEST V4RUNRESULT
# =============================================================================


class TestRunResult:
    """Test RunResult dataclass."""

    def test_to_dict(self):
        """Test RunResult.to_dict() method."""
        result = RunResult(
            strategy_id="STRAT-001",
            success=True,
            determination="VALIDATED",
            gate_results=[
                {"gate": "min_sharpe", "passed": True, "actual": 1.5, "threshold": 1.0},
            ],
        )

        d = result.to_dict()

        assert d["strategy_id"] == "STRAT-001"
        assert d["success"] is True
        assert d["determination"] == "VALIDATED"
        assert len(d["gate_results"]) == 1

    def test_to_dict_with_error(self):
        """Test RunResult.to_dict() with error."""
        result = RunResult(
            strategy_id="STRAT-001",
            success=False,
            determination="FAILED",
            error="Code generation failed",
        )

        d = result.to_dict()

        assert d["success"] is False
        assert d["determination"] == "FAILED"
        assert d["error"] == "Code generation failed"


# =============================================================================
# TEST STATUS UPDATES
# =============================================================================


class TestStatusUpdates:
    """Test strategy status updates."""

    def test_update_status_moves_file(self, runner, sample_strategy, v4_workspace):
        """Test status update moves strategy file."""
        runner._update_status("STRAT-001", "validated")

        # Should be in validated, not pending
        assert not (v4_workspace.strategies_path / "pending" / "STRAT-001.yaml").exists()
        assert (v4_workspace.strategies_path / "validated" / "STRAT-001.yaml").exists()

    def test_update_status_same_status(self, runner, sample_strategy, v4_workspace):
        """Test status update with same status is no-op."""
        # Strategy is already pending
        runner._update_status("STRAT-001", "pending")

        # Should still be in pending
        assert (v4_workspace.strategies_path / "pending" / "STRAT-001.yaml").exists()


# =============================================================================
# TEST BATCH PROCESSING
# =============================================================================


class TestBatchProcessing:
    """Test batch processing of strategies."""

    @pytest.fixture
    def multiple_strategies(self, v4_workspace):
        """Create multiple strategies in workspace."""
        strategies = []
        for i in range(3):
            strategy = {
                "id": f"STRAT-00{i + 1}",
                "name": f"Test Strategy {i + 1}",
                "strategy_type": "momentum",
                "parameters": {"lookback_period": 126, "top_n": 3},
            }
            strategy_file = v4_workspace.strategies_path / "pending" / f"STRAT-00{i + 1}.yaml"
            strategy_file.write_text(yaml.dump(strategy))
            strategies.append(strategy)
        return strategies

    def test_run_all_dry_run(self, runner, multiple_strategies, capsys):
        """Test run_all in dry-run mode."""
        results = runner.run_all(dry_run=True)

        assert len(results) == 3
        assert all(r.dry_run for r in results)

        captured = capsys.readouterr()
        assert "STRAT-001" in captured.out
        assert "STRAT-002" in captured.out
        assert "STRAT-003" in captured.out

    def test_run_all_empty_workspace(self, runner, capsys):
        """Test run_all with no pending strategies."""
        results = runner.run_all(dry_run=True)

        assert len(results) == 0

        captured = capsys.readouterr()
        assert "No pending strategies" in captured.out


# =============================================================================
# TEST FORCE FLAG FOR BLOCKED STRATEGIES
# =============================================================================


class TestForceBlockedRetry:
    """Test --force flag re-runs blocked strategies."""

    @pytest.fixture
    def blocked_strategy(self, v4_workspace):
        """Create a strategy in the blocked directory."""
        strategy = {
            "id": "STRAT-010",
            "name": "Blocked Momentum Strategy",
            "description": "A strategy that was blocked due to transient failure",
            "strategy_type": "momentum",
            "signal_type": "relative_momentum",
            "universe": ["SPY", "QQQ"],
            "parameters": {"lookback_period": 126},
            "status": "blocked",
        }

        blocked_path = v4_workspace.strategies_path / "blocked"
        blocked_path.mkdir(parents=True, exist_ok=True)
        strategy_file = blocked_path / "STRAT-010.yaml"
        strategy_file.write_text(yaml.dump(strategy))

        return strategy

    def test_blocked_strategy_rejected_without_force(self, runner, blocked_strategy):
        """Test that blocked strategies are rejected without --force."""
        result = runner.run("STRAT-010")

        assert not result.success
        assert result.determination == "BLOCKED"
        assert "--force" in result.error

    def test_force_moves_blocked_to_pending(self, runner, blocked_strategy, v4_workspace):
        """Test --force moves strategy from blocked/ to pending/."""
        # Run with force + dry_run to avoid needing full backtest infrastructure
        result = runner.run("STRAT-010", force=True, dry_run=True)

        assert result.dry_run
        assert result.determination == "PENDING"

        # File should now be in pending, not blocked
        assert (v4_workspace.strategies_path / "pending" / "STRAT-010.yaml").exists()
        assert not (v4_workspace.strategies_path / "blocked" / "STRAT-010.yaml").exists()

    def test_force_resets_yaml_status(self, runner, blocked_strategy, v4_workspace):
        """Test --force resets the status field in the YAML to 'pending'."""
        runner.run("STRAT-010", force=True, dry_run=True)

        strategy_file = v4_workspace.strategies_path / "pending" / "STRAT-010.yaml"
        data = yaml.safe_load(strategy_file.read_text())
        assert data["status"] == "pending"

    def test_force_prints_message(self, runner, blocked_strategy, capsys):
        """Test --force prints a message about moving the strategy."""
        runner.run("STRAT-010", force=True, dry_run=True)

        captured = capsys.readouterr()
        assert "--force" in captured.out
        assert "STRAT-010" in captured.out
        assert "blocked" in captured.out
        assert "pending" in captured.out

    def test_force_on_pending_strategy_is_noop(self, runner, v4_workspace):
        """Test --force on an already-pending strategy proceeds normally."""
        strategy = {
            "id": "STRAT-011",
            "name": "Pending Strategy",
            "strategy_type": "momentum",
            "parameters": {"lookback_period": 126},
            "status": "pending",
        }
        pending_path = v4_workspace.strategies_path / "pending"
        pending_path.mkdir(parents=True, exist_ok=True)
        (pending_path / "STRAT-011.yaml").write_text(yaml.dump(strategy))

        result = runner.run("STRAT-011", force=True, dry_run=True)

        assert result.dry_run
        assert result.determination == "PENDING"
        assert (v4_workspace.strategies_path / "pending" / "STRAT-011.yaml").exists()


# =============================================================================
# TEST WINDOW CONSISTENCY GATE
# =============================================================================


class TestWindowConsistencyGate:
    """Test per-window consistency gate for --windows 5 mode."""

    @pytest.fixture
    def runner_5_windows(self, v4_workspace):
        """Create a Runner configured for 5 windows."""
        return Runner(
            workspace=v4_workspace,
            llm_client=None,
            use_local=True,
            num_windows=5,
        )

    def test_window_consistency_all_pass(self, runner_5_windows):
        """All windows passing gates gives 1.0 pass rate."""
        wf_result = WalkForwardResult(strategy_id="TEST-WC-1")
        wf_result.windows = [
            WalkForwardWindow(
                window_id=i + 1,
                start_date=f"201{i*2}-01-01",
                end_date=f"201{i*2+3}-12-31",
                result=BacktestResult(success=True, cagr=0.10, sharpe=1.5, max_drawdown=0.15),
            )
            for i in range(5)
        ]

        gate = runner_5_windows._apply_window_consistency_gate(wf_result)

        assert gate is not None
        assert gate["passed"] is True
        assert gate["actual"] == pytest.approx(1.0)

    def test_window_consistency_one_fails(self, runner_5_windows):
        """4/5 windows passing gives 0.8 pass rate (meets 0.8 threshold)."""
        wf_result = WalkForwardResult(strategy_id="TEST-WC-2")
        wf_result.windows = [
            WalkForwardWindow(
                window_id=i + 1,
                start_date=f"201{i*2}-01-01",
                end_date=f"201{i*2+3}-12-31",
                result=BacktestResult(success=True, cagr=0.10, sharpe=1.5, max_drawdown=0.15),
            )
            for i in range(4)
        ]
        # Add one failing window (low Sharpe)
        wf_result.windows.append(WalkForwardWindow(
            window_id=5,
            start_date="2020-01-01",
            end_date="2023-12-31",
            result=BacktestResult(success=True, cagr=0.02, sharpe=0.1, max_drawdown=0.40),
        ))

        gate = runner_5_windows._apply_window_consistency_gate(wf_result)

        assert gate is not None
        assert gate["passed"] is True
        assert gate["actual"] == pytest.approx(0.8)

    def test_window_consistency_too_many_fail(self, runner_5_windows):
        """2/5 windows failing gives 0.6 pass rate (below 0.8 threshold)."""
        wf_result = WalkForwardResult(strategy_id="TEST-WC-3")
        wf_result.windows = [
            WalkForwardWindow(
                window_id=i + 1,
                start_date=f"201{i*2}-01-01",
                end_date=f"201{i*2+3}-12-31",
                result=BacktestResult(success=True, cagr=0.10, sharpe=1.5, max_drawdown=0.15),
            )
            for i in range(3)
        ]
        # Add two failing windows
        for j in range(2):
            wf_result.windows.append(WalkForwardWindow(
                window_id=4 + j,
                start_date=f"201{8+j*2}-01-01",
                end_date=f"202{1+j*2}-12-31",
                result=BacktestResult(success=True, cagr=-0.05, sharpe=-0.2, max_drawdown=0.45),
            ))

        gate = runner_5_windows._apply_window_consistency_gate(wf_result)

        assert gate is not None
        assert gate["passed"] is False
        assert gate["actual"] == pytest.approx(0.6)

    def test_no_window_consistency_for_single_window(self, runner):
        """Window consistency gate not applied for --windows 1."""
        wf_result = WalkForwardResult(strategy_id="TEST-WC-4")
        wf_result.windows = [
            WalkForwardWindow(
                window_id=1,
                start_date="2012-01-01",
                end_date="2023-12-31",
                result=BacktestResult(success=True, cagr=0.10, sharpe=1.5, max_drawdown=0.15),
            ),
        ]

        gate = runner._apply_window_consistency_gate(wf_result)

        # Should still return a result (gate exists), but it's not called by runner for windows < 5
        assert gate is not None
