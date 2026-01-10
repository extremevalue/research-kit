"""Comprehensive tests for v2 schemas."""

import pytest
from pydantic import ValidationError

from research_system.schemas.proposal import (
    Proposal,
    ProposalRationale,
    ProposalStatus,
    ProposalType,
)
from research_system.schemas.regime import (
    CapLeadership,
    MarketDirection,
    RateEnvironment,
    RegimeDefinition,
    RegimePerformanceEntry,
    RegimePerformanceSummary,
    RegimeTags,
    SectorLeadership,
    VolatilityLevel,
)
from research_system.schemas.strategy import (
    AllocationRule,
    DataRequirement,
    DerivedSignal,
    FilterConfig,
    PositionSizingConfig,
    RebalanceConfig,
    RegimeFilterConfig,
    RiskManagementConfig,
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

    def test_tier2_strategy_with_expressions(self):
        """Test creating a Tier 2 strategy with derived signals."""
        strategy = StrategyDefinition(
            tier=2,
            metadata=StrategyMetadata(id="STRAT-002", name="Macro Rotation"),
            strategy_type="macro_rotation",
            universe=UniverseConfig(type="fixed", symbols=["SPY", "TLT", "GLD", "UUP"]),
            position_sizing=PositionSizingConfig(method="risk_parity"),
            rebalance=RebalanceConfig(frequency="monthly"),
            data_requirements=[
                DataRequirement(id="vix", source="yahoo", series="^VIX"),
                DataRequirement(id="dxy", source="fred", series="DTWEXBGS"),
            ],
            derived_signals=[
                DerivedSignal(id="risk_on", expression="vix < 20 and spy_momentum > 0"),
            ],
            allocation_rules=[
                AllocationRule(
                    name="risk_on_allocation",
                    condition="risk_on == true",
                    allocation={"SPY": 0.6, "GLD": 0.2, "TLT": 0.2},
                ),
                AllocationRule(
                    name="risk_off_allocation",
                    condition="risk_on == false",
                    allocation={"TLT": 0.6, "GLD": 0.3, "UUP": 0.1},
                ),
            ],
        )

        assert strategy.tier == 2
        assert len(strategy.data_requirements) == 2
        assert len(strategy.derived_signals) == 1
        assert len(strategy.allocation_rules) == 2

    def test_tier3_strategy_requires_review(self):
        """Test that Tier 3 strategies are marked for review."""
        strategy = StrategyDefinition(
            tier=3,
            metadata=StrategyMetadata(id="STRAT-003", name="Custom ML Strategy"),
            strategy_type="custom_ml",
            universe=UniverseConfig(type="dynamic"),
            position_sizing=PositionSizingConfig(method="volatility_target"),
            rebalance=RebalanceConfig(frequency="daily"),
            custom_code="# Custom backtesting code here",
        )

        assert strategy.tier == 3
        assert strategy.review_required is True
        assert strategy.custom_code is not None

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

    def test_strategy_hash_changes_with_content(self):
        """Test that different strategies produce different hashes."""
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
            universe=UniverseConfig(type="fixed", symbols=["SPY", "TLT"]),  # Different
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="monthly"),
        )

        assert strategy1.compute_hash() != strategy2.compute_hash()

    def test_strategy_hash_ignores_metadata_changes(self):
        """Test that hash doesn't change when only metadata changes."""
        strategy1 = StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(id="STRAT-001", name="Original Name"),
            strategy_type="momentum",
            universe=UniverseConfig(type="fixed", symbols=["SPY"]),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="monthly"),
        )

        strategy2 = StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(id="STRAT-002", name="Different Name"),  # Different ID/name
            strategy_type="momentum",
            universe=UniverseConfig(type="fixed", symbols=["SPY"]),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="monthly"),
        )

        # Hash should be the same since strategy logic is identical
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

    def test_strategy_with_risk_management(self):
        """Test strategy with risk management config."""
        strategy = StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(id="STRAT-001", name="Risk Managed"),
            strategy_type="momentum",
            universe=UniverseConfig(
                type="fixed",
                symbols=["SPY", "QQQ"],
                defensive_symbols=["TLT", "GLD"],
            ),
            signal=SignalConfig(type="trend_following", lookback_days=200),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="weekly"),
            risk_management=RiskManagementConfig(
                regime_filter=RegimeFilterConfig(
                    enabled=True,
                    indicator="SPY_SMA_200",
                    threshold=0.0,
                    action="switch_to_defensive",
                ),
                stop_loss=0.10,
                max_drawdown=0.20,
            ),
        )

        assert strategy.risk_management is not None
        assert strategy.risk_management.stop_loss == 0.10
        assert strategy.risk_management.regime_filter.enabled is True

    def test_strategy_with_filters(self):
        """Test strategy with filter configs."""
        strategy = StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(id="STRAT-001", name="Filtered"),
            strategy_type="momentum",
            universe=UniverseConfig(type="index_constituents", index="SPY"),
            signal=SignalConfig(type="relative_momentum", lookback_days=126),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="monthly"),
            filters=[
                FilterConfig(type="price", condition="above_sma", lookback_days=200),
                FilterConfig(type="volume", condition="min_avg", threshold=1000000),
            ],
        )

        assert len(strategy.filters) == 2
        assert strategy.filters[0].type == "price"

    def test_invalid_tier_rejected(self):
        """Test that invalid tier values are rejected."""
        with pytest.raises(ValidationError):
            StrategyDefinition(
                tier=4,  # Invalid - only 1, 2, 3 allowed
                metadata=StrategyMetadata(id="STRAT-001", name="Test"),
                strategy_type="momentum",
                universe=UniverseConfig(type="fixed", symbols=["SPY"]),
                position_sizing=PositionSizingConfig(method="equal_weight"),
                rebalance=RebalanceConfig(frequency="monthly"),
            )


