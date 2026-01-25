"""Tests for V4 options income strategy template.

This module tests:
1. Template selection for options strategy types
2. Code generation for each sub-type (cash_secured_put, put_credit_spread, covered_call)
3. DataNormalizationMode.RAW is present
4. PascalCase option filter methods are used correctly
"""

import pytest

from research_system.codegen.v4_generator import V4CodeGenerator
from research_system.codegen.templates.v4 import get_template_for_v4_strategy


# =============================================================================
# TEST TEMPLATE SELECTION
# =============================================================================


class TestOptionsTemplateSelection:
    """Test template selection for options strategy types."""

    def test_options_income_selects_template(self):
        """Test options_income strategy type selects options_income.py.j2."""
        template = get_template_for_v4_strategy("options_income")
        assert template == "options_income.py.j2"

    def test_options_income_hyphenated_selects_template(self):
        """Test options-income (hyphenated) selects template."""
        template = get_template_for_v4_strategy("options-income")
        assert template == "options_income.py.j2"

    def test_cash_secured_put_selects_template(self):
        """Test cash_secured_put strategy type selects options_income.py.j2."""
        template = get_template_for_v4_strategy("cash_secured_put")
        assert template == "options_income.py.j2"

    def test_put_credit_spread_selects_template(self):
        """Test put_credit_spread strategy type selects options_income.py.j2."""
        template = get_template_for_v4_strategy("put_credit_spread")
        assert template == "options_income.py.j2"

    def test_covered_call_selects_template(self):
        """Test covered_call strategy type selects options_income.py.j2."""
        template = get_template_for_v4_strategy("covered_call")
        assert template == "options_income.py.j2"

    def test_generic_options_selects_template(self):
        """Test generic 'options' strategy type selects options_income.py.j2."""
        template = get_template_for_v4_strategy("options")
        assert template == "options_income.py.j2"


# =============================================================================
# TEST CODE GENERATION
# =============================================================================


class TestOptionsCodeGeneration:
    """Test options income code generation."""

    @pytest.fixture
    def generator(self):
        """Create a code generator without LLM client."""
        return V4CodeGenerator(llm_client=None)

    @pytest.fixture
    def cash_secured_put_strategy(self):
        """Sample cash-secured put strategy document."""
        return {
            "id": "STRAT-OPT-001",
            "name": "SPY Cash Secured Puts",
            "description": "Sell cash-secured puts on SPY for income",
            "strategy_type": "options_income",
            "parameters": {
                "sub_type": "cash_secured_put",
                "underlying": "SPY",
                "target_delta": 0.30,
                "min_dte": 30,
                "max_dte": 45,
                "min_premium": 1.00,
                "profit_target": 0.50,
                "initial_capital": 100000,
            },
        }

    @pytest.fixture
    def put_credit_spread_strategy(self):
        """Sample put credit spread strategy document."""
        return {
            "id": "STRAT-OPT-002",
            "name": "SPY Put Credit Spreads",
            "description": "Bull put spreads on SPY for defined-risk income",
            "strategy_type": "options_income",
            "parameters": {
                "sub_type": "put_credit_spread",
                "underlying": "SPY",
                "target_delta": 0.25,
                "spread_width": 5,
                "min_dte": 30,
                "max_dte": 45,
                "min_premium": 0.75,
                "initial_capital": 50000,
            },
        }

    @pytest.fixture
    def covered_call_strategy(self):
        """Sample covered call strategy document."""
        return {
            "id": "STRAT-OPT-003",
            "name": "SPY Covered Calls",
            "description": "Covered calls on SPY for income",
            "strategy_type": "options_income",
            "parameters": {
                "sub_type": "covered_call",
                "underlying": "SPY",
                "target_delta": 0.30,
                "min_dte": 14,
                "max_dte": 30,
                "min_premium": 0.50,
                "initial_capital": 100000,
            },
        }

    def test_cash_secured_put_generates_valid_code(self, generator, cash_secured_put_strategy):
        """Test cash-secured put strategy generates valid Python code."""
        result = generator.generate(cash_secured_put_strategy)

        assert result.success
        assert result.code is not None
        assert result.method == "template"
        assert result.template_used == "options_income.py.j2"

        # Check class name
        assert "class StratOpt001Algorithm(QCAlgorithm):" in result.code

        # Check strategy-specific method
        assert "_open_cash_secured_put" in result.code

    def test_put_credit_spread_generates_valid_code(self, generator, put_credit_spread_strategy):
        """Test put credit spread strategy generates valid Python code."""
        result = generator.generate(put_credit_spread_strategy)

        assert result.success
        assert result.code is not None
        assert result.method == "template"

        # Check class name
        assert "class StratOpt002Algorithm(QCAlgorithm):" in result.code

        # Check strategy-specific method
        assert "_open_put_credit_spread" in result.code

        # Check spread width parameter
        assert "spread_width" in result.code.lower() or "_spread_width" in result.code

    def test_covered_call_generates_valid_code(self, generator, covered_call_strategy):
        """Test covered call strategy generates valid Python code."""
        result = generator.generate(covered_call_strategy)

        assert result.success
        assert result.code is not None
        assert result.method == "template"

        # Check class name
        assert "class StratOpt003Algorithm(QCAlgorithm):" in result.code

        # Check strategy-specific method
        assert "_open_covered_call" in result.code


