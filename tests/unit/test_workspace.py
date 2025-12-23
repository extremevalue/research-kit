"""Tests for workspace management."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from research_system.core.workspace import (
    Workspace,
    WorkspaceError,
    QCCredentials,
    _load_lean_cli_credentials,
    LEAN_CREDENTIALS_PATH,
)


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


class TestQCCredentials:
    """Tests for QC credential resolution."""

    def test_get_credentials_from_config(self, temp_workspace):
        """Test that workspace config credentials take priority."""
        # Update config with QC credentials
        config = temp_workspace.config
        config.qc_user_id = "12345"
        config.qc_api_token = "test-token"
        config.qc_organization_id = "my-org"
        temp_workspace._save_config(config)
        temp_workspace._config = None  # Clear cached config

        creds = temp_workspace.get_qc_credentials()

        assert creds is not None
        assert creds.user_id == "12345"
        assert creds.api_token == "test-token"
        assert creds.organization_id == "my-org"
        assert creds.source == "config"

    def test_get_credentials_falls_back_to_lean_cli(self, temp_workspace, tmp_path):
        """Test fallback to Lean CLI credentials."""
        # Create mock Lean CLI credentials
        lean_creds_file = tmp_path / ".lean" / "credentials"
        lean_creds_file.parent.mkdir(parents=True)
        lean_creds_file.write_text(json.dumps({
            "user-id": "67890",
            "api-token": "lean-token",
            "organization-id": "lean-org"
        }))

        with patch("research_system.core.workspace.LEAN_CREDENTIALS_PATH", lean_creds_file):
            creds = temp_workspace.get_qc_credentials()

        assert creds is not None
        assert creds.user_id == "67890"
        assert creds.api_token == "lean-token"
        assert creds.organization_id == "lean-org"
        assert creds.source == "lean_cli"

    def test_get_credentials_returns_none_when_missing(self, temp_workspace, tmp_path):
        """Test returns None when no credentials configured."""
        # Point to non-existent Lean CLI path
        with patch("research_system.core.workspace.LEAN_CREDENTIALS_PATH", tmp_path / "nonexistent"):
            creds = temp_workspace.get_qc_credentials()

        assert creds is None

    def test_load_lean_cli_credentials_handles_malformed_json(self, tmp_path):
        """Test graceful handling of malformed Lean CLI credentials."""
        lean_creds_file = tmp_path / "credentials"
        lean_creds_file.write_text("not valid json")

        with patch("research_system.core.workspace.LEAN_CREDENTIALS_PATH", lean_creds_file):
            creds = _load_lean_cli_credentials()

        assert creds is None

    def test_load_lean_cli_credentials_requires_user_id_and_token(self, tmp_path):
        """Test that both user-id and api-token are required."""
        lean_creds_file = tmp_path / "credentials"
        lean_creds_file.write_text(json.dumps({
            "user-id": "12345"
            # missing api-token
        }))

        with patch("research_system.core.workspace.LEAN_CREDENTIALS_PATH", lean_creds_file):
            creds = _load_lean_cli_credentials()

        assert creds is None
