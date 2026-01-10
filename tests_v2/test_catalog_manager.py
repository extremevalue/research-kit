"""Tests for CatalogManager CRUD operations."""

import tempfile

import pytest

from research_system.db.catalog_manager import CatalogManager
from research_system.schemas.common import (
    ConfidenceLevel,
    EntryStatus,
    EntryType,
    ValidationStatus,
)
from research_system.schemas.proposal import (
    Proposal,
    ProposalRationale,
    ProposalStatus,
    ProposalType,
)
from research_system.schemas.regime import (
    MarketDirection,
    RateEnvironment,
    RegimePerformanceSummary,
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
from research_system.schemas.validation import (
    AggregateMetrics,
    PerformanceFingerprint,
    ValidationResult,
    WindowMetrics,
    WindowResult,
)


@pytest.fixture
def catalog():
    """Create a temporary CatalogManager for testing."""
    with tempfile.TemporaryDirectory() as tmpdir, CatalogManager(tmpdir) as cm:
        yield cm


@pytest.fixture
def sample_strategy():
    """Create a sample strategy definition."""
    return StrategyDefinition(
        tier=1,
        metadata=StrategyMetadata(
            id="STRAT-001",
            name="Momentum Rotation",
            description="Simple momentum strategy",
            tags=["momentum", "rotation"],
        ),
        strategy_type="momentum_rotation",
        universe=UniverseConfig(type="fixed", symbols=["SPY", "TLT", "GLD"]),
        signal=SignalConfig(type="relative_momentum", lookback_days=126),
        position_sizing=PositionSizingConfig(method="equal_weight"),
        rebalance=RebalanceConfig(frequency="monthly"),
    )


@pytest.fixture
def sample_validation_result():
    """Create a sample validation result."""
    return ValidationResult(
        strategy_id="STRAT-001",
        strategy_definition_hash="sha256:abc123",
        generated_code_hash="sha256:def456",
        walk_forward_results=[
            WindowResult(
                window_id=1,
                start_date="2020-01-01",
                end_date="2020-12-31",
                metrics=WindowMetrics(cagr=0.15, sharpe=1.2, max_drawdown=0.12),
                regime_tags=RegimeTags(
                    direction=MarketDirection.BULL,
                    volatility=VolatilityLevel.NORMAL,
                    rate_environment=RateEnvironment.FALLING,
                ),
            ),
            WindowResult(
                window_id=2,
                start_date="2021-01-01",
                end_date="2021-12-31",
                metrics=WindowMetrics(cagr=0.08, sharpe=0.9, max_drawdown=0.15),
                regime_tags=RegimeTags(
                    direction=MarketDirection.BULL,
                    volatility=VolatilityLevel.HIGH,
                    rate_environment=RateEnvironment.RISING,
                ),
            ),
        ],
        aggregate_metrics=AggregateMetrics(
            mean_sharpe=1.05,
            sharpe_std=0.21,
            sharpe_95_ci_low=0.63,
            sharpe_95_ci_high=1.47,
            mean_cagr=0.115,
            cagr_std=0.05,
            mean_max_drawdown=0.135,
            worst_drawdown=0.15,
            consistency_score=1.0,
            p_value=0.03,
            p_value_adjusted=0.05,
        ),
        regime_performance=RegimePerformanceSummary(),
        performance_fingerprint=PerformanceFingerprint(
            recommended_use="Trending markets",
        ),
        validation_status=ValidationStatus.PASSED,
        confidence=ConfidenceLevel.HIGH,
    )


class TestCatalogManagerEntryOperations:
    """Tests for entry CRUD operations."""

    def test_create_entry(self, catalog, sample_strategy):
        """Test creating an entry."""
        entry_id = catalog.create_entry(sample_strategy)
        assert entry_id == "STRAT-001"

    def test_create_entry_saves_json_file(self, catalog, sample_strategy):
        """Test that create_entry saves JSON file."""
        catalog.create_entry(sample_strategy)

        json_path = catalog.strategies_path / "STRAT-001.json"
        assert json_path.exists()

    def test_get_entry_returns_entry(self, catalog, sample_strategy):
        """Test retrieving an entry."""
        catalog.create_entry(sample_strategy)

        entry = catalog.get_entry("STRAT-001")
        assert entry is not None
        assert entry.id == "STRAT-001"
        assert entry.name == "Momentum Rotation"
        assert entry.status == EntryStatus.UNTESTED
        assert entry.tier == 1

    def test_get_entry_includes_tags(self, catalog, sample_strategy):
        """Test that tags are included in entry."""
        catalog.create_entry(sample_strategy)

        entry = catalog.get_entry("STRAT-001")
        assert "momentum" in entry.tags
        assert "rotation" in entry.tags

    def test_get_entry_returns_none_for_missing(self, catalog):
        """Test that get_entry returns None for non-existent entry."""
        entry = catalog.get_entry("NONEXISTENT")
        assert entry is None

    def test_get_strategy_definition(self, catalog, sample_strategy):
        """Test retrieving full strategy definition."""
        catalog.create_entry(sample_strategy)

        definition = catalog.get_strategy_definition("STRAT-001")
        assert definition is not None
        assert definition.metadata.id == "STRAT-001"
        assert definition.strategy_type == "momentum_rotation"
        assert len(definition.universe.symbols) == 3

    def test_update_status(self, catalog, sample_strategy):
        """Test updating entry status."""
        catalog.create_entry(sample_strategy)

        result = catalog.update_status("STRAT-001", EntryStatus.VALIDATED)
        assert result is True

        entry = catalog.get_entry("STRAT-001")
        assert entry.status == EntryStatus.VALIDATED

    def test_update_status_blocked_with_reason(self, catalog, sample_strategy):
        """Test updating status to BLOCKED with reason."""
        catalog.create_entry(sample_strategy)

        catalog.update_status(
            "STRAT-001",
            EntryStatus.BLOCKED,
            blocking_reason="Missing historical data",
        )

        entry = catalog.get_entry("STRAT-001")
        assert entry.status == EntryStatus.BLOCKED
        assert entry.blocking_reason == "Missing historical data"

    def test_update_status_returns_false_for_missing(self, catalog):
        """Test update_status returns False for non-existent entry."""
        result = catalog.update_status("NONEXISTENT", EntryStatus.VALIDATED)
        assert result is False

    def test_archive_entry(self, catalog, sample_strategy):
        """Test archiving an entry."""
        catalog.create_entry(sample_strategy)

        result = catalog.archive_entry("STRAT-001", reason="Superseded by STRAT-002")
        assert result is True

        entry = catalog.get_entry("STRAT-001")
        assert entry.status == EntryStatus.ARCHIVED

    def test_archive_entry_with_canonical_id(self, catalog, sample_strategy):
        """Test archiving with canonical ID for deduplication."""
        # Create two entries
        catalog.create_entry(sample_strategy)

        strategy2 = StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(id="STRAT-002", name="Momentum V2"),
            strategy_type="momentum_rotation",
            universe=UniverseConfig(type="fixed", symbols=["SPY", "TLT"]),
            position_sizing=PositionSizingConfig(method="equal_weight"),
            rebalance=RebalanceConfig(frequency="monthly"),
        )
        catalog.create_entry(strategy2)

        # Archive first as duplicate of second
        catalog.archive_entry(
            "STRAT-001",
            reason="Duplicate of STRAT-002",
            canonical_id="STRAT-002",
        )

        entry = catalog.get_entry("STRAT-001")
        assert entry.status == EntryStatus.ARCHIVED