# =============================================================================
# TEST REQUIRED OPTIONS COMPONENTS
# =============================================================================


class TestOptionsRequiredComponents:
    """Test that generated options code has required components."""

    @pytest.fixture
    def generator(self):
        return V4CodeGenerator(llm_client=None)

    @pytest.fixture
    def options_strategy(self):
        """Basic options strategy for testing required components."""
        return {
            "id": "STRAT-OPT-TEST",
            "name": "Test Options Strategy",
            "strategy_type": "options_income",
            "parameters": {
                "sub_type": "cash_secured_put",
                "underlying": "SPY",
            },
        }

    def test_has_data_normalization_mode_raw(self, generator, options_strategy):
        """Test that DataNormalizationMode.RAW is set on underlying equity."""
        result = generator.generate(options_strategy)

        assert result.success
        assert "DataNormalizationMode.RAW" in result.code

    def test_has_set_data_normalization_mode_call(self, generator, options_strategy):
        """Test that set_data_normalization_mode is called."""
        result = generator.generate(options_strategy)

        assert result.success
        assert "set_data_normalization_mode" in result.code

    def test_has_add_equity_for_underlying(self, generator, options_strategy):
        """Test that add_equity is called for the underlying."""
        result = generator.generate(options_strategy)

        assert result.success
        assert "add_equity" in result.code

    def test_has_add_option_call(self, generator, options_strategy):
        """Test that add_option is called."""
        result = generator.generate(options_strategy)

        assert result.success
        assert "add_option" in result.code

    def test_has_include_weeklys_pascal_case(self, generator, options_strategy):
        """Test that IncludeWeeklys uses PascalCase (not include_weeklys)."""
        result = generator.generate(options_strategy)

        assert result.success
        assert "IncludeWeeklys()" in result.code
        assert "include_weeklys" not in result.code.lower().replace("includeweeklys", "")

    def test_has_strikes_pascal_case(self, generator, options_strategy):
        """Test that Strikes uses PascalCase."""
        result = generator.generate(options_strategy)

        assert result.success
        assert ".Strikes(" in result.code

    def test_has_expiration_pascal_case(self, generator, options_strategy):
        """Test that Expiration uses PascalCase."""
        result = generator.generate(options_strategy)

        assert result.success
        assert ".Expiration(" in result.code

    def test_has_algorithm_imports(self, generator, options_strategy):
        """Test that AlgorithmImports is imported."""
        result = generator.generate(options_strategy)

        assert result.success
        assert "from AlgorithmImports import *" in result.code

    def test_has_initialize_method(self, generator, options_strategy):
        """Test that initialize method is defined."""
        result = generator.generate(options_strategy)

        assert result.success
        assert "def initialize(self):" in result.code

    def test_has_option_chain_usage(self, generator, options_strategy):
        """Test that option_chain is used."""
        result = generator.generate(options_strategy)

        assert result.success
        assert "option_chain" in result.code


# =============================================================================
# TEST PARAMETER HANDLING
# =============================================================================


class TestOptionsParameterHandling:
    """Test that options template handles parameters correctly."""

    @pytest.fixture
    def generator(self):
        return V4CodeGenerator(llm_client=None)

    def test_custom_underlying(self, generator):
        """Test custom underlying symbol is used."""
        strategy = {
            "id": "STRAT-QQQ",
            "name": "QQQ Options",
            "strategy_type": "options_income",
            "parameters": {
                "sub_type": "cash_secured_put",
                "underlying": "QQQ",
            },
        }
        result = generator.generate(strategy)

        assert result.success
        assert '"QQQ"' in result.code

    def test_custom_delta(self, generator):
        """Test custom target delta is used."""
        strategy = {
            "id": "STRAT-DELTA",
            "name": "Custom Delta",
            "strategy_type": "options_income",
            "parameters": {
                "sub_type": "cash_secured_put",
                "target_delta": 0.15,
            },
        }
        result = generator.generate(strategy)

        assert result.success
        assert "0.15" in result.code

    def test_custom_dte_range(self, generator):
        """Test custom DTE range is used in filter."""
        strategy = {
            "id": "STRAT-DTE",
            "name": "Custom DTE",
            "strategy_type": "options_income",
            "parameters": {
                "sub_type": "cash_secured_put",
                "min_dte": 14,
                "max_dte": 21,
            },
        }
        result = generator.generate(strategy)

        assert result.success
        assert ".Expiration(14, 21)" in result.code

    def test_default_values_used(self, generator):
        """Test that defaults are used when parameters not specified."""
        strategy = {
            "id": "STRAT-DEFAULTS",
            "name": "Default Values",
            "strategy_type": "options_income",
            "parameters": {
                "sub_type": "cash_secured_put",
            },
        }
        result = generator.generate(strategy)

        assert result.success
        # Default underlying is SPY
        assert '"SPY"' in result.code
        # Default delta is 0.30
        assert "0.30" in result.code or "0.3" in result.code
