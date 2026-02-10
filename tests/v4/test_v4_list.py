"""Tests for V4 list command and workspace listing functionality."""

import json
from datetime import datetime, timezone
from pathlib import Path

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
def workspace_with_strategies(v4_workspace):
    """Create workspace with sample strategies."""
    strategies = [
        {
            "id": "STRAT-001",
            "name": "Moving Average Crossover",
            "status": "pending",
            "created": "2024-01-15T10:30:00Z",
            "tags": {"custom": ["momentum", "trend"]},
        },
        {
            "id": "STRAT-002",
            "name": "RSI Mean Reversion",
            "status": "pending",
            "created": "2024-01-16T14:00:00Z",
            "tags": {"custom": ["mean_reversion"]},
        },
        {
            "id": "STRAT-003",
            "name": "Volatility Breakout",
            "status": "validated",
            "created": "2024-01-10T09:00:00Z",
            "tags": {"custom": ["volatility", "breakout"]},
        },
        {
            "id": "STRAT-004",
            "name": "Gap Trading Strategy",
            "status": "invalidated",
            "created": "2024-01-12T11:00:00Z",
            "tags": {"custom": ["event_driven"]},
        },
        {
            "id": "STRAT-005",
            "name": "Data Pending Strategy",
            "status": "blocked",
            "created": "2024-01-14T08:00:00Z",
            "tags": {"custom": ["pending_data"]},
        },
    ]

    for strat in strategies:
        status = strat.pop("status")
        filepath = v4_workspace.strategies_path / status / f"{strat['id']}.yaml"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            yaml.dump(strat, f)

    return v4_workspace


# =============================================================================
# TESTS: list_strategies()
# =============================================================================


class TestListStrategies:
    """Tests for Workspace.list_strategies()."""

    def test_list_empty_workspace(self, v4_workspace):
        """Empty workspace returns empty list."""
        result = v4_workspace.list_strategies()
        assert result == []

    def test_list_all_strategies(self, workspace_with_strategies):
        """Lists all strategies across all statuses."""
        result = workspace_with_strategies.list_strategies()
        assert len(result) == 5
        ids = [s["id"] for s in result]
        assert "STRAT-001" in ids
        assert "STRAT-002" in ids
        assert "STRAT-003" in ids
        assert "STRAT-004" in ids
        assert "STRAT-005" in ids

    def test_list_sorted_by_date(self, workspace_with_strategies):
        """Strategies sorted by created date, newest first."""
        result = workspace_with_strategies.list_strategies()
        # STRAT-002 is newest (Jan 16), should be first
        assert result[0]["id"] == "STRAT-002"
        # STRAT-003 is oldest (Jan 10), should be last
        assert result[-1]["id"] == "STRAT-003"

    def test_filter_by_status(self, workspace_with_strategies):
        """Filter by specific status."""
        pending = workspace_with_strategies.list_strategies(status="pending")
        assert len(pending) == 2
        assert all(s["status"] == "pending" for s in pending)

        validated = workspace_with_strategies.list_strategies(status="validated")
        assert len(validated) == 1
        assert validated[0]["id"] == "STRAT-003"

    def test_filter_by_tags(self, workspace_with_strategies):
        """Filter by tags."""
        momentum = workspace_with_strategies.list_strategies(tags=["momentum"])
        assert len(momentum) == 1
        assert momentum[0]["id"] == "STRAT-001"

    def test_filter_by_multiple_tags(self, workspace_with_strategies):
        """Filter requires all specified tags."""
        # Must have both 'momentum' AND 'trend'
        result = workspace_with_strategies.list_strategies(tags=["momentum", "trend"])
        assert len(result) == 1
        assert result[0]["id"] == "STRAT-001"

        # No strategy has both 'momentum' and 'volatility'
        result = workspace_with_strategies.list_strategies(tags=["momentum", "volatility"])
        assert len(result) == 0

    def test_filter_by_status_and_tags(self, workspace_with_strategies):
        """Combine status and tag filters."""
        result = workspace_with_strategies.list_strategies(
            status="pending",
            tags=["mean_reversion"]
        )
        assert len(result) == 1
        assert result[0]["id"] == "STRAT-002"

    def test_returns_strategy_metadata(self, workspace_with_strategies):
        """Each result has required metadata fields."""
        result = workspace_with_strategies.list_strategies()
        for s in result:
            assert "id" in s
            assert "name" in s
            assert "status" in s
            assert "created" in s
            assert "tags" in s
            assert "file" in s


class TestGetStrategy:
    """Tests for Workspace.get_strategy()."""

    def test_get_existing_strategy(self, workspace_with_strategies):
        """Get strategy by ID returns full data."""
        result = workspace_with_strategies.get_strategy("STRAT-001")
        assert result is not None
        assert result["id"] == "STRAT-001"
        assert result["name"] == "Moving Average Crossover"
        assert result["_status"] == "pending"

    def test_get_nonexistent_strategy(self, workspace_with_strategies):
        """Get non-existent strategy returns None."""
        result = workspace_with_strategies.get_strategy("STRAT-999")
        assert result is None

    def test_get_strategy_from_any_status(self, workspace_with_strategies):
        """Can get strategy regardless of status."""
        validated = workspace_with_strategies.get_strategy("STRAT-003")
        assert validated is not None
        assert validated["_status"] == "validated"

        invalidated = workspace_with_strategies.get_strategy("STRAT-004")
        assert invalidated is not None
        assert invalidated["_status"] == "invalidated"


