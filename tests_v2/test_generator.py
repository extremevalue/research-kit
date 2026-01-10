"""Tests for CodeGenerator class.

This module tests the high-level code generation API that integrates
the TemplateEngine with CatalogManager.
"""

import tempfile
from pathlib import Path

import pytest

from research_system.codegen.engine import CodeGenerationError
from research_system.codegen.generator import CodeGenerator
from research_system.db import CatalogManager
from research_system.schemas.strategy import (
    PositionSizingConfig,
    RebalanceConfig,
    SignalConfig,
    StrategyDefinition,
    StrategyMetadata,
    UniverseConfig,
)


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
            id="TEST-001",
            name="Test Momentum Strategy",
            description="A test momentum rotation strategy",
            tags=["test", "momentum"],
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

    # Add the strategy to the catalog
    catalog.create_entry(sample_strategy)

    yield temp_catalog_dir, sample_strategy.metadata.id

    catalog.close()


class TestCodeGeneratorInit:
    """Tests for CodeGenerator initialization."""

    def test_init_with_path(self, temp_catalog_dir):
        """Test initialization with explicit path."""
        generator = CodeGenerator(temp_catalog_dir)
        assert generator._catalog_path == temp_catalog_dir
        generator.close()

    def test_init_with_string_path(self, temp_catalog_dir):
        """Test initialization with string path."""
        generator = CodeGenerator(str(temp_catalog_dir))
        assert generator._catalog_path == temp_catalog_dir
        generator.close()

    def test_init_without_path_uses_cwd(self):
        """Test initialization without path uses current directory."""
        generator = CodeGenerator()
        assert generator._catalog_path == Path.cwd()
        generator.close()

    def test_context_manager(self, temp_catalog_dir):
        """Test context manager usage."""
        with CodeGenerator(temp_catalog_dir) as generator:
            assert generator._catalog is None  # Lazy initialization
        # After exit, catalog should be closed
        assert generator._catalog is None


class TestCodeGeneratorGenerate:
    """Tests for code generation methods."""

    def test_generate_from_catalog(self, catalog_with_strategy):
        """Test generating code from a catalog entry."""
        catalog_dir, strategy_id = catalog_with_strategy

        with CodeGenerator(catalog_dir) as generator:
            code = generator.generate(strategy_id)

        assert "class Test001(QCAlgorithm):" in code
        assert "def Initialize(self):" in code
        assert "SPY" in code
        assert "TLT" in code
        assert "GLD" in code

    def test_generate_strategy_not_found(self, temp_catalog_dir):
        """Test error when strategy not found."""
        # Initialize catalog without any entries
        catalog = CatalogManager(temp_catalog_dir)
        catalog.close()

        with (
            CodeGenerator(temp_catalog_dir) as generator,
            pytest.raises(CodeGenerationError, match="Strategy not found"),
        ):
            generator.generate("NONEXISTENT-001")

    def test_generate_from_definition(self, temp_catalog_dir, sample_strategy):
        """Test generating code directly from definition."""
        with CodeGenerator(temp_catalog_dir) as generator:
            code = generator.generate_from_definition(sample_strategy)

        assert "class Test001(QCAlgorithm):" in code
        assert "def Initialize(self):" in code

    def test_generate_to_file(self, catalog_with_strategy):
        """Test generating code to a file."""
        catalog_dir, strategy_id = catalog_with_strategy

        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "strategy.py"

            with CodeGenerator(catalog_dir) as generator:
                result_path = generator.generate_to_file(strategy_id, output_path)

            assert result_path == output_path
            assert output_path.exists()

            content = output_path.read_text()
            assert "class Test001(QCAlgorithm):" in content

    def test_generate_to_file_creates_parent_dirs(self, catalog_with_strategy):
        """Test that generate_to_file creates parent directories."""
        catalog_dir, strategy_id = catalog_with_strategy

        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "nested" / "dir" / "strategy.py"

            with CodeGenerator(catalog_dir) as generator:
                generator.generate_to_file(strategy_id, output_path)

            assert output_path.exists()

    def test_generate_to_file_no_overwrite(self, catalog_with_strategy):
        """Test that generate_to_file doesn't overwrite by default."""
        catalog_dir, strategy_id = catalog_with_strategy

        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "strategy.py"
            output_path.write_text("existing content")

            with (
                CodeGenerator(catalog_dir) as generator,
                pytest.raises(FileExistsError),
            ):
                generator.generate_to_file(strategy_id, output_path)

    def test_generate_to_file_with_overwrite(self, catalog_with_strategy):
        """Test that generate_to_file can overwrite with flag."""
        catalog_dir, strategy_id = catalog_with_strategy

        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "strategy.py"
            output_path.write_text("existing content")

            with CodeGenerator(catalog_dir) as generator:
                generator.generate_to_file(strategy_id, output_path, overwrite=True)

            content = output_path.read_text()
            assert "class Test001(QCAlgorithm):" in content


