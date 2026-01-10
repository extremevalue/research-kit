"""Tests for codegen CLI commands.

This module tests the Typer-based CLI for code generation.
"""

import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from research_system.codegen.cli import app
from research_system.db import CatalogManager
from research_system.schemas.strategy import (
    PositionSizingConfig,
    RebalanceConfig,
    SignalConfig,
    StrategyDefinition,
    StrategyMetadata,
    UniverseConfig,
)

runner = CliRunner()


@pytest.fixture
def temp_catalog_dir():
    """Create a temporary directory for catalog testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_strategy():
    """Create a sample strategy definition."""
    return StrategyDefinition(
        tier=1,
        metadata=StrategyMetadata(
            id="CLI-TEST-001",
            name="CLI Test Strategy",
            description="A test strategy for CLI testing",
            tags=["test", "cli"],
        ),
        strategy_type="momentum_rotation",
        universe=UniverseConfig(
            type="fixed",
            symbols=["SPY", "TLT", "GLD"],
            defensive_symbols=["SHY"],
        ),
        signal=SignalConfig(
            type="relative_momentum",
            lookback_days=126,
            selection_n=2,
        ),
        position_sizing=PositionSizingConfig(method="equal_weight", leverage=1.0),
        rebalance=RebalanceConfig(frequency="monthly"),
    )


@pytest.fixture
def catalog_with_strategy(temp_catalog_dir, sample_strategy):
    """Create a catalog with a sample strategy."""
    catalog = CatalogManager(temp_catalog_dir)
    catalog.create_entry(sample_strategy)
    catalog.close()

    return temp_catalog_dir, sample_strategy.metadata.id


class TestGenerateCommand:
    """Tests for the 'generate' CLI command."""

    def test_generate_to_stdout(self, catalog_with_strategy):
        """Test generating code to stdout."""
        catalog_dir, strategy_id = catalog_with_strategy

        result = runner.invoke(
            app, ["generate", strategy_id, "--catalog", str(catalog_dir), "--stdout"]
        )

        assert result.exit_code == 0
        assert "class CliTest001(QCAlgorithm):" in result.stdout
        assert "def Initialize(self):" in result.stdout

    def test_generate_to_file(self, catalog_with_strategy):
        """Test generating code to a file."""
        catalog_dir, strategy_id = catalog_with_strategy

        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "strategy.py"

            result = runner.invoke(
                app,
                [
                    "generate",
                    strategy_id,
                    "--catalog",
                    str(catalog_dir),
                    "--output",
                    str(output_path),
                ],
            )

            assert result.exit_code == 0
            assert output_path.exists()
            assert "Generated:" in result.stdout

            content = output_path.read_text()
            assert "class CliTest001(QCAlgorithm):" in content

    def test_generate_file_exists_no_overwrite(self, catalog_with_strategy):
        """Test that generate fails if file exists without --overwrite."""
        catalog_dir, strategy_id = catalog_with_strategy

        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "strategy.py"
            output_path.write_text("existing content")

            result = runner.invoke(
                app,
                [
                    "generate",
                    strategy_id,
                    "--catalog",
                    str(catalog_dir),
                    "--output",
                    str(output_path),
                ],
            )

            assert result.exit_code == 1
            assert "already exists" in result.stdout
            assert output_path.read_text() == "existing content"

    def test_generate_file_with_overwrite(self, catalog_with_strategy):
        """Test that generate overwrites with --overwrite flag."""
        catalog_dir, strategy_id = catalog_with_strategy

        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "strategy.py"
            output_path.write_text("existing content")

            result = runner.invoke(
                app,
                [
                    "generate",
                    strategy_id,
                    "--catalog",
                    str(catalog_dir),
                    "--output",
                    str(output_path),
                    "--overwrite",
                ],
            )

            assert result.exit_code == 0
            content = output_path.read_text()
            assert "class CliTest001(QCAlgorithm):" in content

    def test_generate_strategy_not_found(self, temp_catalog_dir):
        """Test error when strategy not found."""
        # Initialize empty catalog
        catalog = CatalogManager(temp_catalog_dir)
        catalog.close()

        result = runner.invoke(
            app,
            [
                "generate",
                "NONEXISTENT-001",
                "--catalog",
                str(temp_catalog_dir),
                "--stdout",
            ],
        )

        assert result.exit_code == 1
        assert "Error:" in result.stdout

    def test_generate_without_output_prints_to_stdout(self, catalog_with_strategy):
        """Test that generate without --output prints to stdout."""
        catalog_dir, strategy_id = catalog_with_strategy

        result = runner.invoke(app, ["generate", strategy_id, "--catalog", str(catalog_dir)])

        assert result.exit_code == 0
        assert "class CliTest001(QCAlgorithm):" in result.stdout

    def test_generate_with_validation_disabled(self, catalog_with_strategy):
        """Test generating with validation disabled."""
        catalog_dir, strategy_id = catalog_with_strategy

        result = runner.invoke(
            app,
            [
                "generate",
                strategy_id,
                "--catalog",
                str(catalog_dir),
                "--stdout",
                "--no-validate",
            ],
        )

        assert result.exit_code == 0
        assert "class CliTest001(QCAlgorithm):" in result.stdout


class TestValidateCommand:
    """Tests for the 'validate' CLI command."""

    def test_validate_valid_strategy(self, catalog_with_strategy):
        """Test validating a valid strategy."""
        catalog_dir, strategy_id = catalog_with_strategy

        result = runner.invoke(app, ["validate", strategy_id, "--catalog", str(catalog_dir)])

        # Should pass (exit code 0) or just have warnings
        # Valid strategies should not have critical errors
        assert "Syntax error" not in result.stdout
        assert "Missing QCAlgorithm" not in result.stdout

    def test_validate_strategy_not_found(self, temp_catalog_dir):
        """Test validation error when strategy not found."""
        catalog = CatalogManager(temp_catalog_dir)
        catalog.close()

        result = runner.invoke(
            app, ["validate", "NONEXISTENT-001", "--catalog", str(temp_catalog_dir)]
        )

        assert result.exit_code == 1
        assert "Error:" in result.stdout


class TestDemoCommand:
    """Tests for the 'demo' CLI command."""

    def test_demo_momentum_rotation(self):
        """Test demo for momentum_rotation strategy."""
        result = runner.invoke(app, ["demo", "momentum_rotation"])

        assert result.exit_code == 0
        # Class name derived from ID: DEMO-MOMENTUM -> DemoMomentum
        assert "class DemoMomentum(QCAlgorithm):" in result.stdout
        assert "def Initialize(self):" in result.stdout

    def test_demo_mean_reversion(self):
        """Test demo for mean_reversion strategy."""
        result = runner.invoke(app, ["demo", "mean_reversion"])

        assert result.exit_code == 0
        # Class name derived from ID: DEMO-MEANREV -> DemoMeanrev
        assert "class DemoMeanrev(QCAlgorithm):" in result.stdout

    def test_demo_trend_following(self):
        """Test demo for trend_following strategy."""
        result = runner.invoke(app, ["demo", "trend_following"])

        assert result.exit_code == 0
        # Class name derived from ID: DEMO-TREND -> DemoTrend
        assert "class DemoTrend(QCAlgorithm):" in result.stdout

    def test_demo_dual_momentum(self):
        """Test demo for dual_momentum strategy."""
        result = runner.invoke(app, ["demo", "dual_momentum"])

        assert result.exit_code == 0
        # Class name derived from ID: DEMO-DUALMOM -> DemoDualmom
        assert "class DemoDualmom(QCAlgorithm):" in result.stdout

    def test_demo_breakout(self):
        """Test demo for breakout strategy."""
        result = runner.invoke(app, ["demo", "breakout"])

        assert result.exit_code == 0
        assert "class DemoBreakout(QCAlgorithm):" in result.stdout

    def test_demo_unknown_type(self):
        """Test demo with unknown strategy type."""
        result = runner.invoke(app, ["demo", "unknown_type"])

        assert result.exit_code == 1
        assert "Unknown strategy type" in result.stdout

    def test_demo_to_file(self):
        """Test demo output to file."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "demo.py"

            result = runner.invoke(app, ["demo", "momentum_rotation", "--output", str(output_path)])

            assert result.exit_code == 0
            assert output_path.exists()
            assert "Generated demo:" in result.stdout

            content = output_path.read_text()
            assert "class DemoMomentum(QCAlgorithm):" in content


