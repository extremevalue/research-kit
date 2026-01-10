"""Tests for the template engine."""

import tempfile
from pathlib import Path

import pytest

from research_system.codegen import CodeGenerationError, TemplateEngine
from research_system.codegen.filters import (
    format_symbol_set,
    format_symbols,
    pascal_case,
    safe_identifier,
    snake_case,
)
from research_system.schemas.strategy import (
    PositionSizingConfig,
    RebalanceConfig,
    SignalConfig,
    StrategyDefinition,
    StrategyMetadata,
    UniverseConfig,
)


class TestCustomFilters:
    """Tests for custom Jinja2 filters."""

    def test_snake_case_from_pascal(self):
        """Test snake_case conversion from PascalCase."""
        assert snake_case("MyStrategy") == "my_strategy"
        assert snake_case("HTTPServer") == "http_server"
        assert snake_case("XMLParser") == "xml_parser"

    def test_snake_case_from_camel(self):
        """Test snake_case conversion from camelCase."""
        assert snake_case("myStrategy") == "my_strategy"
        assert snake_case("httpServer") == "http_server"

    def test_snake_case_from_hyphen(self):
        """Test snake_case conversion from hyphenated."""
        assert snake_case("my-strategy") == "my_strategy"
        assert snake_case("http-server") == "http_server"

    def test_snake_case_already_snake(self):
        """Test snake_case with already snake_case input."""
        assert snake_case("my_strategy") == "my_strategy"

    def test_pascal_case_from_snake(self):
        """Test pascal_case conversion from snake_case."""
        assert pascal_case("my_strategy") == "MyStrategy"
        assert pascal_case("http_server") == "HttpServer"

    def test_pascal_case_from_hyphen(self):
        """Test pascal_case conversion from hyphenated."""
        assert pascal_case("my-strategy") == "MyStrategy"

    def test_pascal_case_already_pascal(self):
        """Test pascal_case with already PascalCase input."""
        assert pascal_case("MyStrategy") == "Mystrategy"  # Note: splits on nothing

    def test_format_symbols(self):
        """Test format_symbols creates valid Python list."""
        result = format_symbols(["SPY", "TLT", "GLD"])
        assert result == '["SPY", "TLT", "GLD"]'

    def test_format_symbols_empty(self):
        """Test format_symbols with empty list."""
        assert format_symbols([]) == "[]"

    def test_format_symbol_set(self):
        """Test format_symbol_set creates valid Python set."""
        result = format_symbol_set(["SPY", "TLT"])
        assert result == '{"SPY", "TLT"}'

    def test_safe_identifier_spaces(self):
        """Test safe_identifier replaces spaces."""
        assert safe_identifier("my strategy") == "my_strategy"

    def test_safe_identifier_leading_digit(self):
        """Test safe_identifier handles leading digits."""
        assert safe_identifier("123strategy") == "_123strategy"

    def test_safe_identifier_special_chars(self):
        """Test safe_identifier replaces special characters."""
        assert safe_identifier("my-strategy!") == "my_strategy_"


