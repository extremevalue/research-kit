"""Sample strategy definitions for testing."""

from research_system.schemas.strategy import (
    PositionSizingConfig,
    RebalanceConfig,
    SignalConfig,
    StrategyDefinition,
    StrategyMetadata,
    UniverseConfig,
)


def create_tier1_momentum_strategy() -> StrategyDefinition:
    """Create a standard Tier 1 momentum rotation strategy."""
    return StrategyDefinition(
        tier=1,
        metadata=StrategyMetadata(
            id="STRAT-TEST-001",
            name="Test Momentum Rotation",
            description="A simple momentum rotation strategy for testing",
            tags=["momentum", "rotation", "test"],
        ),
        strategy_type="momentum_rotation",
        universe=UniverseConfig(
            type="fixed",
            symbols=["SPY", "TLT", "GLD"],
            defensive_symbols=["SHY", "BIL"],
        ),
        signal=SignalConfig(
            type="relative_momentum",
            lookback_days=126,
            selection_method="top_n",
            selection_n=1,
        ),
        position_sizing=PositionSizingConfig(method="equal_weight"),
        rebalance=RebalanceConfig(frequency="monthly"),
    )


def create_tier1_mean_reversion_strategy() -> StrategyDefinition:
    """Create a Tier 1 mean reversion strategy."""
    return StrategyDefinition(
        tier=1,
        metadata=StrategyMetadata(
            id="STRAT-TEST-002",
            name="Test Mean Reversion",
            description="A simple mean reversion strategy for testing",
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
