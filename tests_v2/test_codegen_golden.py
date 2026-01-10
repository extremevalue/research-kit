"""Golden tests for code generation stability.

Golden tests compare the current code generation output against stored "golden"
files to detect unexpected changes in generated code. If templates change
intentionally, update the golden files to match.

To update golden files after intentional template changes:
    pytest tests_v2/test_codegen_golden.py --update-golden

Or regenerate manually:
    research-codegen demo momentum_rotation --output tests_v2/fixtures/golden/codegen/momentum_rotation.py
"""

import ast
import re
from pathlib import Path

import pytest

from research_system.codegen.engine import TemplateEngine
from research_system.schemas.common import (
    PositionSizingMethod,
    RebalanceFrequency,
    SignalType,
    UniverseType,
)
from research_system.schemas.strategy import (
    PositionSizingConfig,
    RebalanceConfig,
    SignalConfig,
    StrategyDefinition,
    StrategyMetadata,
    UniverseConfig,
)

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden" / "codegen"


def load_golden_code(name: str) -> str:
    """Load a golden Python file."""
    golden_path = GOLDEN_DIR / f"{name}.py"
    return golden_path.read_text()


def save_golden_code(name: str, code: str) -> None:
    """Save code as a golden Python file."""
    golden_path = GOLDEN_DIR / f"{name}.py"
    golden_path.parent.mkdir(parents=True, exist_ok=True)
    golden_path.write_text(code)


def create_demo_momentum_strategy() -> StrategyDefinition:
    """Create the demo momentum rotation strategy (matches CLI demo command)."""
    return StrategyDefinition(
        tier=1,
        metadata=StrategyMetadata(
            id="DEMO-MOMENTUM",
            name="Demo Momentum Rotation",
            description="Demo strategy showing momentum rotation template",
            tags=["demo", "momentum"],
        ),
        strategy_type="momentum_rotation",
        universe=UniverseConfig(
            type=UniverseType.FIXED,
            symbols=["SPY", "TLT", "GLD", "VNQ"],
            defensive_symbols=["SHY", "BIL"],
        ),
        signal=SignalConfig(
            type=SignalType.RELATIVE_MOMENTUM,
            lookback_days=126,
            selection_n=2,
        ),
        position_sizing=PositionSizingConfig(
            method=PositionSizingMethod.EQUAL_WEIGHT, leverage=1.0
        ),
        rebalance=RebalanceConfig(frequency=RebalanceFrequency.MONTHLY),
    )


def create_demo_mean_reversion_strategy() -> StrategyDefinition:
    """Create the demo mean reversion strategy."""
    return StrategyDefinition(
        tier=1,
        metadata=StrategyMetadata(
            id="DEMO-MEANREV",
            name="Demo Mean Reversion",
            description="Demo strategy showing mean reversion template",
            tags=["demo", "mean_reversion"],
        ),
        strategy_type="mean_reversion",
        universe=UniverseConfig(type=UniverseType.FIXED, symbols=["SPY"]),
        signal=SignalConfig(
            type=SignalType.MEAN_REVERSION,
            lookback_days=20,
            threshold=-2.0,
        ),
        position_sizing=PositionSizingConfig(method=PositionSizingMethod.EQUAL_WEIGHT),
        rebalance=RebalanceConfig(frequency=RebalanceFrequency.DAILY),
    )


def create_demo_trend_following_strategy() -> StrategyDefinition:
    """Create the demo trend following strategy."""
    return StrategyDefinition(
        tier=1,
        metadata=StrategyMetadata(
            id="DEMO-TREND",
            name="Demo Trend Following",
            description="Demo strategy showing trend following template",
            tags=["demo", "trend"],
        ),
        strategy_type="trend_following",
        universe=UniverseConfig(
            type=UniverseType.FIXED,
            symbols=["SPY", "QQQ", "IWM"],
            defensive_symbols=["TLT"],
        ),
        signal=SignalConfig(
            type=SignalType.TREND_FOLLOWING,
            lookback_days=200,
            threshold=0.0,
        ),
        position_sizing=PositionSizingConfig(method=PositionSizingMethod.EQUAL_WEIGHT),
        rebalance=RebalanceConfig(frequency=RebalanceFrequency.WEEKLY),
    )


