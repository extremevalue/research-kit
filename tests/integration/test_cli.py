"""Integration tests for CLI commands."""

import pytest
import subprocess
import sys
from pathlib import Path


class TestCLIInit:
    """Tests for research init command."""

    def test_init_creates_workspace(self, temp_dir):
        """Test init creates workspace structure."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(temp_dir)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert "Initialized workspace" in result.stdout
        assert (temp_dir / "research-kit.yaml").exists()
        assert (temp_dir / "inbox").exists()
        assert (temp_dir / "strategies").exists()

    def test_init_with_name(self, temp_dir):
        """Test init with custom name."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "init", str(temp_dir),
             "--name", "My Research"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert (temp_dir / "research-kit.yaml").exists()


class TestCLICatalog:
    """Tests for research catalog commands."""

    def test_catalog_list_empty(self, temp_workspace):
        """Test listing empty catalog."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main",
             "--workspace", str(temp_workspace.path),
             "catalog", "list"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert "No matching entries" in result.stdout

    def test_catalog_stats(self, temp_workspace):
        """Test catalog stats command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main",
             "--workspace", str(temp_workspace.path),
             "catalog", "stats"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert "Catalog Statistics" in result.stdout
        assert "Total entries" in result.stdout


class TestCLIData:
    """Tests for research data commands."""

    def test_data_list(self, temp_workspace):
        """Test data list command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main",
             "--workspace", str(temp_workspace.path),
             "data", "list"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        # Should succeed even if empty
        assert result.returncode == 0


class TestCLIHelp:
    """Tests for help commands."""

    def test_main_help(self):
        """Test main help command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert "Research Validation System" in result.stdout
        assert "catalog" in result.stdout
        assert "validate" in result.stdout

    def test_validate_help(self):
        """Test validate help command."""
        result = subprocess.run(
            [sys.executable, "-m", "research_system.cli.main", "validate", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        assert result.returncode == 0
        assert "walk-forward" in result.stdout.lower() or "validation" in result.stdout.lower()