class TestUniverseConfig:
    """Tests for UniverseConfig schema."""

    def test_fixed_universe(self):
        """Test fixed symbol universe."""
        universe = UniverseConfig(type="fixed", symbols=["SPY", "TLT", "GLD"])
        assert universe.type == "fixed"
        assert len(universe.symbols) == 3

    def test_index_constituents_universe(self):
        """Test index-based universe."""
        universe = UniverseConfig(type="index_constituents", index="SPY")
        assert universe.type == "index_constituents"
        assert universe.index == "SPY"

    def test_sector_universe(self):
        """Test sector-filtered universe."""
        universe = UniverseConfig(
            type="sector",
            sector="technology",
            min_market_cap=10_000_000_000,
            min_volume=1_000_000,
        )
        assert universe.type == "sector"
        assert universe.min_market_cap == 10_000_000_000


class TestPositionSizingConfig:
    """Tests for PositionSizingConfig schema."""

    def test_equal_weight(self):
        """Test equal weight sizing."""
        sizing = PositionSizingConfig(method="equal_weight")
        assert sizing.method == "equal_weight"
        assert sizing.leverage == 1.0

    def test_volatility_target(self):
        """Test volatility target sizing."""
        sizing = PositionSizingConfig(
            method="volatility_target",
            target_volatility=0.15,
            max_position_size=0.25,
        )
        assert sizing.method == "volatility_target"
        assert sizing.target_volatility == 0.15

    def test_leverage_constraint(self):
        """Test that leverage must be non-negative."""
        with pytest.raises(ValidationError):
            PositionSizingConfig(method="equal_weight", leverage=-1.0)

    def test_max_position_size_bounds(self):
        """Test max_position_size must be between 0 and 1."""
        # Valid
        sizing = PositionSizingConfig(method="equal_weight", max_position_size=0.5)
        assert sizing.max_position_size == 0.5

        # Invalid - above 1
        with pytest.raises(ValidationError):
            PositionSizingConfig(method="equal_weight", max_position_size=1.5)


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

    def test_regime_tags_with_optional_fields(self):
        """Test regime tags with optional sector and cap leadership."""
        tags = RegimeTags(
            direction=MarketDirection.BULL,
            volatility=VolatilityLevel.LOW,
            rate_environment=RateEnvironment.FLAT,
            sector_leader=SectorLeadership.TECH,
            cap_leadership=CapLeadership.LARGE,
        )

        result = tags.to_dict()
        assert result["sector_leader"] == "tech"
        assert result["cap_leadership"] == "large"

    def test_regime_tags_without_optional_fields(self):
        """Test to_dict excludes None optional fields."""
        tags = RegimeTags(
            direction=MarketDirection.SIDEWAYS,
            volatility=VolatilityLevel.NORMAL,
            rate_environment=RateEnvironment.FLAT,
        )

        result = tags.to_dict()
        assert "sector_leader" not in result
        assert "cap_leadership" not in result