def create_demo_dual_momentum_strategy() -> StrategyDefinition:
    """Create the demo dual momentum strategy."""
    return StrategyDefinition(
        tier=1,
        metadata=StrategyMetadata(
            id="DEMO-DUALMOM",
            name="Demo Dual Momentum",
            description="Demo strategy showing dual momentum template",
            tags=["demo", "momentum"],
        ),
        strategy_type="dual_momentum",
        universe=UniverseConfig(
            type=UniverseType.FIXED,
            symbols=["SPY", "EFA", "EEM"],
            defensive_symbols=["AGG"],
        ),
        signal=SignalConfig(
            type=SignalType.ABSOLUTE_MOMENTUM,
            lookback_days=252,
            selection_n=1,
            threshold=0.0,
        ),
        position_sizing=PositionSizingConfig(method=PositionSizingMethod.EQUAL_WEIGHT),
        rebalance=RebalanceConfig(frequency=RebalanceFrequency.MONTHLY),
    )


def create_demo_breakout_strategy() -> StrategyDefinition:
    """Create the demo breakout strategy."""
    return StrategyDefinition(
        tier=1,
        metadata=StrategyMetadata(
            id="DEMO-BREAKOUT",
            name="Demo Breakout",
            description="Demo strategy showing breakout template",
            tags=["demo", "breakout"],
        ),
        strategy_type="breakout",
        universe=UniverseConfig(type=UniverseType.FIXED, symbols=["SPY"]),
        signal=SignalConfig(
            type=SignalType.BREAKOUT,
            lookback_days=20,
            threshold=0.05,  # 5% trailing stop
        ),
        position_sizing=PositionSizingConfig(method=PositionSizingMethod.EQUAL_WEIGHT),
        rebalance=RebalanceConfig(frequency=RebalanceFrequency.DAILY),
    )


class TestCodegenGolden:
    """Golden tests for code generation output."""

    @pytest.fixture
    def engine(self):
        """Create a template engine."""
        return TemplateEngine()

    def test_momentum_rotation_matches_golden(self, engine):
        """Test that momentum rotation code generation is stable."""
        strategy = create_demo_momentum_strategy()
        generated = engine.render(strategy)
        golden = load_golden_code("momentum_rotation")

        assert generated == golden, (
            "Generated momentum_rotation code differs from golden file. "
            "If the change is intentional, regenerate the golden file:\n"
            "  research-codegen demo momentum_rotation "
            "--output tests_v2/fixtures/golden/codegen/momentum_rotation.py"
        )

    def test_mean_reversion_matches_golden(self, engine):
        """Test that mean reversion code generation is stable."""
        strategy = create_demo_mean_reversion_strategy()
        generated = engine.render(strategy)
        golden = load_golden_code("mean_reversion")

        assert generated == golden, (
            "Generated mean_reversion code differs from golden file. "
            "If the change is intentional, regenerate the golden file:\n"
            "  research-codegen demo mean_reversion "
            "--output tests_v2/fixtures/golden/codegen/mean_reversion.py"
        )

    def test_trend_following_matches_golden(self, engine):
        """Test that trend following code generation is stable."""
        strategy = create_demo_trend_following_strategy()
        generated = engine.render(strategy)
        golden = load_golden_code("trend_following")

        assert generated == golden, (
            "Generated trend_following code differs from golden file. "
            "If the change is intentional, regenerate the golden file:\n"
            "  research-codegen demo trend_following "
            "--output tests_v2/fixtures/golden/codegen/trend_following.py"
        )

    def test_dual_momentum_matches_golden(self, engine):
        """Test that dual momentum code generation is stable."""
        strategy = create_demo_dual_momentum_strategy()
        generated = engine.render(strategy)
        golden = load_golden_code("dual_momentum")

        assert generated == golden, (
            "Generated dual_momentum code differs from golden file. "
            "If the change is intentional, regenerate the golden file:\n"
            "  research-codegen demo dual_momentum "
            "--output tests_v2/fixtures/golden/codegen/dual_momentum.py"
        )

    def test_breakout_matches_golden(self, engine):
        """Test that breakout code generation is stable."""
        strategy = create_demo_breakout_strategy()
        generated = engine.render(strategy)
        golden = load_golden_code("breakout")

        assert generated == golden, (
            "Generated breakout code differs from golden file. "
            "If the change is intentional, regenerate the golden file:\n"
            "  research-codegen demo breakout "
            "--output tests_v2/fixtures/golden/codegen/breakout.py"
        )


