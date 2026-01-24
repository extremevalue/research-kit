"""Tests for V4 CLI commands.

This module tests the V4 CLI commands:
1. Test --help output includes all V4 commands
2. Test each command prints "not implemented" message
3. Test --workspace flag is accepted
4. Test research init --v4 creates workspace structure
"""

import pytest
import subprocess
import sys
from pathlib import Path


# =============================================================================
# TEST HELP OUTPUT
# =============================================================================


class TestV4CLIHelp:
    """Test that V4 commands appear in help output."""

    def test_main_help_shows_v4_ingest(self):
        """Test main help shows v4-ingest command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "v4-ingest" in result.stdout

    def test_main_help_shows_v4_verify(self):
        """Test main help shows v4-verify command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "v4-verify" in result.stdout

    def test_main_help_shows_v4_validate(self):
        """Test main help shows v4-validate command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "v4-validate" in result.stdout

    def test_main_help_shows_v4_learn(self):
        """Test main help shows v4-learn command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "v4-learn" in result.stdout

    def test_main_help_shows_v4_status(self):
        """Test main help shows v4-status command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "v4-status" in result.stdout

    def test_main_help_shows_v4_list(self):
        """Test main help shows v4-list command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "v4-list" in result.stdout

    def test_main_help_shows_v4_show(self):
        """Test main help shows v4-show command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "v4-show" in result.stdout

    def test_main_help_shows_v4_config(self):
        """Test main help shows v4-config command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "v4-config" in result.stdout

    def test_init_help_shows_v4_flag(self):
        """Test init --help shows --v4 flag."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "--v4" in result.stdout


class TestV4CommandHelp:
    """Test that each V4 command shows proper help."""

    def test_v4_ingest_help(self):
        """Test v4-ingest shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-ingest", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "inbox" in result.stdout.lower()
        assert "--workspace" in result.stdout or "-w" in result.stdout

    def test_v4_verify_help(self):
        """Test v4-verify shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-verify", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "verification" in result.stdout.lower() or "bias" in result.stdout.lower()
        assert "--workspace" in result.stdout or "-w" in result.stdout

    def test_v4_validate_help(self):
        """Test v4-validate shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-validate", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "walk-forward" in result.stdout.lower() or "validation" in result.stdout.lower()
        assert "--workspace" in result.stdout or "-w" in result.stdout

    def test_v4_learn_help(self):
        """Test v4-learn shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-learn", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "learning" in result.stdout.lower()
        assert "--workspace" in result.stdout or "-w" in result.stdout

    def test_v4_status_help(self):
        """Test v4-status shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-status", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "status" in result.stdout.lower()
        assert "--workspace" in result.stdout or "-w" in result.stdout

    def test_v4_list_help(self):
        """Test v4-list shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-list", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "list" in result.stdout.lower()
        assert "--status" in result.stdout
        assert "--workspace" in result.stdout or "-w" in result.stdout

    def test_v4_show_help(self):
        """Test v4-show shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-show", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "strategy_id" in result.stdout.lower()
        assert "--workspace" in result.stdout or "-w" in result.stdout

    def test_v4_config_help(self):
        """Test v4-config shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-config", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "configuration" in result.stdout.lower() or "config" in result.stdout.lower()
        assert "--validate" in result.stdout
        assert "--workspace" in result.stdout or "-w" in result.stdout


# =============================================================================
# TEST NOT IMPLEMENTED MESSAGES
# =============================================================================


class TestV4NotImplemented:
    """Test that V4 commands print 'not implemented' message."""

    def test_v4_ingest_not_implemented(self, tmp_path):
        """Test v4-ingest prints not implemented message."""
        # First init a v4 workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-ingest",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "not implemented" in result.stdout.lower()

    def test_v4_verify_not_implemented(self, tmp_path):
        """Test v4-verify prints not implemented message."""
        # First init a v4 workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-verify",
             "--workspace", str(tmp_path), "STRAT-001"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "not implemented" in result.stdout.lower()

    def test_v4_validate_not_implemented(self, tmp_path):
        """Test v4-validate prints not implemented message."""
        # First init a v4 workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-validate",
             "--workspace", str(tmp_path), "STRAT-001"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "not implemented" in result.stdout.lower()

    def test_v4_learn_not_implemented(self, tmp_path):
        """Test v4-learn prints not implemented message."""
        # First init a v4 workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-learn",
             "--workspace", str(tmp_path), "STRAT-001"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "not implemented" in result.stdout.lower()

    def test_v4_status_not_implemented(self, tmp_path):
        """Test v4-status prints not implemented message."""
        # First init a v4 workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-status",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "not implemented" in result.stdout.lower()

    def test_v4_list_not_implemented(self, tmp_path):
        """Test v4-list prints not implemented message."""
        # First init a v4 workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-list",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "not implemented" in result.stdout.lower()

    def test_v4_show_not_implemented(self, tmp_path):
        """Test v4-show prints not implemented message."""
        # First init a v4 workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-show",
             "--workspace", str(tmp_path), "STRAT-001"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "not implemented" in result.stdout.lower()


# =============================================================================
# TEST INIT --V4
# =============================================================================


class TestV4Init:
    """Test research init --v4 command."""

    def test_init_v4_creates_workspace(self, tmp_path):
        """Test init --v4 creates V4 workspace structure."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert "Initialized V4 workspace" in result.stdout
        assert (tmp_path / "research-kit.yaml").exists()
        assert (tmp_path / "inbox").exists()
        assert (tmp_path / "strategies" / "pending").exists()
        assert (tmp_path / "strategies" / "validated").exists()
        assert (tmp_path / "strategies" / "invalidated").exists()
        assert (tmp_path / "strategies" / "blocked").exists()
        assert (tmp_path / "validations").exists()
        assert (tmp_path / "learnings").exists()
        assert (tmp_path / "ideas").exists()

    def test_init_v4_shows_next_steps(self, tmp_path):
        """Test init --v4 shows next steps."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert "Next steps" in result.stdout
        assert "v4-ingest" in result.stdout
        assert "v4-verify" in result.stdout
        assert "v4-validate" in result.stdout

    def test_init_v4_already_exists(self, tmp_path):
        """Test init --v4 fails if workspace already exists."""
        # First init
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        # Second init should fail
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 1
        assert "already exists" in result.stdout

    def test_init_v4_force_reinitializes(self, tmp_path):
        """Test init --v4 --force reinitializes workspace."""
        # First init
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        # Force reinit should succeed
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", "--force", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert "Initialized V4 workspace" in result.stdout


# =============================================================================
# TEST WORKSPACE FLAG
# =============================================================================


class TestV4WorkspaceFlag:
    """Test that --workspace flag works for V4 commands."""

    def test_v4_ingest_accepts_workspace_flag(self, tmp_path):
        """Test v4-ingest accepts --workspace flag."""
        # First init a v4 workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-ingest",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert str(tmp_path) in result.stdout

    def test_v4_ingest_accepts_short_workspace_flag(self, tmp_path):
        """Test v4-ingest accepts -w flag."""
        # First init a v4 workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-ingest",
             "-w", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert str(tmp_path) in result.stdout

    def test_v4_status_accepts_workspace_flag(self, tmp_path):
        """Test v4-status accepts --workspace flag."""
        # First init a v4 workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-status",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert str(tmp_path) in result.stdout


# =============================================================================
# TEST V4 CONFIG COMMAND
# =============================================================================


class TestV4Config:
    """Test v4-config command."""

    def test_v4_config_shows_configuration(self, tmp_path):
        """Test v4-config shows configuration values."""
        # First init a v4 workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-config",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert "min_sharpe" in result.stdout
        assert "min_consistency" in result.stdout
        assert "max_drawdown" in result.stdout
        assert "research-kit.yaml" in result.stdout

    def test_v4_config_validate_passes(self, tmp_path):
        """Test v4-config --validate passes for valid config."""
        # First init a v4 workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--v4", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-config",
             "--workspace", str(tmp_path), "--validate"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert "valid" in result.stdout.lower()


# =============================================================================
# TEST ERROR HANDLING
# =============================================================================


class TestV4ErrorHandling:
    """Test error handling for V4 commands."""

    def test_v4_ingest_requires_initialized_workspace(self, tmp_path):
        """Test v4-ingest fails if workspace not initialized."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-ingest",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 1
        assert "not initialized" in result.stdout.lower() or "init --v4" in result.stdout

    def test_v4_status_requires_initialized_workspace(self, tmp_path):
        """Test v4-status fails if workspace not initialized."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-status",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 1
        assert "not initialized" in result.stdout.lower() or "init --v4" in result.stdout

    def test_v4_config_requires_initialized_workspace(self, tmp_path):
        """Test v4-config fails if workspace not initialized."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "v4-config",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 1
        assert "not initialized" in result.stdout.lower() or "init --v4" in result.stdout