class TestListTemplatesCommand:
    """Tests for the 'list-templates' CLI command."""

    def test_list_templates(self):
        """Test listing available templates."""
        result = runner.invoke(app, ["list-templates"])

        assert result.exit_code == 0
        assert "Strategy Type Templates:" in result.stdout
        assert "Signal Type Templates:" in result.stdout
        assert "momentum_rotation" in result.stdout
        assert "mean_reversion" in result.stdout
        assert "trend_following" in result.stdout


class TestCLIHelp:
    """Tests for CLI help messages."""

    def test_help(self):
        """Test main help message."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Generate QuantConnect-compatible strategy code" in result.stdout

    def test_generate_help(self):
        """Test generate command help."""
        result = runner.invoke(app, ["generate", "--help"])

        assert result.exit_code == 0
        assert "Generate code for a strategy from the catalog" in result.stdout
        assert "--output" in result.stdout
        assert "--catalog" in result.stdout

    def test_validate_help(self):
        """Test validate command help."""
        result = runner.invoke(app, ["validate", "--help"])

        assert result.exit_code == 0
        assert "Validate generated code" in result.stdout

    def test_demo_help(self):
        """Test demo command help."""
        result = runner.invoke(app, ["demo", "--help"])

        assert result.exit_code == 0
        assert "Generate demo code" in result.stdout

    def test_list_templates_help(self):
        """Test list-templates command help."""
        result = runner.invoke(app, ["list-templates", "--help"])

        assert result.exit_code == 0
        assert "List available strategy templates" in result.stdout
