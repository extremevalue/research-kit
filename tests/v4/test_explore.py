"""Tests for explore commands (research effort management).

Tests:
1. explore-init creates directory + files with correct content
2. explore-init errors on existing directory
3. explore-init slugifies title correctly
4. explore-list finds efforts and formats output
5. explore-list --index writes INDEX.md
6. explore-update modifies research.yaml correctly
7. explore-update appends strategy without duplicates
8. explore-update errors on missing topic
"""

import json
from pathlib import Path

import pytest
import yaml

from research_system.core.v4 import Workspace


# ============================================================================
# Helper: create initialized workspace
# ============================================================================


@pytest.fixture
def workspace(tmp_path):
    """Create an initialized workspace for testing."""
    ws = Workspace(tmp_path)
    ws.init()
    return ws


# ============================================================================
# Slugify
# ============================================================================


class TestSlugify:
    """Test the _slugify helper."""

    def test_basic_title(self):
        from research_system.cli.main import _slugify
        assert _slugify("Regime-Conditioned Options") == "regime-conditioned-options"

    def test_spaces_to_hyphens(self):
        from research_system.cli.main import _slugify
        assert _slugify("FX Carry Signal") == "fx-carry-signal"

    def test_special_characters(self):
        from research_system.cli.main import _slugify
        assert _slugify("Hello   World!!!") == "hello-world"

    def test_leading_trailing_whitespace(self):
        from research_system.cli.main import _slugify
        assert _slugify("  some title  ") == "some-title"

    def test_already_slug(self):
        from research_system.cli.main import _slugify
        assert _slugify("already-a-slug") == "already-a-slug"

    def test_numbers_preserved(self):
        from research_system.cli.main import _slugify
        assert _slugify("Phase 2 Analysis") == "phase-2-analysis"

    def test_empty_string(self):
        from research_system.cli.main import _slugify
        assert _slugify("") == ""

    def test_only_special_chars(self):
        from research_system.cli.main import _slugify
        assert _slugify("!!!") == ""


# ============================================================================
# explore-init
# ============================================================================


class TestExploreInit:
    """Test explore-init command."""

    def test_creates_directory_and_files(self, workspace):
        """Test that explore-init creates the directory, research.yaml, and RESEARCH_PLAN.md."""
        from research_system.cli.main import cmd_explore_init
        import argparse

        args = argparse.Namespace(
            title="Regime-Conditioned Options",
            tags="options,regime",
            workspace=str(workspace.path),
        )
        result = cmd_explore_init(args)
        assert result == 0

        research_dir = workspace.research_path / "regime-conditioned-options"
        assert research_dir.exists()
        assert (research_dir / "research.yaml").exists()
        assert (research_dir / "RESEARCH_PLAN.md").exists()

    def test_research_yaml_content(self, workspace):
        """Test that research.yaml has the correct fields."""
        from research_system.cli.main import cmd_explore_init
        import argparse

        args = argparse.Namespace(
            title="FX Carry Signal",
            tags="fx,carry",
            workspace=str(workspace.path),
        )
        cmd_explore_init(args)

        yaml_path = workspace.research_path / "fx-carry-signal" / "research.yaml"
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        assert data["topic"] == "fx-carry-signal"
        assert data["title"] == "FX Carry Signal"
        assert data["status"] == "active"
        assert data["tags"] == ["fx", "carry"]
        assert data["strategies_produced"] == []

    def test_research_plan_content(self, workspace):
        """Test that RESEARCH_PLAN.md has the expected template."""
        from research_system.cli.main import cmd_explore_init
        import argparse

        args = argparse.Namespace(
            title="Volatility Surface",
            tags="",
            workspace=str(workspace.path),
        )
        cmd_explore_init(args)

        plan_path = workspace.research_path / "volatility-surface" / "RESEARCH_PLAN.md"
        content = plan_path.read_text()

        assert "# Volatility Surface" in content
        assert "## Hypothesis" in content
        assert "## Edge Rationale" in content
        assert "## Risks" in content
        assert "## Data Inventory" in content
        assert "## Phases" in content
        assert "### Phase 1:" in content
        assert "## Strategy Implications" in content

    def test_no_tags(self, workspace):
        """Test creating research effort without tags."""
        from research_system.cli.main import cmd_explore_init
        import argparse

        args = argparse.Namespace(
            title="No Tags Research",
            tags="",
            workspace=str(workspace.path),
        )
        result = cmd_explore_init(args)
        assert result == 0

        yaml_path = workspace.research_path / "no-tags-research" / "research.yaml"
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        assert data["tags"] == []

    def test_error_on_existing_directory(self, workspace):
        """Test that explore-init errors when directory already exists."""
        from research_system.cli.main import cmd_explore_init
        import argparse

        args = argparse.Namespace(
            title="Duplicate Topic",
            tags="",
            workspace=str(workspace.path),
        )
        # Create first
        result = cmd_explore_init(args)
        assert result == 0

        # Attempt to create again
        result = cmd_explore_init(args)
        assert result == 1

    def test_error_on_empty_title(self, workspace):
        """Test that explore-init errors when title has no alphanumeric chars."""
        from research_system.cli.main import cmd_explore_init
        import argparse

        args = argparse.Namespace(
            title="!!!",
            tags="",
            workspace=str(workspace.path),
        )
        result = cmd_explore_init(args)
        assert result == 1


