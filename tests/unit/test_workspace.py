"""Tests for workspace management."""

import pytest
from pathlib import Path

from research_system.core.workspace import Workspace, WorkspaceError


class TestWorkspace:
    """Tests for Workspace class."""

    def test_init_creates_structure(self, temp_dir):
        """Test that init creates the expected directory structure."""
        ws = Workspace(temp_dir)
        ws.init(name="Test")

        assert ws.exists
        assert ws.inbox_path.exists()
        assert ws.archive_path.exists()
        assert ws.catalog_path.exists()
        assert ws.data_registry_path.exists()
        assert ws.validations_path.exists()
        assert ws.config_file.exists()

    def test_init_with_name(self, temp_dir):
        """Test that init saves the workspace name."""
        ws = Workspace(temp_dir)
        ws.init(name="My Research")

        config = ws.load_config()
        assert config.name == "My Research"

    def test_exists_false_before_init(self, temp_dir):
        """Test that exists returns False before init."""
        ws = Workspace(temp_dir / "nonexistent")
        assert not ws.exists

    def test_double_init_without_force_fails(self, temp_dir):
        """Test that double init without force raises error."""
        ws = Workspace(temp_dir)
        ws.init(name="Test")

        # This should work because temp_workspace already initialized
        # but re-init without force should fail
        ws2 = Workspace(temp_dir)
        with pytest.raises(WorkspaceError):
            ws2.init(name="Test2")

    def test_double_init_with_force_succeeds(self, temp_dir):
        """Test that double init with force succeeds."""
        ws = Workspace(temp_dir)
        ws.init(name="Test1")

        ws.init(name="Test2", force=True)

        config = ws.load_config()
        assert config.name == "Test2"

    def test_validation_path(self, temp_workspace):
        """Test validation_path returns correct path."""
        val_path = temp_workspace.validation_path("IND-001")

        assert val_path == temp_workspace.validations_path / "IND-001"
