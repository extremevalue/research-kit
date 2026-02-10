"""Tests for V4 show command."""

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def v4_workspace(tmp_path):
    """Create an initialized V4 workspace."""
    from research_system.core.v4.workspace import Workspace

    ws = Workspace(tmp_path)
    ws.init()
    return ws


@pytest.fixture
def workspace_with_strategy(v4_workspace):
    """Create workspace with a sample strategy."""
    strategy = {
        "id": "STRAT-001",
        "name": "Moving Average Crossover",
        "created": "2024-01-15T10:30:00Z",
        "source": {
            "type": "podcast",
            "author": "John Doe",
            "url": "https://example.com/episode",
            "track_record": "verified_fund_manager",
        },
        "hypothesis": {
            "thesis": "Trend following using EMA crossovers works in equity markets",
            "type": "trend_following",
            "testable_prediction": "Long when 20 EMA > 50 EMA",
            "expected_sharpe": {"min": 0.5, "max": 1.5},
        },
        "edge": {
            "category": "behavioral",
            "why_exists": "Investors slow to react to trend changes",
            "why_persists": "Hard to arbitrage away behavioral biases",
        },
        "universe": {
            "type": "static",
            "symbols": ["SPY", "QQQ", "IWM"],
        },
        "entry": {
            "type": "technical",
            "signals": [
                {"name": "ema_cross", "condition": "ema_20 > ema_50"},
                {"name": "volume_confirm", "condition": "volume > sma_20_volume"},
            ],
        },
        "exit": {
            "paths": [
                {"name": "trend_reversal", "condition": "ema_20 < ema_50"},
                {"name": "stop_loss", "condition": "price < entry - 2%"},
            ],
        },
        "data_requirements": {
            "primary": ["spy_prices", "qqq_prices", "iwm_prices"],
            "derived": ["ema_20", "ema_50"],
        },
        "tags": {
            "custom": ["trend", "momentum", "equity"],
        },
    }

    filepath = v4_workspace.strategies_path / "pending" / "STRAT-001.yaml"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        yaml.dump(strategy, f)

    return v4_workspace


# =============================================================================
# TESTS: Text format output
# =============================================================================


class TestV4ShowTextFormat:
    """Tests for text format output."""

    def test_show_strategy_basic(self, workspace_with_strategy, capsys):
        """Shows basic strategy information."""
        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-001",
            v4_workspace=str(workspace_with_strategy.path),
            format="text"
        )

        result = cmd_show(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "STRAT-001" in captured.out
        assert "Moving Average Crossover" in captured.out
        assert "pending" in captured.out

    def test_show_strategy_source(self, workspace_with_strategy, capsys):
        """Shows source information."""
        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-001",
            v4_workspace=str(workspace_with_strategy.path),
            format="text"
        )

        cmd_show(args)

        captured = capsys.readouterr()
        assert "Source" in captured.out
        assert "podcast" in captured.out
        assert "John Doe" in captured.out

    def test_show_strategy_hypothesis(self, workspace_with_strategy, capsys):
        """Shows hypothesis section."""
        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-001",
            v4_workspace=str(workspace_with_strategy.path),
            format="text"
        )

        cmd_show(args)

        captured = capsys.readouterr()
        assert "Hypothesis" in captured.out
        assert "Trend following" in captured.out
        assert "EMA crossovers" in captured.out

    def test_show_strategy_edge(self, workspace_with_strategy, capsys):
        """Shows edge section."""
        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-001",
            v4_workspace=str(workspace_with_strategy.path),
            format="text"
        )

        cmd_show(args)

        captured = capsys.readouterr()
        assert "Edge" in captured.out
        assert "behavioral" in captured.out

    def test_show_strategy_universe(self, workspace_with_strategy, capsys):
        """Shows universe section."""
        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-001",
            v4_workspace=str(workspace_with_strategy.path),
            format="text"
        )

        cmd_show(args)

        captured = capsys.readouterr()
        assert "Universe" in captured.out
        assert "SPY" in captured.out

    def test_show_strategy_entry(self, workspace_with_strategy, capsys):
        """Shows entry section."""
        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-001",
            v4_workspace=str(workspace_with_strategy.path),
            format="text"
        )

        cmd_show(args)

        captured = capsys.readouterr()
        assert "Entry" in captured.out
        assert "Signal" in captured.out


# =============================================================================
# TESTS: YAML format output
# =============================================================================