class TestCatalogManagerQueryOperations:
    """Tests for query operations."""

    def test_list_entries_all(self, catalog, sample_strategy):
        """Test listing all entries."""
        catalog.create_entry(sample_strategy)

        entries = catalog.list_entries()
        assert len(entries) == 1
        assert entries[0].id == "STRAT-001"

    def test_list_entries_by_status(self, catalog, sample_strategy):
        """Test filtering by status."""
        catalog.create_entry(sample_strategy)

        # No validated entries yet
        entries = catalog.list_entries(status=EntryStatus.VALIDATED)
        assert len(entries) == 0

        # One untested entry
        entries = catalog.list_entries(status=EntryStatus.UNTESTED)
        assert len(entries) == 1

    def test_list_entries_by_type(self, catalog, sample_strategy):
        """Test filtering by entry type."""
        catalog.create_entry(sample_strategy, entry_type=EntryType.STRAT)

        entries = catalog.list_entries(entry_type=EntryType.STRAT)
        assert len(entries) == 1

        entries = catalog.list_entries(entry_type=EntryType.IDEA)
        assert len(entries) == 0

    def test_list_entries_by_tag(self, catalog, sample_strategy):
        """Test filtering by tag."""
        catalog.create_entry(sample_strategy)

        entries = catalog.list_entries(tag="momentum")
        assert len(entries) == 1

        entries = catalog.list_entries(tag="nonexistent")
        assert len(entries) == 0

    def test_list_entries_pagination(self, catalog):
        """Test pagination."""
        # Create multiple entries
        for i in range(5):
            strategy = StrategyDefinition(
                tier=1,
                metadata=StrategyMetadata(id=f"STRAT-{i:03d}", name=f"Strategy {i}"),
                strategy_type="momentum",
                universe=UniverseConfig(type="fixed", symbols=["SPY"]),
                position_sizing=PositionSizingConfig(method="equal_weight"),
                rebalance=RebalanceConfig(frequency="monthly"),
            )
            catalog.create_entry(strategy)

        # Get first page
        page1 = catalog.list_entries(limit=2, offset=0)
        assert len(page1) == 2

        # Get second page
        page2 = catalog.list_entries(limit=2, offset=2)
        assert len(page2) == 2

        # Pages should be different
        assert page1[0].id != page2[0].id

    def test_count_entries(self, catalog, sample_strategy):
        """Test counting entries."""
        assert catalog.count_entries() == 0

        catalog.create_entry(sample_strategy)
        assert catalog.count_entries() == 1

    def test_count_entries_with_filters(self, catalog, sample_strategy):
        """Test counting with filters."""
        catalog.create_entry(sample_strategy)

        assert catalog.count_entries(status=EntryStatus.UNTESTED) == 1
        assert catalog.count_entries(status=EntryStatus.VALIDATED) == 0
        assert catalog.count_entries(entry_type=EntryType.STRAT) == 1


