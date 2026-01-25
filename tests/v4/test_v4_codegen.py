"""Tests for V4 code generation.

This module tests:
1. Template selection for different strategy types
2. Code generation produces valid Python
3. LLM fallback for complex strategies
4. QC API fixes applied correctly
"""

import pytest

from research_system.codegen.v4_generator import (
    V4CodeGenerator,
    V4CodeGenResult,
    generate_v4_code,
)
from research_system.codegen.templates.v4 import (
    get_template_for_v4_strategy,
    V4_STRATEGY_TO_TEMPLATE,
)


# =============================================================================
# TEST TEMPLATE SELECTION
# =============================================================================


class TestTemplateSelection:
    """Test template selection for different strategy types."""

    def test_momentum_strategies_select_momentum_template(self):
        """Test that momentum strategies select momentum.py.j2."""
        momentum_types = ["momentum", "momentum_rotation", "relative_momentum", "dual_momentum"]
        for strategy_type in momentum_types:
            template = get_template_for_v4_strategy(strategy_type)
            assert template == "momentum.py.j2", f"{strategy_type} should use momentum.py.j2"

    def test_mean_reversion_strategies_select_correct_template(self):
        """Test that mean reversion strategies select mean_reversion.py.j2."""
        mr_types = ["mean_reversion", "mean-reversion", "zscore"]
        for strategy_type in mr_types:
            template = get_template_for_v4_strategy(strategy_type)
            assert template == "mean_reversion.py.j2", f"{strategy_type} should use mean_reversion.py.j2"

    def test_regime_strategies_select_regime_template(self):
        """Test that regime strategies select regime_adaptive.py.j2."""
        regime_types = ["regime_adaptive", "regime-adaptive", "regime_switching", "tactical_allocation"]
        for strategy_type in regime_types:
            template = get_template_for_v4_strategy(strategy_type)
            assert template == "regime_adaptive.py.j2", f"{strategy_type} should use regime_adaptive.py.j2"

    def test_unknown_strategy_type_returns_base(self):
        """Test that unknown strategy types return base.py.j2."""
        template = get_template_for_v4_strategy("unknown_strategy")
        assert template == "base.py.j2"

    def test_signal_type_fallback(self):
        """Test signal_type is used as fallback when strategy_type doesn't match."""
        template = get_template_for_v4_strategy(
            strategy_type="custom",
            signal_type="momentum"
        )
        assert template == "momentum.py.j2"


# =============================================================================
# TEST CODE GENERATION
# =============================================================================