class TestCodeGeneratorValidation:
    """Tests for validation methods."""

    def test_validate_valid_strategy(self, catalog_with_strategy):
        """Test validation of a valid strategy."""
        catalog_dir, strategy_id = catalog_with_strategy

        with CodeGenerator(catalog_dir) as generator:
            errors = generator.validate(strategy_id)

        # Should have no critical errors
        critical_errors = [
            e
            for e in errors
            if "Syntax error" in e
            or "Missing required import" in e
            or "Missing QCAlgorithm" in e
            or "Missing Initialize" in e
        ]
        assert len(critical_errors) == 0

    def test_validate_definition(self, temp_catalog_dir, sample_strategy):
        """Test validation of a strategy definition."""
        with CodeGenerator(temp_catalog_dir) as generator:
            errors = generator.validate_definition(sample_strategy)

        # Should have no critical errors
        critical_errors = [
            e
            for e in errors
            if "Syntax error" in e
            or "Missing required import" in e
            or "Missing QCAlgorithm" in e
            or "Missing Initialize" in e
        ]
        assert len(critical_errors) == 0


class TestCodeGeneratorCatalogIntegration:
    """Tests for catalog integration."""

    def test_lazy_catalog_initialization(self, temp_catalog_dir):
        """Test that catalog is lazily initialized."""
        generator = CodeGenerator(temp_catalog_dir)
        assert generator._catalog is None

        # Access catalog
        catalog = generator._get_catalog()
        assert generator._catalog is not None
        assert catalog is generator._catalog

        generator.close()

    def test_catalog_reuse(self, temp_catalog_dir):
        """Test that catalog is reused on multiple calls."""
        generator = CodeGenerator(temp_catalog_dir)

        catalog1 = generator._get_catalog()
        catalog2 = generator._get_catalog()

        assert catalog1 is catalog2

        generator.close()

    def test_close_clears_catalog(self, temp_catalog_dir):
        """Test that close() clears the catalog."""
        generator = CodeGenerator(temp_catalog_dir)
        generator._get_catalog()
        assert generator._catalog is not None

        generator.close()
        assert generator._catalog is None

    def test_entry_exists_but_no_definition(self, temp_catalog_dir):
        """Test error when entry exists but definition is missing."""
        # Create a strategy normally
        orphan_strategy = StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(
                id="ORPHAN-001",
                name="Orphan Strategy",
                description="Entry to have its definition deleted",
                tags=["test"],
            ),
            strategy_type="momentum_rotation",
            universe=UniverseConfig(type="fixed", symbols=["SPY"]),
            signal=SignalConfig(type="relative_momentum", lookback_days=126),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="monthly"),
        )

        catalog = CatalogManager(temp_catalog_dir)
        catalog.create_entry(orphan_strategy)
        catalog.close()

        # Delete the JSON file to simulate missing definition
        json_path = temp_catalog_dir / "strategies" / "ORPHAN-001.json"
        json_path.unlink()

        with (
            CodeGenerator(temp_catalog_dir) as generator,
            pytest.raises(CodeGenerationError, match="Strategy definition not found"),
        ):
            generator.generate("ORPHAN-001")


class TestCodeGeneratorMultipleStrategies:
    """Tests for generating multiple strategies."""

    def test_generate_multiple_strategies(self, temp_catalog_dir):
        """Test generating code for multiple strategies."""
        catalog = CatalogManager(temp_catalog_dir)

        # Create multiple strategies
        strategies = [
            StrategyDefinition(
                tier=1,
                metadata=StrategyMetadata(
                    id=f"STRAT-{i:03d}",
                    name=f"Strategy {i}",
                    description=f"Test strategy {i}",
                    tags=["test"],
                ),
                strategy_type="momentum_rotation",
                universe=UniverseConfig(
                    type="fixed",
                    symbols=["SPY", "TLT"],
                    defensive_symbols=["SHY"],
                ),
                signal=SignalConfig(
                    type="relative_momentum",
                    lookback_days=126,
                    selection_n=1,
                ),
                position_sizing=PositionSizingConfig(method="equal_weight"),
                rebalance=RebalanceConfig(frequency="monthly"),
            )
            for i in range(1, 4)
        ]

        for strat in strategies:
            catalog.create_entry(strat)

        catalog.close()

        # Generate all strategies
        # Class names are derived from ID: STRAT-001 -> Strat001
        with CodeGenerator(temp_catalog_dir) as generator:
            for strat in strategies:
                code = generator.generate(strat.metadata.id)
                # Extract the number from ID and check class name
                idx = strat.metadata.id.split("-")[1]
                assert f"class Strat{idx}(QCAlgorithm):" in code