class TestCatalogManagerValidationOperations:
    """Tests for validation operations."""

    def test_add_validation_result(self, catalog, sample_strategy, sample_validation_result):
        """Test adding a validation result."""
        catalog.create_entry(sample_strategy)

        validation_id = catalog.add_validation_result("STRAT-001", sample_validation_result)
        assert validation_id > 0

    def test_add_validation_updates_entry_status(
        self, catalog, sample_strategy, sample_validation_result
    ):
        """Test that validation updates entry status."""
        catalog.create_entry(sample_strategy)
        catalog.add_validation_result("STRAT-001", sample_validation_result)

        entry = catalog.get_entry("STRAT-001")
        assert entry.status == EntryStatus.VALIDATED

    def test_add_validation_failed_sets_invalidated(self, catalog, sample_strategy):
        """Test that failed validation sets INVALIDATED status."""
        catalog.create_entry(sample_strategy)

        failed_result = ValidationResult(
            strategy_id="STRAT-001",
            strategy_definition_hash="sha256:abc123",
            generated_code_hash="sha256:def456",
            walk_forward_results=[
                WindowResult(
                    window_id=1,
                    start_date="2020-01-01",
                    end_date="2020-12-31",
                    metrics=WindowMetrics(cagr=-0.05, sharpe=-0.5, max_drawdown=0.30),
                    regime_tags=RegimeTags(
                        direction=MarketDirection.BEAR,
                        volatility=VolatilityLevel.HIGH,
                        rate_environment=RateEnvironment.RISING,
                    ),
                ),
            ],
            aggregate_metrics=AggregateMetrics(
                mean_sharpe=-0.5,
                sharpe_std=0.1,
                sharpe_95_ci_low=-0.7,
                sharpe_95_ci_high=-0.3,
                mean_cagr=-0.05,
                cagr_std=0.02,
                mean_max_drawdown=0.30,
                worst_drawdown=0.30,
                consistency_score=0.0,
                p_value=0.8,
                p_value_adjusted=0.9,
            ),
            regime_performance=RegimePerformanceSummary(),
            performance_fingerprint=PerformanceFingerprint(
                recommended_use="Not recommended",
            ),
            validation_status=ValidationStatus.FAILED,
            confidence=ConfidenceLevel.HIGH,
        )

        catalog.add_validation_result("STRAT-001", failed_result)

        entry = catalog.get_entry("STRAT-001")
        assert entry.status == EntryStatus.INVALIDATED

    def test_get_latest_validation(self, catalog, sample_strategy, sample_validation_result):
        """Test retrieving latest validation."""
        catalog.create_entry(sample_strategy)
        catalog.add_validation_result("STRAT-001", sample_validation_result)

        result = catalog.get_latest_validation("STRAT-001")
        assert result is not None
        assert result.strategy_id == "STRAT-001"
        assert result.validation_status == ValidationStatus.PASSED

    def test_get_latest_validation_returns_most_recent(self, catalog, sample_strategy):
        """Test that latest validation is returned when multiple exist."""
        catalog.create_entry(sample_strategy)

        # Add first validation
        result1 = ValidationResult(
            strategy_id="STRAT-001",
            strategy_definition_hash="sha256:v1",
            generated_code_hash="sha256:code1",
            walk_forward_results=[
                WindowResult(
                    window_id=1,
                    start_date="2020-01-01",
                    end_date="2020-12-31",
                    metrics=WindowMetrics(cagr=0.10, sharpe=0.8, max_drawdown=0.15),
                    regime_tags=RegimeTags(
                        direction=MarketDirection.BULL,
                        volatility=VolatilityLevel.NORMAL,
                        rate_environment=RateEnvironment.FLAT,
                    ),
                ),
            ],
            aggregate_metrics=AggregateMetrics(
                mean_sharpe=0.8,
                sharpe_std=0.1,
                sharpe_95_ci_low=0.6,
                sharpe_95_ci_high=1.0,
                mean_cagr=0.10,
                cagr_std=0.02,
                mean_max_drawdown=0.15,
                worst_drawdown=0.15,
                consistency_score=1.0,
                p_value=0.05,
                p_value_adjusted=0.08,
            ),
            regime_performance=RegimePerformanceSummary(),
            performance_fingerprint=PerformanceFingerprint(recommended_use="Test"),
            validation_status=ValidationStatus.PASSED,
            confidence=ConfidenceLevel.MEDIUM,
        )
        catalog.add_validation_result("STRAT-001", result1)

        # Add second validation with different hash
        result2 = ValidationResult(
            strategy_id="STRAT-001",
            strategy_definition_hash="sha256:v2",  # Different
            generated_code_hash="sha256:code2",
            walk_forward_results=[
                WindowResult(
                    window_id=1,
                    start_date="2020-01-01",
                    end_date="2020-12-31",
                    metrics=WindowMetrics(cagr=0.15, sharpe=1.2, max_drawdown=0.10),
                    regime_tags=RegimeTags(
                        direction=MarketDirection.BULL,
                        volatility=VolatilityLevel.NORMAL,
                        rate_environment=RateEnvironment.FLAT,
                    ),
                ),
            ],
            aggregate_metrics=AggregateMetrics(
                mean_sharpe=1.2,
                sharpe_std=0.1,
                sharpe_95_ci_low=1.0,
                sharpe_95_ci_high=1.4,
                mean_cagr=0.15,
                cagr_std=0.02,
                mean_max_drawdown=0.10,
                worst_drawdown=0.10,
                consistency_score=1.0,
                p_value=0.01,
                p_value_adjusted=0.02,
            ),
            regime_performance=RegimePerformanceSummary(),
            performance_fingerprint=PerformanceFingerprint(recommended_use="Test"),
            validation_status=ValidationStatus.PASSED,
            confidence=ConfidenceLevel.HIGH,
        )
        catalog.add_validation_result("STRAT-001", result2)

        # Should get the second (most recent) validation
        latest = catalog.get_latest_validation("STRAT-001")
        assert latest.strategy_definition_hash == "sha256:v2"
        assert latest.confidence == ConfidenceLevel.HIGH

    def test_get_latest_validation_returns_none_if_none(self, catalog, sample_strategy):
        """Test that None is returned if no validations exist."""
        catalog.create_entry(sample_strategy)
        result = catalog.get_latest_validation("STRAT-001")
        assert result is None


