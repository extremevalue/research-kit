"""Tests for V4 status command."""

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
def workspace_with_content(v4_workspace):
    """Create workspace with strategies and inbox files."""
    # Create strategies in various states
    strategies = [
        {"id": "STRAT-001", "name": "Strategy One", "created": "2024-01-15T10:00:00Z"},
        {"id": "STRAT-002", "name": "Strategy Two", "created": "2024-01-16T10:00:00Z"},
        {"id": "STRAT-003", "name": "Strategy Three", "created": "2024-01-14T10:00:00Z"},
    ]

    # Pending strategies
    for s in strategies[:2]:
        filepath = v4_workspace.strategies_path / "pending" / f"{s['id']}.yaml"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            yaml.dump(s, f)

    # Validated strategy
    filepath = v4_workspace.strategies_path / "validated" / f"{strategies[2]['id']}.yaml"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        yaml.dump(strategies[2], f)

    # Add inbox files
    (v4_workspace.inbox_path / "doc1.txt").write_text("Strategy document 1")
    (v4_workspace.inbox_path / "doc2.txt").write_text("Strategy document 2")

    return v4_workspace


# =============================================================================
# TESTS: Basic output
# =============================================================================


class TestV4StatusBasic:
    """Tests for basic status output."""

    def test_status_empty_workspace(self, v4_workspace, capsys):
        """Shows status for empty workspace."""
        from research_system.cli.main import cmd_status

        args = SimpleNamespace(
            v4_workspace=str(v4_workspace.path)
        )

        result = cmd_status(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "Research-Kit Workspace Status" in captured.out
        assert str(v4_workspace.path) in captured.out
        assert "No strategies yet" in captured.out

    def test_status_with_content(self, workspace_with_content, capsys):
        """Shows status with strategies and inbox files."""
        from research_system.cli.main import cmd_status

        args = SimpleNamespace(
            v4_workspace=str(workspace_with_content.path)
        )

        result = cmd_status(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "pending" in captured.out
        assert "validated" in captured.out
        assert "2" in captured.out  # 2 pending
        assert "1" in captured.out  # 1 validated

    def test_status_shows_workspace_path(self, v4_workspace, capsys):
        """Shows workspace path in output."""
        from research_system.cli.main import cmd_status

        args = SimpleNamespace(
            v4_workspace=str(v4_workspace.path)
        )

        cmd_status(args)

        captured = capsys.readouterr()
        assert str(v4_workspace.path) in captured.out


# =============================================================================
# TESTS: Strategy counts
# =============================================================================


class TestV4StatusCounts:
    """Tests for strategy counts."""

    def test_counts_by_status(self, workspace_with_content, capsys):
        """Shows correct counts by status."""
        from research_system.cli.main import cmd_status

        args = SimpleNamespace(
            v4_workspace=str(workspace_with_content.path)
        )

        cmd_status(args)

        captured = capsys.readouterr()
        # 2 pending, 1 validated
        lines = captured.out.split('\n')
        pending_line = [l for l in lines if 'pending' in l.lower()]
        assert any('2' in l for l in pending_line)

    def test_shows_total(self, workspace_with_content, capsys):
        """Shows total strategy count."""
        from research_system.cli.main import cmd_status

        args = SimpleNamespace(
            v4_workspace=str(workspace_with_content.path)
        )

        cmd_status(args)

        captured = capsys.readouterr()
        assert "Total" in captured.out
        assert "3" in captured.out  # 3 total strategies


# =============================================================================
# TESTS: Inbox
# =============================================================================


class TestV4StatusInbox:
    """Tests for inbox status."""

    def test_empty_inbox_message(self, v4_workspace, capsys):
        """Shows empty inbox message."""
        from research_system.cli.main import cmd_status

        args = SimpleNamespace(
            v4_workspace=str(v4_workspace.path)
        )

        cmd_status(args)

        captured = capsys.readouterr()
        assert "Inbox is empty" in captured.out

    def test_inbox_file_count(self, workspace_with_content, capsys):
        """Shows inbox file count."""
        from research_system.cli.main import cmd_status

        args = SimpleNamespace(
            v4_workspace=str(workspace_with_content.path)
        )

        cmd_status(args)

        captured = capsys.readouterr()
        assert "2 file(s) ready to ingest" in captured.out


# =============================================================================
# TESTS: ID counters
# =============================================================================


class TestV4StatusCounters:
    """Tests for ID counter display."""

    def test_shows_next_ids(self, v4_workspace, capsys):
        """Shows next ID numbers."""
        from research_system.cli.main import cmd_status

        args = SimpleNamespace(
            v4_workspace=str(v4_workspace.path)
        )

        cmd_status(args)

        captured = capsys.readouterr()
        assert "Next strategy: STRAT-001" in captured.out
        assert "Next idea:" in captured.out

    def test_counter_increments(self, v4_workspace, capsys):
        """Counter increments are reflected."""
        # Use some IDs
        v4_workspace.next_strategy_id()
        v4_workspace.next_strategy_id()

        from research_system.cli.main import cmd_status

        args = SimpleNamespace(
            v4_workspace=str(v4_workspace.path)
        )

        cmd_status(args)

        captured = capsys.readouterr()
        assert "STRAT-003" in captured.out  # Next would be 003


# =============================================================================
# TESTS: Recent strategies
# =============================================================================


class TestV4StatusRecent:
    """Tests for recent strategies section."""

    def test_no_recent_when_empty(self, v4_workspace, capsys):
        """No recent section when no strategies."""
        from research_system.cli.main import cmd_status

        args = SimpleNamespace(
            v4_workspace=str(v4_workspace.path)
        )

        cmd_status(args)

        captured = capsys.readouterr()
        assert "STRAT-" not in captured.out or "Recent" not in captured.out

    def test_shows_recent_strategies(self, workspace_with_content, capsys):
        """Shows recent strategies."""
        from research_system.cli.main import cmd_status

        args = SimpleNamespace(
            v4_workspace=str(workspace_with_content.path)
        )

        cmd_status(args)

        captured = capsys.readouterr()
        assert "Recent Strategies" in captured.out
        assert "STRAT-001" in captured.out or "STRAT-002" in captured.out


# =============================================================================
# TESTS: Actions
# =============================================================================


class TestV4StatusActions:
    """Tests for suggested actions."""

    def test_suggests_ingest_when_inbox_has_files(self, workspace_with_content, capsys):
        """Suggests running ingest when inbox has files."""
        from research_system.cli.main import cmd_status

        args = SimpleNamespace(
            v4_workspace=str(workspace_with_content.path)
        )

        cmd_status(args)

        captured = capsys.readouterr()
        assert "ingest" in captured.out

    def test_suggests_adding_to_inbox_when_empty(self, v4_workspace, capsys):
        """Suggests adding docs when empty workspace."""
        from research_system.cli.main import cmd_status

        args = SimpleNamespace(
            v4_workspace=str(v4_workspace.path)
        )

        cmd_status(args)

        captured = capsys.readouterr()
        assert "inbox" in captured.out.lower()


# =============================================================================
# TESTS: Error handling
# =============================================================================


class TestV4StatusErrors:
    """Tests for error handling."""

    def test_uninitialized_workspace(self, tmp_path, capsys):
        """Shows error for uninitialized workspace."""
        from research_system.cli.main import cmd_status

        args = SimpleNamespace(
            v4_workspace=str(tmp_path / "nonexistent")
        )

        result = cmd_status(args)
        assert result == 1

        captured = capsys.readouterr()
        assert "Error" in captured.out
        assert "init --v4" in captured.out