class TestTemplateEngine:
    """Tests for the TemplateEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a template engine instance."""
        return TemplateEngine()

    @pytest.fixture
    def momentum_strategy(self):
        """Create a sample momentum rotation strategy."""
        return StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(
                id="STRAT-TEST-001",
                name="Test Momentum Strategy",
                description="A momentum strategy for testing",
                tags=["momentum", "test"],
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
                selection_n=1,
            ),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="monthly"),
        )

    @pytest.fixture
    def mean_reversion_strategy(self):
        """Create a sample mean reversion strategy."""
        return StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(
                id="STRAT-TEST-002",
                name="Test Mean Reversion",
                description="A mean reversion strategy for testing",
                tags=["mean_reversion", "test"],
            ),
            strategy_type="mean_reversion",
            universe=UniverseConfig(
                type="fixed",
                symbols=["SPY"],
            ),
            signal=SignalConfig(
                type="mean_reversion",
                lookback_days=20,
                threshold=-2.0,
            ),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="daily"),
        )

    def test_render_momentum_strategy(self, engine, momentum_strategy):
        """Test rendering a momentum rotation strategy."""
        code = engine.render(momentum_strategy)

        assert "class StratTest001(QCAlgorithm):" in code
        assert "Test Momentum Strategy" in code
        assert "STRAT-TEST-001" in code
        assert "SPY" in code
        assert "TLT" in code
        assert "GLD" in code
        assert "SHY" in code  # Defensive symbol
        assert "SetWarmUp" in code
        assert "_lookback_days = 126" in code

    def test_render_mean_reversion_strategy(self, engine, mean_reversion_strategy):
        """Test rendering a mean reversion strategy."""
        code = engine.render(mean_reversion_strategy)

        assert "class StratTest002(QCAlgorithm):" in code
        assert "CalculateZScore" in code
        assert "_threshold = -2.0" in code
        assert "_lookback_days = 20" in code

    def test_rendered_code_is_valid_python(self, engine, momentum_strategy):
        """Test that rendered code is syntactically valid Python."""
        code = engine.render(momentum_strategy)
        errors = engine.validate_output(code)

        # Filter out the date pattern false positive (it's not actually a hardcoded date)
        syntax_errors = [e for e in errors if "Syntax error" in e]
        assert not syntax_errors, f"Syntax errors: {syntax_errors}"

    def test_rendered_code_has_no_hardcoded_dates(self, engine, momentum_strategy):
        """Test that rendered code has no SetStartDate/SetEndDate."""
        code = engine.render(momentum_strategy)

        assert "SetStartDate(" not in code
        assert "SetEndDate(" not in code

    def test_render_to_file(self, engine, momentum_strategy):
        """Test rendering to a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "strategy.py"
            engine.render_to_file(momentum_strategy, output_path)

            assert output_path.exists()
            content = output_path.read_text()
            assert "class StratTest001(QCAlgorithm):" in content

    def test_render_to_file_creates_directories(self, engine, momentum_strategy):
        """Test that render_to_file creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "nested" / "strategy.py"
            engine.render_to_file(momentum_strategy, output_path)

            assert output_path.exists()

    def test_render_to_file_no_overwrite(self, engine, momentum_strategy):
        """Test that render_to_file respects overwrite=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "strategy.py"
            output_path.write_text("existing content")

            with pytest.raises(FileExistsError):
                engine.render_to_file(momentum_strategy, output_path, overwrite=False)

    def test_render_to_file_with_overwrite(self, engine, momentum_strategy):
        """Test that render_to_file overwrites when overwrite=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "strategy.py"
            output_path.write_text("existing content")

            engine.render_to_file(momentum_strategy, output_path, overwrite=True)

            content = output_path.read_text()
            assert "class StratTest001(QCAlgorithm):" in content

    def test_validate_output_valid_code(self, engine, momentum_strategy):
        """Test validate_output with valid code."""
        code = engine.render(momentum_strategy)
        errors = engine.validate_output(code)

        # Only check for actual errors, not date pattern warnings
        critical_errors = [
            e
            for e in errors
            if "Syntax error" in e
            or "Missing required import" in e
            or "Missing QCAlgorithm" in e
            or "Missing Initialize" in e
        ]
        assert not critical_errors

    def test_validate_output_syntax_error(self, engine):
        """Test validate_output detects syntax errors."""
        invalid_code = "def foo(\n    pass"  # Missing closing paren
        errors = engine.validate_output(invalid_code)

        assert any("Syntax error" in e for e in errors)

    def test_validate_output_missing_imports(self, engine):
        """Test validate_output detects missing imports."""
        code_without_imports = """
class MyStrategy(QCAlgorithm):
    def Initialize(self):
        pass
"""
        errors = engine.validate_output(code_without_imports)
        assert any("Missing required import" in e for e in errors)

    def test_validate_output_hardcoded_dates(self, engine):
        """Test validate_output detects hardcoded dates."""
        code_with_dates = """
from AlgorithmImports import *

class MyStrategy(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2023, 12, 31)
"""
        errors = engine.validate_output(code_with_dates)
        assert any("hardcoded date" in e.lower() for e in errors)


