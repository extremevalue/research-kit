"""Tests for CLI commands.

This module tests the CLI commands:
1. Test --help output includes all commands
2. Test each command prints "not implemented" message
3. Test --workspace flag is accepted
4. Test research init creates workspace structure
"""

import pytest
import subprocess
import sys
from pathlib import Path


# =============================================================================
# TEST HELP OUTPUT
# =============================================================================


class TestCLIHelp:
    """Test that commands appear in help output."""

    def test_main_help_shows_ingest(self):
        """Test main help shows ingest command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "ingest" in result.stdout

    def test_main_help_shows_verify(self):
        """Test main help shows verify command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "verify" in result.stdout

    def test_main_help_shows_validate(self):
        """Test main help shows validate command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "validate" in result.stdout

    def test_main_help_shows_learn(self):
        """Test main help shows learn command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "learn" in result.stdout

    def test_main_help_shows_status(self):
        """Test main help shows status command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "status" in result.stdout

    def test_main_help_shows_list(self):
        """Test main help shows list command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "list" in result.stdout

    def test_main_help_shows_show(self):
        """Test main help shows show command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "show" in result.stdout

    def test_main_help_shows_config(self):
        """Test main help shows config command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "config" in result.stdout

    def test_init_help(self):
        """Test init --help shows expected options."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "path" in result.stdout.lower()


class TestCommandHelp:
    """Test that each command shows proper help."""

    def test_ingest_help(self):
        """Test ingest shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "ingest", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "inbox" in result.stdout.lower()
        assert "--workspace" in result.stdout or "-w" in result.stdout

    def test_verify_help(self):
        """Test verify shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "verify", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "verification" in result.stdout.lower() or "bias" in result.stdout.lower()
        assert "--workspace" in result.stdout or "-w" in result.stdout

    def test_validate_help(self):
        """Test validate shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "validate", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "walk-forward" in result.stdout.lower() or "validation" in result.stdout.lower()
        assert "--workspace" in result.stdout or "-w" in result.stdout

    def test_learn_help(self):
        """Test learn shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "learn", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "learning" in result.stdout.lower()
        assert "--workspace" in result.stdout or "-w" in result.stdout

    def test_status_help(self):
        """Test status shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "status", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "status" in result.stdout.lower()
        assert "--workspace" in result.stdout or "-w" in result.stdout

    def test_list_help(self):
        """Test list shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "list", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "list" in result.stdout.lower()
        assert "--status" in result.stdout
        assert "--workspace" in result.stdout or "-w" in result.stdout

    def test_show_help(self):
        """Test show shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "show", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "strategy_id" in result.stdout.lower()
        assert "--workspace" in result.stdout or "-w" in result.stdout

    def test_config_help(self):
        """Test config shows help with description."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "config", "--help"],
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


class TestCommandBehavior:
    """Test that commands work correctly."""

    def test_ingest_empty_inbox(self, tmp_path):
        """Test ingest handles empty inbox gracefully."""
        # First init a workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "ingest",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "no files found in inbox" in result.stdout.lower()

    def test_ingest_processes_file(self, tmp_path):
        """Test ingest processes a file from inbox."""
        # First init a workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        # Create a test file in inbox
        inbox_path = tmp_path / "inbox"
        test_file = inbox_path / "test_strategy.txt"
        test_file.write_text("Test strategy document")

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "ingest",
             "--workspace", str(tmp_path), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "processing" in result.stdout.lower()
        assert "test_strategy.txt" in result.stdout

    def test_verify_runs(self, tmp_path):
        """Test verify runs verification tests."""
        # First init a workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "verify",
             "--workspace", str(tmp_path), "STRAT-001"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        # Returns 1 when strategy not found (which is expected)
        assert "Strategy ID required" in result.stdout or "not found" in result.stdout

    def test_validate_runs(self, tmp_path):
        """Test validate runs validation."""
        # First init a workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "validate",
             "--workspace", str(tmp_path), "STRAT-001"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        # Returns error when strategy not found
        assert "Strategy ID required" in result.stdout or "not found" in result.stdout

    def test_learn_runs(self, tmp_path):
        """Test learn extracts learnings."""
        # First init a workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "learn",
             "--workspace", str(tmp_path), "STRAT-001"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        # Returns error when strategy not found
        assert "Strategy ID required" in result.stdout or "not found" in result.stdout

    def test_status_works(self, tmp_path):
        """Test status shows workspace status."""
        # First init a workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "status",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "Research-Kit" in result.stdout
        assert "Workspace" in result.stdout

    def test_list_works(self, tmp_path):
        """Test list works on empty workspace."""
        # First init a workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "list",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0
        assert "No strategies" in result.stdout

    def test_show_not_found(self, tmp_path):
        """Test show returns error for non-existent strategy."""
        # First init a workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "show",
             "--workspace", str(tmp_path), "STRAT-001"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 1
        assert "not found" in result.stdout


# =============================================================================
# TEST INIT
# =============================================================================


class TestInit:
    """Test research init command."""

    def test_init_creates_workspace(self, tmp_path):
        """Test init creates workspace structure."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert "Initialized workspace" in result.stdout
        assert (tmp_path / "research-kit.yaml").exists()
        assert (tmp_path / "inbox").exists()
        assert (tmp_path / "strategies" / "pending").exists()
        assert (tmp_path / "strategies" / "validated").exists()
        assert (tmp_path / "strategies" / "invalidated").exists()
        assert (tmp_path / "strategies" / "blocked").exists()
        assert (tmp_path / "validations").exists()
        assert (tmp_path / "learnings").exists()
        assert (tmp_path / "ideas").exists()

    def test_init_shows_next_steps(self, tmp_path):
        """Test init shows next steps."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert "Next steps" in result.stdout
        assert "ingest" in result.stdout
        assert "verify" in result.stdout
        assert "validate" in result.stdout

    def test_init_already_exists(self, tmp_path):
        """Test init fails if workspace already exists."""
        # First init
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        # Second init should fail
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 1
        assert "already exists" in result.stdout

    def test_init_force_reinitializes(self, tmp_path):
        """Test init --force reinitializes workspace."""
        # First init
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        # Force reinit should succeed
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", "--force", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert "Initialized workspace" in result.stdout


# =============================================================================
# TEST WORKSPACE FLAG
# =============================================================================


class TestWorkspaceFlag:
    """Test that --workspace flag works for commands."""

    def test_ingest_accepts_workspace_flag(self, tmp_path):
        """Test ingest accepts --workspace flag."""
        # First init a workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "ingest",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert str(tmp_path) in result.stdout

    def test_ingest_accepts_short_workspace_flag(self, tmp_path):
        """Test ingest accepts -w flag."""
        # First init a workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "ingest",
             "-w", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert str(tmp_path) in result.stdout

    def test_status_accepts_workspace_flag(self, tmp_path):
        """Test status accepts --workspace flag."""
        # First init a workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "status",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert str(tmp_path) in result.stdout


# =============================================================================
# TEST CONFIG COMMAND
# =============================================================================


class TestConfigCommand:
    """Test config command."""

    def test_config_shows_configuration(self, tmp_path):
        """Test config shows configuration values."""
        # First init a workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "config",
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

    def test_config_validate_passes(self, tmp_path):
        """Test config --validate passes for valid config."""
        # First init a workspace
        subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "config",
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


class TestErrorHandling:
    """Test error handling for commands."""

    def test_ingest_requires_initialized_workspace(self, tmp_path):
        """Test ingest fails if workspace not initialized."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "ingest",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 1
        assert "not initialized" in result.stdout.lower() or "init" in result.stdout

    def test_status_requires_initialized_workspace(self, tmp_path):
        """Test status fails if workspace not initialized."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "status",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 1
        assert "not initialized" in result.stdout.lower() or "init" in result.stdout

    def test_config_requires_initialized_workspace(self, tmp_path):
        """Test config fails if workspace not initialized."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "config",
             "--workspace", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 1
        assert "not initialized" in result.stdout.lower() or "init" in result.stdout
