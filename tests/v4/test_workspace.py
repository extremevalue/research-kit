"""Tests for V4 workspace management.

This module tests the V4 workspace functionality:
1. Workspace initialization creates all directories
2. ID generation increments correctly
3. ID persistence across workspace instances
4. Strategy path resolution for different statuses
5. Move strategy between status directories
6. Config file generation
7. .env.template generation
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from research_system.core.v4 import (
    Workspace,
    WorkspaceError,
    get_workspace,
    require_workspace,
    DEFAULT_WORKSPACE,
    WORKSPACE_ENV_VAR,
    Config,
)


# =============================================================================
# TEST WORKSPACE INITIALIZATION
# =============================================================================


class TestWorkspaceInit:
    """Test workspace initialization."""

    def test_init_creates_all_directories(self, tmp_path):
        """Test that init creates all expected directories."""
        ws = Workspace(tmp_path)
        ws.init()

        # Check all workspace directories exist
        for dir_path in Workspace.WORKSPACE_DIRS:
            assert (tmp_path / dir_path).exists(), f"Directory {dir_path} not created"
            assert (tmp_path / dir_path).is_dir(), f"{dir_path} is not a directory"

    def test_init_creates_config_file(self, tmp_path):
        """Test that init creates research-kit.yaml."""
        ws = Workspace(tmp_path)
        ws.init()

        config_file = tmp_path / "research-kit.yaml"
        assert config_file.exists()

        # Verify it's valid YAML with expected structure
        with open(config_file) as f:
            data = yaml.safe_load(f)

        assert "version" in data
        assert "gates" in data
        assert "ingestion" in data

    def test_init_creates_env_template(self, tmp_path):
        """Test that init creates .env.template."""
        ws = Workspace(tmp_path)
        ws.init()

        env_template = tmp_path / ".env.template"
        assert env_template.exists()

        content = env_template.read_text()
        assert "ANTHROPIC_API_KEY" in content
        assert "RESEARCH_WORKSPACE" in content
        assert "QC_USER_ID" in content
        assert "QC_API_TOKEN" in content

    def test_init_creates_counters_file(self, tmp_path):
        """Test that init creates counters.json."""
        ws = Workspace(tmp_path)
        ws.init()

        counters_file = tmp_path / ".state" / "counters.json"
        assert counters_file.exists()

        with open(counters_file) as f:
            counters = json.load(f)

        assert counters["strategy"] == 0
        assert counters["idea"] == 0

    def test_init_with_custom_name(self, tmp_path):
        """Test that init accepts custom workspace name."""
        ws = Workspace(tmp_path)
        ws.init(name="Custom Workspace")

        # Name is stored in config but Config doesn't have a name field
        # The workspace was initialized successfully
        assert ws.exists

    def test_init_returns_true_on_success(self, tmp_path):
        """Test that init returns True when creating new workspace."""
        ws = Workspace(tmp_path)
        result = ws.init()

        assert result is True

    def test_init_returns_false_if_exists(self, tmp_path):
        """Test that init returns False if workspace already exists."""
        ws = Workspace(tmp_path)
        ws.init()

        result = ws.init()
        assert result is False

    def test_init_with_force_reinitializes(self, tmp_path):
        """Test that init with force=True reinitializes workspace."""
        ws = Workspace(tmp_path)
        ws.init()

        # Modify counters
        counters_file = tmp_path / ".state" / "counters.json"
        with open(counters_file, "w") as f:
            json.dump({"strategy": 100, "idea": 50}, f)

        # Reinitialize with force
        result = ws.init(force=True)
        assert result is True

        # Counters should be reset
        with open(counters_file) as f:
            counters = json.load(f)
        assert counters["strategy"] == 0
        assert counters["idea"] == 0


# =============================================================================
# TEST WORKSPACE EXISTS
# =============================================================================


class TestWorkspaceExists:
    """Test workspace existence checking."""

    def test_exists_false_before_init(self, tmp_path):
        """Test that exists is False before initialization."""
        ws = Workspace(tmp_path)
        assert ws.exists is False

    def test_exists_true_after_init(self, tmp_path):
        """Test that exists is True after initialization."""
        ws = Workspace(tmp_path)
        ws.init()
        assert ws.exists is True

    def test_exists_checks_config_file(self, tmp_path):
        """Test that exists checks for research-kit.yaml."""
        ws = Workspace(tmp_path)
        tmp_path.mkdir(parents=True, exist_ok=True)

        # Directory exists but no config
        assert ws.exists is False

        # Create config file
        (tmp_path / "research-kit.yaml").write_text("version: '1.0'")
        assert ws.exists is True


# =============================================================================
# TEST ID GENERATION
# =============================================================================


class TestIDGeneration:
    """Test ID generation functionality."""

    def test_next_strategy_id_starts_at_001(self, tmp_path):
        """Test that first strategy ID is STRAT-001."""
        ws = Workspace(tmp_path)
        ws.init()

        strat_id = ws.next_strategy_id()
        assert strat_id == "STRAT-001"

    def test_next_strategy_id_increments(self, tmp_path):
        """Test that strategy ID increments correctly."""
        ws = Workspace(tmp_path)
        ws.init()

        ids = [ws.next_strategy_id() for _ in range(5)]
        assert ids == ["STRAT-001", "STRAT-002", "STRAT-003", "STRAT-004", "STRAT-005"]

    def test_next_idea_id_starts_at_001(self, tmp_path):
        """Test that first idea ID is IDEA-001."""
        ws = Workspace(tmp_path)
        ws.init()

        idea_id = ws.next_idea_id()
        assert idea_id == "IDEA-001"

    def test_next_idea_id_increments(self, tmp_path):
        """Test that idea ID increments correctly."""
        ws = Workspace(tmp_path)
        ws.init()

        ids = [ws.next_idea_id() for _ in range(5)]
        assert ids == ["IDEA-001", "IDEA-002", "IDEA-003", "IDEA-004", "IDEA-005"]

    def test_strategy_and_idea_counters_independent(self, tmp_path):
        """Test that strategy and idea counters are independent."""
        ws = Workspace(tmp_path)
        ws.init()

        strat1 = ws.next_strategy_id()
        idea1 = ws.next_idea_id()
        strat2 = ws.next_strategy_id()
        idea2 = ws.next_idea_id()

        assert strat1 == "STRAT-001"
        assert idea1 == "IDEA-001"
        assert strat2 == "STRAT-002"
        assert idea2 == "IDEA-002"

    def test_ids_zero_padded_to_three_digits(self, tmp_path):
        """Test that IDs are zero-padded to 3 digits."""
        ws = Workspace(tmp_path)
        ws.init()

        # Set counter to 47
        counters_file = tmp_path / ".state" / "counters.json"
        with open(counters_file, "w") as f:
            json.dump({"strategy": 46, "idea": 11}, f)

        strat_id = ws.next_strategy_id()
        idea_id = ws.next_idea_id()

        assert strat_id == "STRAT-047"
        assert idea_id == "IDEA-012"


# =============================================================================
# TEST ID PERSISTENCE
# =============================================================================


class TestIDPersistence:
    """Test ID persistence across workspace instances."""

    def test_ids_persist_across_instances(self, tmp_path):
        """Test that IDs persist when creating new workspace instance."""
        ws1 = Workspace(tmp_path)
        ws1.init()

        # Generate some IDs
        ws1.next_strategy_id()  # STRAT-001
        ws1.next_strategy_id()  # STRAT-002
        ws1.next_idea_id()      # IDEA-001

        # Create new instance
        ws2 = Workspace(tmp_path)

        # IDs should continue from where they left off
        assert ws2.next_strategy_id() == "STRAT-003"
        assert ws2.next_idea_id() == "IDEA-002"

    def test_counters_saved_after_each_increment(self, tmp_path):
        """Test that counters are saved immediately after each increment."""
        ws = Workspace(tmp_path)
        ws.init()

        ws.next_strategy_id()

        # Read counters directly
        counters_file = tmp_path / ".state" / "counters.json"
        with open(counters_file) as f:
            counters = json.load(f)

        assert counters["strategy"] == 1


# =============================================================================
# TEST STRATEGY PATH RESOLUTION
# =============================================================================


class TestStrategyPath:
    """Test strategy path resolution."""

    def test_strategy_path_pending(self, tmp_path):
        """Test strategy path for pending status."""
        ws = Workspace(tmp_path)
        ws.init()

        path = ws.strategy_path("STRAT-001", status="pending")
        assert path == tmp_path / "strategies" / "pending" / "STRAT-001.yaml"

    def test_strategy_path_validated(self, tmp_path):
        """Test strategy path for validated status."""
        ws = Workspace(tmp_path)
        ws.init()

        path = ws.strategy_path("STRAT-001", status="validated")
        assert path == tmp_path / "strategies" / "validated" / "STRAT-001.yaml"

    def test_strategy_path_invalidated(self, tmp_path):
        """Test strategy path for invalidated status."""
        ws = Workspace(tmp_path)
        ws.init()

        path = ws.strategy_path("STRAT-001", status="invalidated")
        assert path == tmp_path / "strategies" / "invalidated" / "STRAT-001.yaml"

    def test_strategy_path_blocked(self, tmp_path):
        """Test strategy path for blocked status."""
        ws = Workspace(tmp_path)
        ws.init()

        path = ws.strategy_path("STRAT-001", status="blocked")
        assert path == tmp_path / "strategies" / "blocked" / "STRAT-001.yaml"

    def test_strategy_path_default_is_pending(self, tmp_path):
        """Test that default status is pending."""
        ws = Workspace(tmp_path)
        ws.init()

        path = ws.strategy_path("STRAT-001")
        assert path == tmp_path / "strategies" / "pending" / "STRAT-001.yaml"

    def test_strategy_path_invalid_status_raises(self, tmp_path):
        """Test that invalid status raises ValueError."""
        ws = Workspace(tmp_path)
        ws.init()

        with pytest.raises(ValueError, match="Invalid status"):
            ws.strategy_path("STRAT-001", status="invalid")


# =============================================================================
# TEST MOVE STRATEGY
# =============================================================================


class TestMoveStrategy:
    """Test moving strategies between status directories."""

    def test_move_strategy_pending_to_validated(self, tmp_path):
        """Test moving strategy from pending to validated."""
        ws = Workspace(tmp_path)
        ws.init()

        # Create a strategy file in pending
        pending_path = tmp_path / "strategies" / "pending" / "STRAT-001.yaml"
        pending_path.write_text("name: Test Strategy")

        # Move to validated
        new_path = ws.move_strategy("STRAT-001", "pending", "validated")

        assert new_path == tmp_path / "strategies" / "validated" / "STRAT-001.yaml"
        assert new_path.exists()
        assert not pending_path.exists()
        assert new_path.read_text() == "name: Test Strategy"

    def test_move_strategy_validated_to_invalidated(self, tmp_path):
        """Test moving strategy from validated to invalidated."""
        ws = Workspace(tmp_path)
        ws.init()

        # Create a strategy file in validated
        validated_path = tmp_path / "strategies" / "validated" / "STRAT-002.yaml"
        validated_path.write_text("name: Another Strategy")

        # Move to invalidated
        new_path = ws.move_strategy("STRAT-002", "validated", "invalidated")

        assert new_path == tmp_path / "strategies" / "invalidated" / "STRAT-002.yaml"
        assert new_path.exists()
        assert not validated_path.exists()

    def test_move_strategy_to_blocked(self, tmp_path):
        """Test moving strategy to blocked status."""
        ws = Workspace(tmp_path)
        ws.init()

        # Create a strategy file in pending
        pending_path = tmp_path / "strategies" / "pending" / "STRAT-003.yaml"
        pending_path.write_text("name: Blocked Strategy")

        # Move to blocked
        new_path = ws.move_strategy("STRAT-003", "pending", "blocked")

        assert new_path == tmp_path / "strategies" / "blocked" / "STRAT-003.yaml"
        assert new_path.exists()

    def test_move_strategy_invalid_from_status_raises(self, tmp_path):
        """Test that invalid from_status raises ValueError."""
        ws = Workspace(tmp_path)
        ws.init()

        with pytest.raises(ValueError, match="Invalid from_status"):
            ws.move_strategy("STRAT-001", "invalid", "validated")

    def test_move_strategy_invalid_to_status_raises(self, tmp_path):
        """Test that invalid to_status raises ValueError."""
        ws = Workspace(tmp_path)
        ws.init()

        with pytest.raises(ValueError, match="Invalid to_status"):
            ws.move_strategy("STRAT-001", "pending", "invalid")

    def test_move_strategy_not_found_raises(self, tmp_path):
        """Test that moving non-existent strategy raises error."""
        ws = Workspace(tmp_path)
        ws.init()

        with pytest.raises(WorkspaceError, match="Strategy file not found"):
            ws.move_strategy("STRAT-999", "pending", "validated")


# =============================================================================
# TEST CONFIG LOADING
# =============================================================================


class TestConfigLoading:
    """Test configuration loading from workspace."""

    def test_config_loads_after_init(self, tmp_path):
        """Test that config loads correctly after init."""
        ws = Workspace(tmp_path)
        ws.init()

        config = ws.config
        assert isinstance(config, Config)
        assert config.version == "1.0"

    def test_config_returns_cached_instance(self, tmp_path):
        """Test that config returns cached instance."""
        ws = Workspace(tmp_path)
        ws.init()

        config1 = ws.config
        config2 = ws.config

        assert config1 is config2

    def test_config_raises_if_not_initialized(self, tmp_path):
        """Test that accessing config before init raises error."""
        ws = Workspace(tmp_path)

        with pytest.raises(WorkspaceError, match="not initialized"):
            _ = ws.config


# =============================================================================
# TEST PATH PROPERTIES
# =============================================================================


class TestPathProperties:
    """Test path property accessors."""

    def test_inbox_path(self, tmp_path):
        """Test inbox_path property."""
        ws = Workspace(tmp_path)
        assert ws.inbox_path == tmp_path / "inbox"

    def test_strategies_path(self, tmp_path):
        """Test strategies_path property."""
        ws = Workspace(tmp_path)
        assert ws.strategies_path == tmp_path / "strategies"

    def test_validations_path(self, tmp_path):
        """Test validations_path property."""
        ws = Workspace(tmp_path)
        assert ws.validations_path == tmp_path / "validations"

    def test_learnings_path(self, tmp_path):
        """Test learnings_path property."""
        ws = Workspace(tmp_path)
        assert ws.learnings_path == tmp_path / "learnings"

    def test_ideas_path(self, tmp_path):
        """Test ideas_path property."""
        ws = Workspace(tmp_path)
        assert ws.ideas_path == tmp_path / "ideas"

    def test_personas_path(self, tmp_path):
        """Test personas_path property."""
        ws = Workspace(tmp_path)
        assert ws.personas_path == tmp_path / "personas"

    def test_archive_path(self, tmp_path):
        """Test archive_path property."""
        ws = Workspace(tmp_path)
        assert ws.archive_path == tmp_path / "archive"

    def test_logs_path(self, tmp_path):
        """Test logs_path property."""
        ws = Workspace(tmp_path)
        assert ws.logs_path == tmp_path / "logs"

    def test_state_path(self, tmp_path):
        """Test state_path property."""
        ws = Workspace(tmp_path)
        assert ws.state_path == tmp_path / ".state"


# =============================================================================
# TEST PATH RESOLUTION
# =============================================================================


class TestPathResolution:
    """Test workspace path resolution."""

    def test_explicit_path_used(self, tmp_path):
        """Test that explicit path is used."""
        ws = Workspace(tmp_path / "custom")
        assert ws.path == tmp_path / "custom"

    def test_string_path_converted(self, tmp_path):
        """Test that string path is converted to Path."""
        ws = Workspace(str(tmp_path / "custom"))
        assert ws.path == tmp_path / "custom"
        assert isinstance(ws.path, Path)

    def test_env_var_used_when_no_path(self, tmp_path, monkeypatch):
        """Test that environment variable is used when no path given."""
        monkeypatch.setenv(WORKSPACE_ENV_VAR, str(tmp_path / "env-workspace"))

        ws = Workspace()
        assert ws.path == tmp_path / "env-workspace"

    def test_default_path_when_no_env(self, monkeypatch):
        """Test that default path is used when no env var."""
        monkeypatch.delenv(WORKSPACE_ENV_VAR, raising=False)

        ws = Workspace()
        assert ws.path == DEFAULT_WORKSPACE

    def test_explicit_path_overrides_env(self, tmp_path, monkeypatch):
        """Test that explicit path overrides environment variable."""
        monkeypatch.setenv(WORKSPACE_ENV_VAR, str(tmp_path / "env-workspace"))

        ws = Workspace(tmp_path / "explicit")
        assert ws.path == tmp_path / "explicit"


# =============================================================================
# TEST HELPER FUNCTIONS
# =============================================================================


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_workspace(self, tmp_path):
        """Test get_workspace function."""
        ws = get_workspace(tmp_path)
        assert isinstance(ws, Workspace)
        assert ws.path == tmp_path

    def test_get_workspace_no_path(self, monkeypatch):
        """Test get_workspace with no path uses default."""
        monkeypatch.delenv(WORKSPACE_ENV_VAR, raising=False)

        ws = get_workspace()
        assert ws.path == DEFAULT_WORKSPACE

    def test_require_workspace_initialized(self, tmp_path):
        """Test require_workspace with initialized workspace."""
        ws = Workspace(tmp_path)
        ws.init()

        required_ws = require_workspace(tmp_path)
        assert isinstance(required_ws, Workspace)
        assert required_ws.path == tmp_path

    def test_require_workspace_raises_if_not_initialized(self, tmp_path):
        """Test require_workspace raises if not initialized."""
        with pytest.raises(WorkspaceError, match="not initialized"):
            require_workspace(tmp_path)


# =============================================================================
# TEST WORKSPACE STATUS
# =============================================================================


class TestWorkspaceStatus:
    """Test workspace status reporting."""

    def test_status_returns_dict(self, tmp_path):
        """Test that status returns a dictionary."""
        ws = Workspace(tmp_path)
        ws.init()

        status = ws.status()
        assert isinstance(status, dict)

    def test_status_includes_path(self, tmp_path):
        """Test that status includes workspace path."""
        ws = Workspace(tmp_path)
        ws.init()

        status = ws.status()
        assert status["path"] == str(tmp_path)

    def test_status_includes_strategy_counts(self, tmp_path):
        """Test that status includes strategy counts by status."""
        ws = Workspace(tmp_path)
        ws.init()

        # Create some strategy files
        (tmp_path / "strategies" / "pending" / "STRAT-001.yaml").write_text("test")
        (tmp_path / "strategies" / "pending" / "STRAT-002.yaml").write_text("test")
        (tmp_path / "strategies" / "validated" / "STRAT-003.yaml").write_text("test")

        status = ws.status()
        assert status["strategies"]["pending"] == 2
        assert status["strategies"]["validated"] == 1
        assert status["strategies"]["invalidated"] == 0
        assert status["strategies"]["blocked"] == 0

    def test_status_includes_counters(self, tmp_path):
        """Test that status includes current counters."""
        ws = Workspace(tmp_path)
        ws.init()

        ws.next_strategy_id()
        ws.next_strategy_id()
        ws.next_idea_id()

        status = ws.status()
        assert status["counters"]["strategy"] == 2
        assert status["counters"]["idea"] == 1

    def test_status_raises_if_not_initialized(self, tmp_path):
        """Test that status raises error if not initialized."""
        ws = Workspace(tmp_path)

        with pytest.raises(WorkspaceError, match="not initialized"):
            ws.status()


# =============================================================================
# TEST REQUIRE INITIALIZED
# =============================================================================


class TestRequireInitialized:
    """Test require_initialized method."""

    def test_require_initialized_passes_when_initialized(self, tmp_path):
        """Test require_initialized passes for initialized workspace."""
        ws = Workspace(tmp_path)
        ws.init()

        # Should not raise
        ws.require_initialized()

    def test_require_initialized_raises_when_not_initialized(self, tmp_path):
        """Test require_initialized raises for uninitialized workspace."""
        ws = Workspace(tmp_path)

        with pytest.raises(WorkspaceError, match="not initialized"):
            ws.require_initialized()