class TestRegimeDefinition:
    """Tests for RegimeDefinition schema."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        definition = RegimeDefinition()

        assert definition.direction_bull_threshold == 0.05
        assert definition.direction_bear_threshold == -0.05
        assert definition.volatility_low_threshold == 15.0
        assert definition.volatility_high_threshold == 25.0

    def test_custom_thresholds(self):
        """Test custom threshold values."""
        definition = RegimeDefinition(
            direction_bull_threshold=0.10,
            volatility_high_threshold=30.0,
        )

        assert definition.direction_bull_threshold == 0.10
        assert definition.volatility_high_threshold == 30.0


class TestRegimePerformance:
    """Tests for regime performance schemas."""

    def test_performance_entry(self):
        """Test RegimePerformanceEntry."""
        entry = RegimePerformanceEntry(
            mean_sharpe=1.2,
            mean_cagr=0.15,
            n_windows=5,
            win_rate=0.6,
        )
        assert entry.mean_sharpe == 1.2
        assert entry.n_windows == 5

    def test_performance_summary(self):
        """Test RegimePerformanceSummary."""
        summary = RegimePerformanceSummary(
            by_direction={
                "bull": RegimePerformanceEntry(mean_sharpe=1.5, mean_cagr=0.20, n_windows=8),
                "bear": RegimePerformanceEntry(mean_sharpe=0.3, mean_cagr=0.02, n_windows=4),
            },
        )

        assert "bull" in summary.by_direction
        assert summary.by_direction["bull"].mean_sharpe == 1.5


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
        assert proposal.status == ProposalStatus.PENDING

    def test_proposal_types(self):
        """Test all proposal types can be used."""
        types = [
            ProposalType.ENHANCEMENT_LEVERAGE,
            ProposalType.ENHANCEMENT_SIZING,
            ProposalType.COMPOSITE_STRATEGY,
            ProposalType.NEW_STRATEGY,
        ]

        for ptype in types:
            proposal = Proposal(
                id=f"PROP-{ptype.value}",
                type=ptype,
                created_by="test",
                title="Test",
                description="Test",
                rationale=ProposalRationale(
                    proposed_solution="Solution",
                    expected_improvement="Improvement",
                ),
            )
            assert proposal.type == ptype

    def test_proposal_with_component_strategies(self):
        """Test composite proposal with component strategies."""
        proposal = Proposal(
            id="PROP-001",
            type=ProposalType.COMPOSITE_STRATEGY,
            created_by="synthesis_engine",
            title="Combine Strategies",
            description="Combine momentum and mean reversion",
            component_strategies=["STRAT-001", "STRAT-002"],
            rationale=ProposalRationale(
                proposed_solution="50/50 allocation",
                expected_improvement="Diversification benefit",
            ),
        )

        assert len(proposal.component_strategies) == 2
        assert "STRAT-001" in proposal.component_strategies

    def test_proposal_json_roundtrip(self):
        """Test JSON serialization round-trip."""
        proposal = Proposal(
            id="PROP-001",
            type=ProposalType.ENHANCEMENT_SIZING,
            created_by="test",
            title="Adjust Position Sizing",
            description="Implement volatility targeting",
            rationale=ProposalRationale(
                proposed_solution="Use volatility-scaled positions",
                expected_improvement="Reduce drawdowns",
            ),
        )

        json_str = proposal.model_dump_json()
        restored = Proposal.model_validate_json(json_str)

        assert restored.id == proposal.id
        assert restored.type == proposal.type
        assert restored.rationale.proposed_solution == proposal.rationale.proposed_solution