class TestCatalogManagerProposalOperations:
    """Tests for proposal operations."""

    def test_create_proposal(self, catalog):
        """Test creating a proposal."""
        proposal = Proposal(
            id="PROP-001",
            type=ProposalType.NEW_STRATEGY,
            created_by="synthesis_engine",
            title="New Mean Reversion Strategy",
            description="Test proposal",
            rationale=ProposalRationale(
                proposed_solution="Implement mean reversion",
                expected_improvement="Diversification",
            ),
        )

        proposal_id = catalog.create_proposal(proposal)
        assert proposal_id == "PROP-001"

    def test_list_proposals(self, catalog):
        """Test listing proposals."""
        proposal = Proposal(
            id="PROP-001",
            type=ProposalType.NEW_STRATEGY,
            created_by="test",
            title="Test",
            description="Test",
            rationale=ProposalRationale(proposed_solution="Test"),
        )
        catalog.create_proposal(proposal)

        proposals = catalog.list_proposals()
        assert len(proposals) == 1
        assert proposals[0].id == "PROP-001"

    def test_list_proposals_by_status(self, catalog):
        """Test filtering proposals by status."""
        proposal = Proposal(
            id="PROP-001",
            type=ProposalType.NEW_STRATEGY,
            created_by="test",
            title="Test",
            description="Test",
            rationale=ProposalRationale(proposed_solution="Test"),
        )
        catalog.create_proposal(proposal)

        pending = catalog.list_proposals(status=ProposalStatus.PENDING)
        assert len(pending) == 1

        approved = catalog.list_proposals(status=ProposalStatus.APPROVED)
        assert len(approved) == 0

    def test_review_proposal(self, catalog):
        """Test reviewing a proposal."""
        proposal = Proposal(
            id="PROP-001",
            type=ProposalType.NEW_STRATEGY,
            created_by="test",
            title="Test",
            description="Test",
            rationale=ProposalRationale(proposed_solution="Test"),
        )
        catalog.create_proposal(proposal)

        result = catalog.review_proposal(
            "PROP-001",
            status=ProposalStatus.APPROVED,
            notes="Looks good",
            reviewed_by="reviewer@test.com",
        )
        assert result is True

        # Note: Can't easily verify the update without a get_proposal method


