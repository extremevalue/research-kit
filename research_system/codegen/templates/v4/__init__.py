"""V4 strategy templates for code generation.

Template Structure:
- base.py.j2: Base template with shared structure
- momentum.py.j2: Momentum/rotation strategies
- mean_reversion.py.j2: Z-score based mean reversion
- regime_adaptive.py.j2: Regime-switching strategies
- options_income.py.j2: Options income strategies (puts, spreads, covered calls)

Template Selection:
Templates are selected based on the strategy's signal_type or strategy_type field.
"""

from pathlib import Path

# Template directory
TEMPLATE_DIR = Path(__file__).parent

# Strategy type to template mapping
STRATEGY_TO_TEMPLATE = {
    # Momentum variants
    "momentum": "momentum.py.j2",
    "momentum_rotation": "momentum.py.j2",
    "relative_momentum": "momentum.py.j2",
    "absolute_momentum": "momentum.py.j2",
    "dual_momentum": "momentum.py.j2",
    # Mean reversion variants
    "mean_reversion": "mean_reversion.py.j2",
    "mean-reversion": "mean_reversion.py.j2",
    "zscore": "mean_reversion.py.j2",
    "statistical_arbitrage": "mean_reversion.py.j2",
    # Regime-based variants
    "regime_adaptive": "regime_adaptive.py.j2",
    "regime-adaptive": "regime_adaptive.py.j2",
    "regime_switching": "regime_adaptive.py.j2",
    "tactical_allocation": "regime_adaptive.py.j2",
    # Options income strategies
    "options_income": "options_income.py.j2",
    "options-income": "options_income.py.j2",
    "cash_secured_put": "options_income.py.j2",
    "cash-secured-put": "options_income.py.j2",
    "put_credit_spread": "options_income.py.j2",
    "put-credit-spread": "options_income.py.j2",
    "covered_call": "options_income.py.j2",
    "covered-call": "options_income.py.j2",
    "options": "options_income.py.j2",
    # Fallback
    "base": "base.py.j2",
}


def get_template_for_strategy(
    strategy_type: str | None = None,
    signal_type: str | None = None,
) -> str:
    """Get the appropriate V4 template for a strategy.

    Args:
        strategy_type: The strategy_type field from strategy doc
        signal_type: The signal_type field from strategy doc (fallback)

    Returns:
        Template filename (e.g., "momentum.py.j2")
    """
    # Try strategy_type first (normalized to lowercase with underscores)
    if strategy_type:
        normalized = strategy_type.lower().replace("-", "_").replace(" ", "_")
        if normalized in STRATEGY_TO_TEMPLATE:
            return STRATEGY_TO_TEMPLATE[normalized]

    # Try signal_type as fallback
    if signal_type:
        normalized = signal_type.lower().replace("-", "_").replace(" ", "_")
        if normalized in STRATEGY_TO_TEMPLATE:
            return STRATEGY_TO_TEMPLATE[normalized]

    # Default to base template
    return "base.py.j2"


def list_templates() -> list[str]:
    """List all available V4 templates.

    Returns:
        List of template filenames
    """
    return sorted(TEMPLATE_DIR.glob("*.py.j2"))


# Backward-compat aliases
V4_TEMPLATE_DIR = TEMPLATE_DIR
V4_STRATEGY_TO_TEMPLATE = STRATEGY_TO_TEMPLATE
get_template_for_v4_strategy = get_template_for_strategy
list_v4_templates = list_templates
