"""Basic tests for v2 schemas."""


from research_system.schemas.proposal import Proposal, ProposalRationale, ProposalType
from research_system.schemas.regime import (
    MarketDirection,
    RateEnvironment,
    RegimeTags,
    VolatilityLevel,
)
from research_system.schemas.strategy import (
    PositionSizingConfig,
    RebalanceConfig,
    SignalConfig,
    StrategyDefinition,
    StrategyMetadata,
    UniverseConfig,
)


class TestStrategyDefinition:
    """Tests for StrategyDefinition schema."""

    def test_tier1_strategy_creation(self):
        """Test creating a valid Tier 1 strategy."""
        strategy = StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(id="STRAT-001", name="Test Strategy"),
            strategy_type="momentum_rotation",
            universe=UniverseConfig(type="fixed", symbols=["SPY", "TLT", "GLD"]),
            signal=SignalConfig(type="relative_momentum", lookback_days=126),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="monthly"),
        )

        assert strategy.metadata.id == "STRAT-001"
        assert strategy.tier == 1
        assert len(strategy.universe.symbols) == 3

    def test_strategy_hash_is_deterministic(self):
        """Test that the same strategy produces the same hash."""
        strategy1 = StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(id="STRAT-001", name="Test"),
            strategy_type="momentum",
            universe=UniverseConfig(type="fixed", symbols=["SPY"]),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="monthly"),
        )

        strategy2 = StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(id="STRAT-001", name="Test"),
            strategy_type="momentum",
            universe=UniverseConfig(type="fixed", symbols=["SPY"]),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="monthly"),
        )

        assert strategy1.compute_hash() == strategy2.compute_hash()

    def test_strategy_json_serialization(self):
        """Test JSON serialization round-trip."""
        strategy = StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(id="STRAT-001", name="Test"),
            strategy_type="momentum",
            universe=UniverseConfig(type="fixed", symbols=["SPY"]),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="monthly"),
        )

        json_str = strategy.model_dump_json()
        restored = StrategyDefinition.model_validate_json(json_str)

        assert restored.metadata.id == strategy.metadata.id
        assert restored.strategy_type == strategy.strategy_type


class TestRegimeTags:
    """Tests for RegimeTags schema."""

    def test_regime_tags_creation(self):
        """Test creating regime tags."""
        tags = RegimeTags(
            direction=MarketDirection.BULL,
            volatility=VolatilityLevel.NORMAL,
            rate_environment=RateEnvironment.FALLING,
        )

        assert tags.direction == MarketDirection.BULL
        assert tags.volatility == VolatilityLevel.NORMAL

    def test_regime_tags_to_dict(self):
        """Test converting regime tags to dictionary."""
        tags = RegimeTags(
            direction=MarketDirection.BEAR,
            volatility=VolatilityLevel.HIGH,
            rate_environment=RateEnvironment.RISING,
        )

        result = tags.to_dict()

        assert result["direction"] == "bear"
        assert result["volatility"] == "high"
        assert result["rate_environment"] == "rising"


class TestProposal:
    """Tests for Proposal schema."""

    def test_proposal_creation(self):
        """Test creating a proposal."""
        proposal = Proposal(
            id="PROP-001",
            type=ProposalType.ENHANCEMENT_LEVERAGE,
            created_by="synthesis_engine",
            title="Test Proposal",
            description="A test proposal",
            rationale=ProposalRationale(
                proposed_solution="Apply 2x leverage",
                expected_improvement="Higher returns",
            ),
        )

        assert proposal.id == "PROP-001"
        assert proposal.type == ProposalType.ENHANCEMENT_LEVERAGE
        assert proposal.status.value == "pending"