# ============================================================================
# explore-list
# ============================================================================


class TestExploreList:
    """Test explore-list command."""

    def _create_effort(self, workspace, topic, title, status="active", tags=None, strategies=None):
        """Helper to create a research effort directly."""
        research_dir = workspace.research_path / topic
        research_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "topic": topic,
            "title": title,
            "status": status,
            "tags": tags or [],
            "strategies_produced": strategies or [],
        }
        with open(research_dir / "research.yaml", "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def test_list_empty(self, workspace, capsys):
        """Test listing when no research efforts exist."""
        from research_system.cli.main import cmd_explore_list
        import argparse

        args = argparse.Namespace(
            index=False,
            workspace=str(workspace.path),
        )
        result = cmd_explore_list(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "No research efforts found" in captured.out

    def test_list_finds_efforts(self, workspace, capsys):
        """Test that explore-list finds and displays research efforts."""
        from research_system.cli.main import cmd_explore_list
        import argparse

        self._create_effort(workspace, "regime-options", "Regime Options", "complete",
                           tags=["options", "regime"], strategies=["STRAT-306", "STRAT-310"])
        self._create_effort(workspace, "fx-signal", "FX Signal", "paused",
                           tags=["fx"], strategies=["STRAT-277"])

        args = argparse.Namespace(
            index=False,
            workspace=str(workspace.path),
        )
        result = cmd_explore_list(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "Research Efforts:" in captured.out
        assert "regime-options" in captured.out
        assert "fx-signal" in captured.out
        assert "complete" in captured.out
        assert "paused" in captured.out

    def test_list_strategies_displayed(self, workspace, capsys):
        """Test that strategies are displayed with S prefix shorthand."""
        from research_system.cli.main import cmd_explore_list
        import argparse

        self._create_effort(workspace, "test-topic", "Test", strategies=["STRAT-100", "STRAT-200"])

        args = argparse.Namespace(
            index=False,
            workspace=str(workspace.path),
        )
        cmd_explore_list(args)

        captured = capsys.readouterr()
        assert "S100" in captured.out
        assert "S200" in captured.out

    def test_list_no_strategies_shows_dash(self, workspace, capsys):
        """Test that no strategies shows em-dash."""
        from research_system.cli.main import cmd_explore_list
        import argparse

        self._create_effort(workspace, "empty-topic", "Empty", strategies=[])

        args = argparse.Namespace(
            index=False,
            workspace=str(workspace.path),
        )
        cmd_explore_list(args)

        captured = capsys.readouterr()
        assert "\u2014" in captured.out

    def test_list_index_writes_file(self, workspace):
        """Test that --index writes INDEX.md."""
        from research_system.cli.main import cmd_explore_list
        import argparse

        self._create_effort(workspace, "regime-options", "Regime-Conditioned Options", "complete",
                           tags=["options", "regime"], strategies=["STRAT-306", "STRAT-310"])
        self._create_effort(workspace, "fx-signal", "FX Signal", "paused",
                           tags=["fx"])

        args = argparse.Namespace(
            index=True,
            workspace=str(workspace.path),
        )
        result = cmd_explore_list(args)
        assert result == 0

        index_path = workspace.research_path / "INDEX.md"
        assert index_path.exists()

        content = index_path.read_text()
        assert "# Research Index" in content
        assert "regime-options" in content
        assert "fx-signal" in content
        assert "Regime-Conditioned Options" in content
        assert "STRAT-306" in content
        assert "Auto-generated" in content

    def test_index_contains_links(self, workspace):
        """Test that INDEX.md contains links to RESEARCH_PLAN.md."""
        from research_system.cli.main import cmd_explore_list
        import argparse

        self._create_effort(workspace, "my-topic", "My Topic", "active")

        args = argparse.Namespace(
            index=True,
            workspace=str(workspace.path),
        )
        cmd_explore_list(args)

        content = (workspace.research_path / "INDEX.md").read_text()
        assert "[my-topic](my-topic/RESEARCH_PLAN.md)" in content

    def test_list_ignores_dirs_without_yaml(self, workspace, capsys):
        """Test that directories without research.yaml are ignored."""
        from research_system.cli.main import cmd_explore_list
        import argparse

        # Create a directory without research.yaml
        (workspace.research_path / "random-dir").mkdir(parents=True)
        self._create_effort(workspace, "real-effort", "Real Effort")

        args = argparse.Namespace(
            index=False,
            workspace=str(workspace.path),
        )
        cmd_explore_list(args)

        captured = capsys.readouterr()
        assert "real-effort" in captured.out
        assert "random-dir" not in captured.out


# ============================================================================
# explore-update
# ============================================================================


class TestExploreUpdate:
    """Test explore-update command."""

    def _create_effort(self, workspace, topic, title="Test", status="active",
                       tags=None, strategies=None):
        """Helper to create a research effort directly."""
        research_dir = workspace.research_path / topic
        research_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "topic": topic,
            "title": title,
            "status": status,
            "tags": tags or [],
            "strategies_produced": strategies or [],
        }
        with open(research_dir / "research.yaml", "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def test_update_status(self, workspace):
        """Test updating status."""
        from research_system.cli.main import cmd_explore_update
        import argparse

        self._create_effort(workspace, "my-topic")

        args = argparse.Namespace(
            topic="my-topic",
            status="complete",
            strategy=None,
            tag=None,
            workspace=str(workspace.path),
        )
        result = cmd_explore_update(args)
        assert result == 0

        with open(workspace.research_path / "my-topic" / "research.yaml") as f:
            data = yaml.safe_load(f)
        assert data["status"] == "complete"

    def test_update_add_strategy(self, workspace):
        """Test appending a strategy."""
        from research_system.cli.main import cmd_explore_update
        import argparse

        self._create_effort(workspace, "my-topic", strategies=["STRAT-100"])

        args = argparse.Namespace(
            topic="my-topic",
            status=None,
            strategy="STRAT-200",
            tag=None,
            workspace=str(workspace.path),
        )
        result = cmd_explore_update(args)
        assert result == 0

        with open(workspace.research_path / "my-topic" / "research.yaml") as f:
            data = yaml.safe_load(f)
        assert "STRAT-200" in data["strategies_produced"]
        assert "STRAT-100" in data["strategies_produced"]

    def test_update_strategy_no_duplicate(self, workspace, capsys):
        """Test that adding an existing strategy doesn't duplicate."""
        from research_system.cli.main import cmd_explore_update
        import argparse

        self._create_effort(workspace, "my-topic", strategies=["STRAT-100"])

        args = argparse.Namespace(
            topic="my-topic",
            status=None,
            strategy="STRAT-100",
            tag=None,
            workspace=str(workspace.path),
        )
        result = cmd_explore_update(args)
        assert result == 0

        with open(workspace.research_path / "my-topic" / "research.yaml") as f:
            data = yaml.safe_load(f)
        assert data["strategies_produced"].count("STRAT-100") == 1

        captured = capsys.readouterr()
        assert "already present" in captured.out

    def test_update_add_tag(self, workspace):
        """Test appending a tag."""
        from research_system.cli.main import cmd_explore_update
        import argparse

        self._create_effort(workspace, "my-topic", tags=["options"])

        args = argparse.Namespace(
            topic="my-topic",
            status=None,
            strategy=None,
            tag="regime",
            workspace=str(workspace.path),
        )
        result = cmd_explore_update(args)
        assert result == 0

        with open(workspace.research_path / "my-topic" / "research.yaml") as f:
            data = yaml.safe_load(f)
        assert "regime" in data["tags"]
        assert "options" in data["tags"]

    def test_update_tag_no_duplicate(self, workspace, capsys):
        """Test that adding an existing tag doesn't duplicate."""
        from research_system.cli.main import cmd_explore_update
        import argparse

        self._create_effort(workspace, "my-topic", tags=["options"])

        args = argparse.Namespace(
            topic="my-topic",
            status=None,
            strategy=None,
            tag="options",
            workspace=str(workspace.path),
        )
        result = cmd_explore_update(args)
        assert result == 0

        with open(workspace.research_path / "my-topic" / "research.yaml") as f:
            data = yaml.safe_load(f)
        assert data["tags"].count("options") == 1

        captured = capsys.readouterr()
        assert "already present" in captured.out

    def test_update_multiple_fields(self, workspace):
        """Test updating status and adding strategy at the same time."""
        from research_system.cli.main import cmd_explore_update
        import argparse

        self._create_effort(workspace, "my-topic")

        args = argparse.Namespace(
            topic="my-topic",
            status="complete",
            strategy="STRAT-310",
            tag="quality",
            workspace=str(workspace.path),
        )
        result = cmd_explore_update(args)
        assert result == 0

        with open(workspace.research_path / "my-topic" / "research.yaml") as f:
            data = yaml.safe_load(f)
        assert data["status"] == "complete"
        assert "STRAT-310" in data["strategies_produced"]
        assert "quality" in data["tags"]

    def test_error_on_missing_topic(self, workspace):
        """Test that explore-update errors when topic doesn't exist."""
        from research_system.cli.main import cmd_explore_update
        import argparse

        args = argparse.Namespace(
            topic="nonexistent",
            status="complete",
            strategy=None,
            tag=None,
            workspace=str(workspace.path),
        )
        result = cmd_explore_update(args)
        assert result == 1

    def test_error_no_update_flags(self, workspace):
        """Test that explore-update errors when no flags provided."""
        from research_system.cli.main import cmd_explore_update
        import argparse

        self._create_effort(workspace, "my-topic")

        args = argparse.Namespace(
            topic="my-topic",
            status=None,
            strategy=None,
            tag=None,
            workspace=str(workspace.path),
        )
        result = cmd_explore_update(args)
        assert result == 1


# ============================================================================
# Workspace integration
# ============================================================================


class TestWorkspaceResearchIntegration:
    """Test workspace changes for research support."""

    def test_research_in_workspace_dirs(self):
        """Test that 'research' is in WORKSPACE_DIRS."""
        assert "research" in Workspace.WORKSPACE_DIRS

    def test_init_creates_research_dir(self, tmp_path):
        """Test that workspace init creates the research directory."""
        ws = Workspace(tmp_path)
        ws.init()
        assert (tmp_path / "research").exists()
        assert (tmp_path / "research").is_dir()

    def test_research_path_property(self, tmp_path):
        """Test the research_path property."""
        ws = Workspace(tmp_path)
        assert ws.research_path == tmp_path / "research"

    def test_status_includes_research_efforts(self, tmp_path):
        """Test that status() includes research_efforts count."""
        ws = Workspace(tmp_path)
        ws.init()
        status = ws.status()
        assert "research_efforts" in status
        assert status["research_efforts"] == 0

    def test_status_counts_research_efforts(self, tmp_path):
        """Test that status() correctly counts research efforts."""
        ws = Workspace(tmp_path)
        ws.init()

        # Create two research efforts
        for topic in ["topic-a", "topic-b"]:
            d = ws.research_path / topic
            d.mkdir(parents=True)
            with open(d / "research.yaml", "w") as f:
                yaml.dump({"topic": topic}, f)

        # Create a directory without research.yaml (should not be counted)
        (ws.research_path / "not-a-research").mkdir()

        status = ws.status()
        assert status["research_efforts"] == 2