class TestCodeGeneration:
    """Test code generation produces valid Python."""

    @pytest.fixture
    def generator(self):
        """Create a code generator without LLM client."""
        return V4CodeGenerator(llm_client=None)

    @pytest.fixture
    def momentum_strategy(self):
        """Sample momentum strategy document."""
        return {
            "id": "STRAT-001",
            "name": "Test Momentum Strategy",
            "description": "A test momentum strategy",
            "strategy_type": "momentum",
            "signal_type": "relative_momentum",
            "universe": ["SPY", "QQQ", "IWM", "EFA", "EEM"],
            "parameters": {
                "lookback_period": 126,
                "top_n": 3,
                "rebalance_frequency": "monthly",
                "leverage": 1.0,
            },
        }

    @pytest.fixture
    def mean_reversion_strategy(self):
        """Sample mean reversion strategy document."""
        return {
            "id": "STRAT-002",
            "name": "Test Mean Reversion Strategy",
            "description": "A test mean reversion strategy",
            "strategy_type": "mean_reversion",
            "universe": ["SPY"],
            "parameters": {
                "lookback_period": 20,
                "entry_threshold": -2.0,
                "exit_threshold": 0.0,
                "leverage": 1.0,
            },
        }

    def test_momentum_strategy_generates_valid_code(self, generator, momentum_strategy):
        """Test momentum strategy generates valid Python code."""
        result = generator.generate(momentum_strategy)

        assert result.success
        assert result.code is not None
        assert result.method == "template"
        assert result.template_used == "momentum.py.j2"

        # Check code structure
        assert "class Strat001Algorithm(QCAlgorithm):" in result.code
        assert "def initialize(self):" in result.code
        assert "def rebalance(self):" in result.code

    def test_mean_reversion_strategy_generates_valid_code(self, generator, mean_reversion_strategy):
        """Test mean reversion strategy generates valid Python code."""
        result = generator.generate(mean_reversion_strategy)

        assert result.success
        assert result.code is not None
        assert result.method == "template"
        assert result.template_used == "mean_reversion.py.j2"

        # Check code structure
        assert "class Strat002Algorithm(QCAlgorithm):" in result.code
        assert "def calculate_zscore(self" in result.code

    def test_generated_code_has_imports(self, generator, momentum_strategy):
        """Test generated code includes necessary imports."""
        result = generator.generate(momentum_strategy)

        assert result.success
        assert "from AlgorithmImports import *" in result.code

    def test_generated_code_has_no_hardcoded_dates(self, generator, momentum_strategy):
        """Test generated code doesn't have hardcoded dates in set_start_date."""
        result = generator.generate(momentum_strategy)

        assert result.success
        # There should be no set_start_date with specific years in template output
        assert "set_start_date(2020" not in result.code
        assert "set_start_date(2021" not in result.code

    def test_strategy_without_params_doesnt_match_template(self, generator):
        """Test strategy without parameters doesn't match template."""
        strategy = {
            "id": "STRAT-003",
            "name": "No Params Strategy",
            "strategy_type": "momentum",
            "parameters": {},  # Empty params
        }

        # Should not match template (parameters required)
        assert not generator._matches_template(strategy)


# =============================================================================
# TEST QC API FIXES
# =============================================================================


class TestQCAPIFixes:
    """Test that QC API fixes are applied correctly."""

    @pytest.fixture
    def generator(self):
        return V4CodeGenerator(llm_client=None)

    def test_fixes_resolution_case(self, generator):
        """Test Resolution enum is fixed to uppercase."""
        code = "self.add_equity('SPY', Resolution.daily)"
        fixed = generator._fix_qc_api_issues(code)
        assert "Resolution.DAILY" in fixed
        assert "Resolution.daily" not in fixed

    def test_fixes_pascal_case_methods(self, generator):
        """Test PascalCase methods are converted to snake_case."""
        code = """
class Test(QCAlgorithm):
    def Initialize(self):
        self.SetCash(100000)
        self.SetBenchmark("SPY")
        self.AddEquity("SPY", Resolution.DAILY)
"""
        fixed = generator._fix_qc_api_issues(code)
        assert "set_cash(100000)" in fixed
        assert "set_benchmark" in fixed
        assert "add_equity" in fixed

    def test_adds_import_if_missing(self, generator):
        """Test AlgorithmImports import is added if missing."""
        code = """class Test(QCAlgorithm):
    def initialize(self):
        pass
"""
        fixed = generator._fix_qc_api_issues(code)
        assert "from AlgorithmImports import *" in fixed

    def test_preserves_import_if_present(self, generator):
        """Test import is not duplicated if already present."""
        code = """from AlgorithmImports import *

class Test(QCAlgorithm):
    pass
"""
        fixed = generator._fix_qc_api_issues(code)
        # Should only have one import statement
        assert fixed.count("from AlgorithmImports import *") == 1


# =============================================================================
# TEST CONVENIENCE FUNCTION
# =============================================================================


class TestConvenienceFunction:
    """Test generate_v4_code convenience function."""

    def test_generate_v4_code_works(self):
        """Test the convenience function works."""
        strategy = {
            "id": "STRAT-TEST",
            "name": "Test",
            "strategy_type": "momentum",
            "parameters": {"lookback_period": 126, "top_n": 3},
        }

        result = generate_v4_code(strategy)
        assert isinstance(result, V4CodeGenResult)
        assert result.success