# =============================================================================
# TESTS: CLI command
# =============================================================================


class TestV4ListCLI:
    """Tests for the v4-list CLI command."""

    def test_list_empty_workspace(self, v4_workspace, capsys):
        """Empty workspace shows appropriate message."""
        from research_system.cli.main import cmd_list
        from types import SimpleNamespace

        args = SimpleNamespace(
            v4_workspace=str(v4_workspace.path),
            status=None,
            tags=None,
            format="table"
        )

        result = cmd_list(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "No strategies" in captured.out

    def test_list_table_format(self, workspace_with_strategies, capsys):
        """Table format shows columns and summary."""
        from research_system.cli.main import cmd_list
        from types import SimpleNamespace

        args = SimpleNamespace(
            v4_workspace=str(workspace_with_strategies.path),
            status=None,
            tags=None,
            format="table"
        )

        result = cmd_list(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "ID" in captured.out
        assert "Name" in captured.out
        assert "Status" in captured.out
        assert "Created" in captured.out
        assert "STRAT-001" in captured.out
        assert "Total: 5 strategies" in captured.out

    def test_list_json_format(self, workspace_with_strategies, capsys):
        """JSON format outputs valid JSON."""
        from research_system.cli.main import cmd_list
        from types import SimpleNamespace

        args = SimpleNamespace(
            v4_workspace=str(workspace_with_strategies.path),
            status=None,
            tags=None,
            format="json"
        )

        result = cmd_list(args)
        assert result == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 5

    def test_list_filter_by_status(self, workspace_with_strategies, capsys):
        """Status filter works in CLI."""
        from research_system.cli.main import cmd_list
        from types import SimpleNamespace

        args = SimpleNamespace(
            v4_workspace=str(workspace_with_strategies.path),
            status="validated",
            tags=None,
            format="table"
        )

        result = cmd_list(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "STRAT-003" in captured.out
        assert "STRAT-001" not in captured.out
        assert "Total: 1 strategies" in captured.out

    def test_list_filter_by_tags(self, workspace_with_strategies, capsys):
        """Tag filter works in CLI."""
        from research_system.cli.main import cmd_list
        from types import SimpleNamespace

        args = SimpleNamespace(
            v4_workspace=str(workspace_with_strategies.path),
            status=None,
            tags="volatility",
            format="table"
        )

        result = cmd_list(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "STRAT-003" in captured.out
        assert "Total: 1 strategies" in captured.out


class TestV4ListErrorHandling:
    """Tests for error handling in v4-list."""

    def test_uninitialized_workspace(self, tmp_path, capsys):
        """Uninitialized workspace shows error."""
        from research_system.cli.main import cmd_list
        from types import SimpleNamespace

        args = SimpleNamespace(
            v4_workspace=str(tmp_path / "nonexistent"),
            status=None,
            tags=None,
            format="table"
        )

        result = cmd_list(args)
        assert result == 1

        captured = capsys.readouterr()
        assert "Error" in captured.out
        assert "init --v4" in captured.out

    def test_malformed_yaml_graceful(self, v4_workspace, capsys):
        """Malformed YAML files don't crash the listing."""
        # Create a malformed YAML file
        malformed = v4_workspace.strategies_path / "pending" / "STRAT-BAD.yaml"
        malformed.parent.mkdir(parents=True, exist_ok=True)
        malformed.write_text("this: is: invalid: yaml: [")

        from research_system.cli.main import cmd_list
        from types import SimpleNamespace

        args = SimpleNamespace(
            v4_workspace=str(v4_workspace.path),
            status=None,
            tags=None,
            format="table"
        )

        result = cmd_list(args)
        assert result == 0  # Should not crash

        captured = capsys.readouterr()
        assert "STRAT-BAD" in captured.out


# =============================================================================
# TESTS: Edge cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests."""

    def test_tags_as_list(self, v4_workspace):
        """Strategies with tags as list (not dict) work."""
        strat = {
            "id": "STRAT-010",
            "name": "Simple Tags Strategy",
            "created": "2024-01-20T10:00:00Z",
            "tags": ["simple", "test"],  # List instead of dict
        }
        filepath = v4_workspace.strategies_path / "pending" / "STRAT-010.yaml"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            yaml.dump(strat, f)

        result = v4_workspace.list_strategies()
        assert len(result) == 1
        assert result[0]["tags"] == ["simple", "test"]

    def test_missing_created_field(self, v4_workspace):
        """Strategies without created field still list."""
        strat = {
            "id": "STRAT-011",
            "name": "No Date Strategy",
        }
        filepath = v4_workspace.strategies_path / "pending" / "STRAT-011.yaml"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            yaml.dump(strat, f)

        result = v4_workspace.list_strategies()
        assert len(result) == 1
        assert result[0]["created"] is None

    def test_very_long_name_truncated(self, v4_workspace, capsys):
        """Very long names are truncated in table output."""
        strat = {
            "id": "STRAT-012",
            "name": "A" * 100,  # 100 character name
            "created": "2024-01-20T10:00:00Z",
        }
        filepath = v4_workspace.strategies_path / "pending" / "STRAT-012.yaml"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            yaml.dump(strat, f)

        from research_system.cli.main import cmd_list
        from types import SimpleNamespace

        args = SimpleNamespace(
            v4_workspace=str(v4_workspace.path),
            status=None,
            tags=None,
            format="table"
        )

        cmd_list(args)

        captured = capsys.readouterr()
        # Name should be truncated with ..
        assert ".." in captured.out