class TestCodegenValidation:
    """Validation tests for generated code quality."""

    @pytest.fixture
    def engine(self):
        """Create a template engine."""
        return TemplateEngine()

    @pytest.fixture
    def all_strategies(self):
        """Return all demo strategies."""
        return [
            create_demo_momentum_strategy(),
            create_demo_mean_reversion_strategy(),
            create_demo_trend_following_strategy(),
            create_demo_dual_momentum_strategy(),
            create_demo_breakout_strategy(),
        ]

    def test_generated_code_is_valid_python(self, engine, all_strategies):
        """Test that all generated code is syntactically valid Python."""
        for strategy in all_strategies:
            code = engine.render(strategy)
            try:
                ast.parse(code)
            except SyntaxError as e:
                pytest.fail(
                    f"Strategy {strategy.metadata.id} generated invalid Python: {e}"
                )

    def test_no_hardcoded_dates_in_generated_code(self, engine, all_strategies):
        """Test that generated code has no hardcoded dates.

        This is critical for walk-forward validation to work correctly.
        Dates should only be set by the framework, not in strategy code.
        """
        date_patterns = [
            (r"SetStartDate\s*\(", "SetStartDate call"),
            (r"SetEndDate\s*\(", "SetEndDate call"),
            (r"\b20[0-2][0-9]\s*,\s*[1-9]|1[0-2]\s*,\s*[1-3]?[0-9]\b", "Date literal"),
        ]

        for strategy in all_strategies:
            code = engine.render(strategy)
            for pattern, description in date_patterns:
                matches = re.findall(pattern, code)
                if matches:
                    pytest.fail(
                        f"Strategy {strategy.metadata.id} contains hardcoded date "
                        f"({description}): {matches}"
                    )

    def test_required_imports_present(self, engine, all_strategies):
        """Test that generated code has required imports."""
        for strategy in all_strategies:
            code = engine.render(strategy)
            assert "from AlgorithmImports import" in code, (
                f"Strategy {strategy.metadata.id} missing AlgorithmImports"
            )

    def test_class_structure_correct(self, engine, all_strategies):
        """Test that generated code has correct class structure."""
        for strategy in all_strategies:
            code = engine.render(strategy)
            assert "(QCAlgorithm)" in code, (
                f"Strategy {strategy.metadata.id} doesn't inherit from QCAlgorithm"
            )
            assert "def Initialize(self)" in code, (
                f"Strategy {strategy.metadata.id} missing Initialize method"
            )

    def test_warmup_period_set(self, engine, all_strategies):
        """Test that generated code sets warmup period."""
        for strategy in all_strategies:
            code = engine.render(strategy)
            assert "SetWarmUp" in code, (
                f"Strategy {strategy.metadata.id} missing SetWarmUp call"
            )

    def test_no_hardcoded_capital(self, engine, all_strategies):
        """Test that SetCash has a comment about framework override.

        The capital amount should be noted as overridable by framework.
        """
        for strategy in all_strategies:
            code = engine.render(strategy)
            # Check that SetCash is accompanied by a comment about framework override
            lines = code.split("\n")
            set_cash_found = False
            for i, line in enumerate(lines):
                if "SetCash" in line:
                    set_cash_found = True
                    # Check surrounding lines for framework comment
                    context = "\n".join(lines[max(0, i - 2) : i + 2])
                    assert "framework" in context.lower() or "override" in context.lower(), (
                        f"Strategy {strategy.metadata.id} has SetCash without "
                        "framework override comment"
                    )
            assert set_cash_found, f"Strategy {strategy.metadata.id} missing SetCash"


class TestCodegenDeterminism:
    """Tests for deterministic code generation."""

    @pytest.fixture
    def engine(self):
        """Create a template engine."""
        return TemplateEngine()

    def test_same_strategy_generates_identical_code(self, engine):
        """Test that rendering the same strategy twice produces identical code."""
        strategy = create_demo_momentum_strategy()

        code1 = engine.render(strategy)
        code2 = engine.render(strategy)

        assert code1 == code2, "Same strategy should generate identical code"

    def test_equivalent_strategies_generate_identical_code(self, engine):
        """Test that equivalent strategy definitions generate identical code."""
        strategy1 = create_demo_momentum_strategy()
        strategy2 = create_demo_momentum_strategy()

        code1 = engine.render(strategy1)
        code2 = engine.render(strategy2)

        assert code1 == code2, "Equivalent strategies should generate identical code"

    def test_different_ids_generate_different_class_names(self, engine):
        """Test that different strategy IDs result in different class names."""
        strategy1 = create_demo_momentum_strategy()
        strategy2 = create_demo_momentum_strategy()
        strategy2.metadata.id = "DIFFERENT-ID"

        code1 = engine.render(strategy1)
        code2 = engine.render(strategy2)

        assert "DemoMomentum" in code1
        assert "DifferentId" in code2
        assert code1 != code2