class TestCatalogManagerStatistics:
    """Tests for statistics operations."""

    def test_get_catalog_stats_empty(self, catalog):
        """Test stats on empty catalog."""
        stats = catalog.get_catalog_stats()
        assert stats["total"] == 0
        assert stats["by_status"] == {}
        assert stats["by_type"] == {}

    def test_get_catalog_stats(self, catalog, sample_strategy):
        """Test stats with entries."""
        catalog.create_entry(sample_strategy)

        stats = catalog.get_catalog_stats()
        assert stats["total"] == 1
        assert stats["by_status"]["UNTESTED"] == 1
        assert stats["by_type"]["STRAT"] == 1

    def test_get_catalog_stats_multiple_entries(self, catalog):
        """Test stats with multiple entries in different states."""
        # Create strategies
        for i in range(3):
            strategy = StrategyDefinition(
                tier=1,
                metadata=StrategyMetadata(id=f"STRAT-{i:03d}", name=f"Strategy {i}"),
                strategy_type="momentum",
                universe=UniverseConfig(type="fixed", symbols=["SPY"]),
                position_sizing=PositionSizingConfig(method="equal_weight"),
                rebalance=RebalanceConfig(frequency="monthly"),
            )
            catalog.create_entry(strategy)

        # Update some statuses
        catalog.update_status("STRAT-000", EntryStatus.VALIDATED)
        catalog.update_status("STRAT-001", EntryStatus.INVALIDATED)

        stats = catalog.get_catalog_stats()
        assert stats["total"] == 3
        assert stats["by_status"]["VALIDATED"] == 1
        assert stats["by_status"]["INVALIDATED"] == 1
        assert stats["by_status"]["UNTESTED"] == 1


class TestCatalogManagerIntegration:
    """Integration tests for complete workflows."""

    def test_entry_lifecycle(self, catalog, sample_strategy, sample_validation_result):
        """Test complete entry lifecycle: create -> validate -> archive."""
        # Create
        entry_id = catalog.create_entry(sample_strategy)
        entry = catalog.get_entry(entry_id)
        assert entry.status == EntryStatus.UNTESTED

        # Validate
        catalog.add_validation_result(entry_id, sample_validation_result)
        entry = catalog.get_entry(entry_id)
        assert entry.status == EntryStatus.VALIDATED

        # Archive
        catalog.archive_entry(entry_id, reason="Replaced by better strategy")
        entry = catalog.get_entry(entry_id)
        assert entry.status == EntryStatus.ARCHIVED

    def test_proposal_to_entry_flow(self, catalog, sample_strategy):
        """Test proposal -> approve -> create entry flow."""
        # Create proposal
        proposal = Proposal(
            id="PROP-001",
            type=ProposalType.NEW_STRATEGY,
            created_by="synthesis_engine",
            title="New Strategy Proposal",
            description="Test",
            rationale=ProposalRationale(proposed_solution="Implement momentum"),
        )
        catalog.create_proposal(proposal)

        # Review and approve
        catalog.review_proposal(
            "PROP-001",
            status=ProposalStatus.APPROVED,
            notes="Approved for implementation",
            reviewed_by="reviewer",
        )

        # Create entry based on proposal
        catalog.create_entry(sample_strategy)

        # Verify both exist
        proposals = catalog.list_proposals(status=ProposalStatus.APPROVED)
        assert len(proposals) == 1

        entry = catalog.get_entry("STRAT-001")
        assert entry is not None

    def test_definition_hash_consistency(self, catalog, sample_strategy):
        """Test that definition hash is stored and retrievable."""
        catalog.create_entry(sample_strategy)

        entry = catalog.get_entry("STRAT-001")
        stored_hash = entry.definition_hash

        # Recompute hash from definition
        definition = catalog.get_strategy_definition("STRAT-001")
        computed_hash = definition.compute_hash()

        assert stored_hash == computed_hash