class TestV4ShowYamlFormat:
    """Tests for YAML format output."""

    def test_yaml_output_valid(self, workspace_with_strategy, capsys):
        """YAML output is valid YAML."""
        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-001",
            v4_workspace=str(workspace_with_strategy.path),
            format="yaml"
        )

        result = cmd_show(args)
        assert result == 0

        captured = capsys.readouterr()
        data = yaml.safe_load(captured.out)
        assert data["id"] == "STRAT-001"
        assert data["name"] == "Moving Average Crossover"

    def test_yaml_no_internal_fields(self, workspace_with_strategy, capsys):
        """YAML output doesn't include internal fields."""
        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-001",
            v4_workspace=str(workspace_with_strategy.path),
            format="yaml"
        )

        cmd_show(args)

        captured = capsys.readouterr()
        data = yaml.safe_load(captured.out)
        assert "_file" not in data
        assert "_status" not in data


# =============================================================================
# TESTS: JSON format output
# =============================================================================


class TestV4ShowJsonFormat:
    """Tests for JSON format output."""

    def test_json_output_valid(self, workspace_with_strategy, capsys):
        """JSON output is valid JSON."""
        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-001",
            v4_workspace=str(workspace_with_strategy.path),
            format="json"
        )

        result = cmd_show(args)
        assert result == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["id"] == "STRAT-001"
        assert data["name"] == "Moving Average Crossover"

    def test_json_no_internal_fields(self, workspace_with_strategy, capsys):
        """JSON output doesn't include internal fields."""
        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-001",
            v4_workspace=str(workspace_with_strategy.path),
            format="json"
        )

        cmd_show(args)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "_file" not in data
        assert "_status" not in data


# =============================================================================
# TESTS: Error handling
# =============================================================================


class TestV4ShowErrors:
    """Tests for error handling."""

    def test_strategy_not_found(self, v4_workspace, capsys):
        """Shows error for non-existent strategy."""
        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-999",
            v4_workspace=str(v4_workspace.path),
            format="text"
        )

        result = cmd_show(args)
        assert result == 1

        captured = capsys.readouterr()
        assert "not found" in captured.out
        assert "STRAT-999" in captured.out

    def test_uninitialized_workspace(self, tmp_path, capsys):
        """Shows error for uninitialized workspace."""
        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-001",
            v4_workspace=str(tmp_path / "nonexistent"),
            format="text"
        )

        result = cmd_show(args)
        assert result == 1

        captured = capsys.readouterr()
        assert "Error" in captured.out
        assert "init --v4" in captured.out


# =============================================================================
# TESTS: Edge cases
# =============================================================================


class TestV4ShowEdgeCases:
    """Edge case tests."""

    def test_minimal_strategy(self, v4_workspace, capsys):
        """Shows minimal strategy with only required fields."""
        strategy = {
            "id": "STRAT-002",
            "name": "Minimal Strategy",
        }
        filepath = v4_workspace.strategies_path / "pending" / "STRAT-002.yaml"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            yaml.dump(strategy, f)

        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-002",
            v4_workspace=str(v4_workspace.path),
            format="text"
        )

        result = cmd_show(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "STRAT-002" in captured.out
        assert "Minimal Strategy" in captured.out

    def test_strategy_in_validated(self, v4_workspace, capsys):
        """Can show strategy from validated directory."""
        strategy = {
            "id": "STRAT-003",
            "name": "Validated Strategy",
        }
        filepath = v4_workspace.strategies_path / "validated" / "STRAT-003.yaml"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            yaml.dump(strategy, f)

        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-003",
            v4_workspace=str(v4_workspace.path),
            format="text"
        )

        result = cmd_show(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "STRAT-003" in captured.out
        assert "validated" in captured.out

    def test_strategy_with_many_symbols(self, v4_workspace, capsys):
        """Truncates display when many symbols."""
        strategy = {
            "id": "STRAT-004",
            "name": "Many Symbols Strategy",
            "universe": {
                "type": "static",
                "symbols": [f"SYM{i}" for i in range(20)],
            },
        }
        filepath = v4_workspace.strategies_path / "pending" / "STRAT-004.yaml"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            yaml.dump(strategy, f)

        from research_system.cli.main import cmd_show

        args = SimpleNamespace(
            strategy_id="STRAT-004",
            v4_workspace=str(v4_workspace.path),
            format="text"
        )

        result = cmd_show(args)
        assert result == 0

        captured = capsys.readouterr()
        # Should show first few and indicate more
        assert "SYM0" in captured.out
        assert "more" in captured.out
