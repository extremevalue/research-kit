"""Tests for template structure and configuration."""

import pytest
from jinja2 import Environment, FileSystemLoader

from research_system.codegen.templates import (
    SIGNAL_TO_TEMPLATE,
    STRATEGY_TYPE_TO_TEMPLATE,
    TEMPLATE_DIR,
    get_template_for_strategy,
)


class TestTemplateConfiguration:
    """Tests for template configuration and mapping."""

    def test_template_directory_exists(self):
        """Test that template directory exists."""
        assert TEMPLATE_DIR.exists()
        assert TEMPLATE_DIR.is_dir()

    def test_base_template_exists(self):
        """Test that base template exists."""
        base_path = TEMPLATE_DIR / "base.py.j2"
        assert base_path.exists(), "base.py.j2 template not found"

    def test_all_mapped_templates_exist(self):
        """Test that all templates in mappings exist."""
        all_templates = set(SIGNAL_TO_TEMPLATE.values()) | set(STRATEGY_TYPE_TO_TEMPLATE.values())
        for template_name in all_templates:
            template_path = TEMPLATE_DIR / template_name
            assert template_path.exists(), f"Template {template_name} not found"

    def test_get_template_by_strategy_type(self):
        """Test template lookup by strategy type."""
        assert get_template_for_strategy("momentum_rotation") == "momentum_rotation.py.j2"
        assert get_template_for_strategy("mean_reversion") == "mean_reversion.py.j2"
        assert get_template_for_strategy("trend_following") == "trend_following.py.j2"
        assert get_template_for_strategy("dual_momentum") == "dual_momentum.py.j2"

    def test_get_template_by_signal_type(self):
        """Test template lookup by signal type when strategy type not found."""
        # Use a non-mapped strategy type to fall back to signal type
        assert (
            get_template_for_strategy("custom_strategy", "relative_momentum")
            == "momentum_rotation.py.j2"
        )
        assert (
            get_template_for_strategy("custom_strategy", "mean_reversion") == "mean_reversion.py.j2"
        )

    def test_get_template_unknown_raises(self):
        """Test that unknown strategy/signal type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_template_for_strategy("unknown_strategy", "unknown_signal")

        assert "No template found" in str(exc_info.value)


class TestTemplateLoading:
    """Tests for loading and parsing templates."""

    @pytest.fixture
    def jinja_env(self):
        """Create Jinja2 environment for testing."""
        return Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def test_base_template_loads(self, jinja_env):
        """Test that base template loads without syntax errors."""
        template = jinja_env.get_template("base.py.j2")
        assert template is not None

    def test_momentum_rotation_template_loads(self, jinja_env):
        """Test that momentum rotation template loads."""
        template = jinja_env.get_template("momentum_rotation.py.j2")
        assert template is not None

    def test_mean_reversion_template_loads(self, jinja_env):
        """Test that mean reversion template loads."""
        template = jinja_env.get_template("mean_reversion.py.j2")
        assert template is not None

    def test_trend_following_template_loads(self, jinja_env):
        """Test that trend following template loads."""
        template = jinja_env.get_template("trend_following.py.j2")
        assert template is not None

    def test_dual_momentum_template_loads(self, jinja_env):
        """Test that dual momentum template loads."""
        template = jinja_env.get_template("dual_momentum.py.j2")
        assert template is not None

    def test_breakout_template_loads(self, jinja_env):
        """Test that breakout template loads."""
        template = jinja_env.get_template("breakout.py.j2")
        assert template is not None


class TestTemplateContent:
    """Tests for template content requirements."""

    def _read_template(self, name: str) -> str:
        """Read template content as string."""
        return (TEMPLATE_DIR / name).read_text()

    def test_base_template_has_no_hardcoded_dates(self):
        """Test that base template has no hardcoded dates."""
        content = self._read_template("base.py.j2")
        # Check for date-setting methods that shouldn't be in template
        assert "SetStartDate(" not in content or "SetStartDate" in content.split("{#")[0]
        assert "SetEndDate(" not in content

    def test_base_template_has_warmup(self):
        """Test that base template sets warmup period."""
        content = self._read_template("base.py.j2")
        assert "SetWarmUp" in content

    def test_base_template_has_required_methods(self):
        """Test that base template has required methods."""
        content = self._read_template("base.py.j2")
        assert "def Initialize(self):" in content
        assert "def Rebalance(self):" in content
        assert "def CalculateTargetWeights(self)" in content
        assert "def ExecuteTargetWeights(self" in content

    def test_strategy_templates_extend_base(self):
        """Test that strategy templates extend base template."""
        strategy_templates = [
            "momentum_rotation.py.j2",
            "mean_reversion.py.j2",
            "trend_following.py.j2",
            "dual_momentum.py.j2",
            "breakout.py.j2",
        ]
        for template_name in strategy_templates:
            content = self._read_template(template_name)
            assert '{% extends "base.py.j2" %}' in content, f"{template_name} does not extend base"

    def test_strategy_templates_override_calculate_weights(self):
        """Test that strategy templates override the calculate weights block."""
        strategy_templates = [
            "momentum_rotation.py.j2",
            "mean_reversion.py.j2",
            "trend_following.py.j2",
            "dual_momentum.py.j2",
            "breakout.py.j2",
        ]
        for template_name in strategy_templates:
            content = self._read_template(template_name)
            assert "{% block calculate_weights %}" in content, (
                f"{template_name} does not override calculate_weights"
            )


class TestTemplateRendering:
    """Tests for template rendering with sample data."""

    @pytest.fixture
    def jinja_env(self):
        """Create Jinja2 environment for testing."""
        return Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @pytest.fixture
    def sample_context(self):
        """Sample context for rendering templates."""
        return {
            "class_name": "TestMomentumStrategy",
            "schema_version": "2.0",
            "strategy_type": "momentum_rotation",
            "metadata": {
                "id": "STRAT-TEST-001",
                "name": "Test Momentum Strategy",
                "description": "A test strategy for unit tests",
            },
            "universe": {
                "symbols": ["SPY", "TLT", "GLD"],
                "defensive_symbols": ["SHY"],
            },
            "signal": {
                "type": "relative_momentum",
                "lookback_days": 126,
                "selection_n": 1,
                "threshold": None,
            },
            "position_sizing": {
                "method": "equal_weight",
                "leverage": 1.0,
                "max_position_size": None,
                "target_volatility": None,
            },
            "rebalance": {
                "frequency": "monthly",
            },
        }

    def test_momentum_rotation_renders(self, jinja_env, sample_context):
        """Test that momentum rotation template renders."""
        template = jinja_env.get_template("momentum_rotation.py.j2")
        code = template.render(**sample_context)

        assert "class TestMomentumStrategy(QCAlgorithm):" in code
        assert "STRAT-TEST-001" in code
        assert "SetWarmUp" in code
        assert "SPY" in code
        assert "TLT" in code
        assert "GLD" in code

    def test_rendered_code_has_no_hardcoded_dates(self, jinja_env, sample_context):
        """Test that rendered code has no hardcoded dates."""
        template = jinja_env.get_template("momentum_rotation.py.j2")
        code = template.render(**sample_context)

        # These should not appear in generated code
        assert "SetStartDate(" not in code
        assert "SetEndDate(" not in code
        assert "2020" not in code  # No year hardcoded
        assert "2021" not in code
        assert "2022" not in code
        assert "2023" not in code
        assert "2024" not in code

    def test_rendered_code_is_valid_python_syntax(self, jinja_env, sample_context):
        """Test that rendered code has valid Python syntax."""
        template = jinja_env.get_template("momentum_rotation.py.j2")
        code = template.render(**sample_context)

        # This should not raise a SyntaxError
        compile(code, "<string>", "exec")

    def test_different_rebalance_frequencies(self, jinja_env, sample_context):
        """Test that different rebalance frequencies render correctly."""
        template = jinja_env.get_template("momentum_rotation.py.j2")

        for freq in ["daily", "weekly", "monthly", "quarterly"]:
            sample_context["rebalance"]["frequency"] = freq
            code = template.render(**sample_context)
            assert "Schedule.On" in code
            compile(code, "<string>", "exec")  # Valid syntax

    def test_mean_reversion_renders(self, jinja_env, sample_context):
        """Test that mean reversion template renders."""
        sample_context["signal"]["type"] = "mean_reversion"
        sample_context["signal"]["threshold"] = -2.0

        template = jinja_env.get_template("mean_reversion.py.j2")
        code = template.render(**sample_context)

        assert "CalculateZScore" in code
        assert "_threshold" in code
        compile(code, "<string>", "exec")

    def test_trend_following_renders(self, jinja_env, sample_context):
        """Test that trend following template renders."""
        sample_context["signal"]["type"] = "trend_following"

        template = jinja_env.get_template("trend_following.py.j2")
        code = template.render(**sample_context)

        assert "IsTrending" in code
        compile(code, "<string>", "exec")