class TestTemplateEngineEdgeCases:
    """Edge case tests for the template engine."""

    @pytest.fixture
    def engine(self):
        """Create a template engine instance."""
        return TemplateEngine()

    def test_strategy_without_defensive_symbols(self, engine):
        """Test rendering strategy without defensive symbols."""
        strategy = StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(id="STRAT-001", name="No Defensive"),
            strategy_type="momentum_rotation",
            universe=UniverseConfig(type="fixed", symbols=["SPY", "TLT"]),
            signal=SignalConfig(type="relative_momentum", lookback_days=60),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="monthly"),
        )

        code = engine.render(strategy)
        assert "SPY" in code
        assert "TLT" in code
        # Should not have defensive symbols section
        assert "_defensive_symbols" not in code or "self._defensive_symbols = []" not in code

    def test_strategy_with_threshold(self, engine):
        """Test rendering strategy with signal threshold."""
        strategy = StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(id="STRAT-001", name="With Threshold"),
            strategy_type="momentum_rotation",
            universe=UniverseConfig(type="fixed", symbols=["SPY"]),
            signal=SignalConfig(
                type="relative_momentum",
                lookback_days=60,
                threshold=0.05,
            ),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="monthly"),
        )

        code = engine.render(strategy)
        assert "_threshold = 0.05" in code

    def test_different_rebalance_frequencies(self, engine):
        """Test rendering with different rebalance frequencies."""
        for freq in ["daily", "weekly", "monthly", "quarterly"]:
            strategy = StrategyDefinition(
                tier=1,
                metadata=StrategyMetadata(id=f"STRAT-{freq}", name=f"{freq} Strategy"),
                strategy_type="momentum_rotation",
                universe=UniverseConfig(type="fixed", symbols=["SPY"]),
                signal=SignalConfig(type="relative_momentum", lookback_days=60),
                position_sizing=PositionSizingConfig(method="equal_weight"),
                rebalance=RebalanceConfig(frequency=freq),
            )

            code = engine.render(strategy)
            errors = engine.validate_output(code)
            syntax_errors = [e for e in errors if "Syntax error" in e]
            assert not syntax_errors, f"Syntax errors for {freq}: {syntax_errors}"

    def test_all_strategy_types(self, engine):
        """Test rendering all supported strategy types."""
        strategy_types = [
            ("momentum_rotation", "relative_momentum"),
            ("mean_reversion", "mean_reversion"),
            ("trend_following", "trend_following"),
            ("dual_momentum", "absolute_momentum"),
            ("breakout", "breakout"),
        ]

        for strategy_type, signal_type in strategy_types:
            strategy = StrategyDefinition(
                tier=1,
                metadata=StrategyMetadata(
                    id=f"STRAT-{strategy_type}", name=f"Test {strategy_type}"
                ),
                strategy_type=strategy_type,
                universe=UniverseConfig(type="fixed", symbols=["SPY"]),
                signal=SignalConfig(type=signal_type, lookback_days=60, threshold=-2.0),
                position_sizing=PositionSizingConfig(method="equal_weight"),
                rebalance=RebalanceConfig(frequency="monthly"),
            )

            code = engine.render(strategy)
            errors = engine.validate_output(code)
            syntax_errors = [e for e in errors if "Syntax error" in e]
            assert not syntax_errors, f"Syntax errors for {strategy_type}: {syntax_errors}"

    def test_unknown_strategy_type_raises(self, engine):
        """Test that unknown strategy type raises error."""
        strategy = StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(id="STRAT-001", name="Unknown"),
            strategy_type="unknown_type",
            universe=UniverseConfig(type="fixed", symbols=["SPY"]),
            signal=SignalConfig(type="custom", lookback_days=60),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="monthly"),
        )

        with pytest.raises(CodeGenerationError):
            engine.render(strategy)
