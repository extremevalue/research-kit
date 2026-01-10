"""Jinja2 templates for Tier 1 strategy code generation.

Template Structure
-----------------
- base.py.j2: Base template with shared structure (all strategies extend this)
- momentum_rotation.py.j2: Top-N momentum selection with rebalancing
- mean_reversion.py.j2: Z-score based entry/exit
- trend_following.py.j2: Moving average trend filter
- dual_momentum.py.j2: Combined absolute + relative momentum
- breakout.py.j2: Price breakout with trailing stops

Template Selection
-----------------
Templates are selected based on the `signal.type` field in the strategy schema:
- relative_momentum -> momentum_rotation.py.j2
- absolute_momentum -> dual_momentum.py.j2
- mean_reversion -> mean_reversion.py.j2
- trend_following -> trend_following.py.j2
- breakout -> breakout.py.j2

Or by explicit strategy_type:
- momentum_rotation -> momentum_rotation.py.j2
- dual_momentum -> dual_momentum.py.j2

Design Principles
----------------
1. NO HARDCODED DATES - All dates come from the framework
2. Deterministic output - Same schema always produces same code
3. Parameter injection - All configurable values come from schema
4. Framework compatibility - Generated code works with QuantConnect
"""

from pathlib import Path

# Template directory
TEMPLATE_DIR = Path(__file__).parent

# Signal type to template mapping
SIGNAL_TO_TEMPLATE = {
    "relative_momentum": "momentum_rotation.py.j2",
    "absolute_momentum": "dual_momentum.py.j2",
    "mean_reversion": "mean_reversion.py.j2",
    "trend_following": "trend_following.py.j2",
    "breakout": "breakout.py.j2",
}

# Strategy type to template mapping (takes precedence if specified)
STRATEGY_TYPE_TO_TEMPLATE = {
    "momentum_rotation": "momentum_rotation.py.j2",
    "dual_momentum": "dual_momentum.py.j2",
    "mean_reversion": "mean_reversion.py.j2",
    "trend_following": "trend_following.py.j2",
    "breakout": "breakout.py.j2",
}


def get_template_for_strategy(strategy_type: str, signal_type: str | None = None) -> str:
    """Get the appropriate template name for a strategy.

    Args:
        strategy_type: The strategy_type field from schema
        signal_type: The signal.type field from schema (optional)

    Returns:
        Template filename (e.g., "momentum_rotation.py.j2")

    Raises:
        ValueError: If no matching template found
    """
    # Strategy type takes precedence
    if strategy_type in STRATEGY_TYPE_TO_TEMPLATE:
        return STRATEGY_TYPE_TO_TEMPLATE[strategy_type]

    # Fall back to signal type
    if signal_type and signal_type in SIGNAL_TO_TEMPLATE:
        return SIGNAL_TO_TEMPLATE[signal_type]

    raise ValueError(
        f"No template found for strategy_type='{strategy_type}', signal_type='{signal_type}'. "
        f"Available strategy types: {list(STRATEGY_TYPE_TO_TEMPLATE.keys())}. "
        f"Available signal types: {list(SIGNAL_TO_TEMPLATE.keys())}."
    )
