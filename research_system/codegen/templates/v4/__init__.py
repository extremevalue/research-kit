"""V4 strategy templates for code generation.

Template Structure:
- base.py.j2: Base template with shared structure
- momentum.py.j2: Momentum/rotation strategies
- mean_reversion.py.j2: Z-score based mean reversion
- regime_adaptive.py.j2: Regime-switching strategies

Template Selection:
Templates are selected based on the strategy's signal_type or strategy_type field.
"""

from pathlib import Path

# Template directory
V4_TEMPLATE_DIR = Path(__file__).parent

# Strategy type to template mapping
V4_STRATEGY_TO_TEMPLATE = {
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
    # Fallback
    "base": "base.py.j2",
}


def get_template_for_v4_strategy(
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
        if normalized in V4_STRATEGY_TO_TEMPLATE:
            return V4_STRATEGY_TO_TEMPLATE[normalized]

    # Try signal_type as fallback
    if signal_type:
        normalized = signal_type.lower().replace("-", "_").replace(" ", "_")
        if normalized in V4_STRATEGY_TO_TEMPLATE:
            return V4_STRATEGY_TO_TEMPLATE[normalized]

    # Default to base template
    return "base.py.j2"


def list_v4_templates() -> list[str]:
    """List all available V4 templates.

    Returns:
        List of template filenames
    """
    return sorted(V4_TEMPLATE_DIR.glob("*.py.j2"))
