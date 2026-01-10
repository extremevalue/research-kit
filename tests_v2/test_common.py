"""Tests for common types and enums."""

from research_system.schemas.common import (
    ConfidenceLevel,
    EntryStatus,
    EntryType,
    PositionSizingMethod,
    RebalanceFrequency,
    SignalType,
    StrategyTier,
    UniverseType,
    ValidationStatus,
)


class TestEntryStatus:
    """Tests for EntryStatus enum."""

    def test_all_status_values_exist(self):
        """Verify all expected status values are defined."""
        expected = {"UNTESTED", "VALIDATED", "INVALIDATED", "BLOCKED", "ARCHIVED"}
        actual = {s.value for s in EntryStatus}
        assert actual == expected

    def test_status_is_string_enum(self):
        """Verify status values can be used as strings."""
        assert EntryStatus.VALIDATED.value == "VALIDATED"
        # str() on StrEnum includes class name, use .value for raw string
        assert EntryStatus.VALIDATED == "VALIDATED"  # StrEnum comparison works


class TestEntryType:
    """Tests for EntryType enum."""

    def test_all_entry_types_exist(self):
        """Verify all expected entry types are defined."""
        expected = {"STRAT", "IDEA", "IND", "TOOL", "LEARN", "DATA", "OBS"}
        actual = {t.value for t in EntryType}
        assert actual == expected

    def test_entry_type_is_string_enum(self):
        """Verify entry types can be used as strings."""
        assert EntryType.STRAT.value == "STRAT"
        assert EntryType.IDEA == "IDEA"  # StrEnum comparison works


class TestValidationStatus:
    """Tests for ValidationStatus enum."""

    def test_all_validation_statuses_exist(self):
        """Verify all expected validation statuses are defined."""
        expected = {"PASSED", "FAILED", "ERROR", "BLOCKED"}
        actual = {s.value for s in ValidationStatus}
        assert actual == expected


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_all_confidence_levels_exist(self):
        """Verify all expected confidence levels are defined."""
        expected = {"HIGH", "MEDIUM", "LOW"}
        actual = {c.value for c in ConfidenceLevel}
        assert actual == expected


class TestStrategyTier:
    """Tests for StrategyTier enum."""

    def test_tier_values_are_integers(self):
        """Verify tiers are integer values 1-3."""
        assert StrategyTier.TIER_1.value == 1
        assert StrategyTier.TIER_2.value == 2
        assert StrategyTier.TIER_3.value == 3

    def test_tier_count(self):
        """Verify exactly 3 tiers exist."""
        assert len(StrategyTier) == 3


class TestRebalanceFrequency:
    """Tests for RebalanceFrequency enum."""

    def test_all_frequencies_exist(self):
        """Verify all expected frequencies are defined."""
        expected = {"daily", "weekly", "monthly", "quarterly"}
        actual = {f.value for f in RebalanceFrequency}
        assert actual == expected


class TestPositionSizingMethod:
    """Tests for PositionSizingMethod enum."""

    def test_all_methods_exist(self):
        """Verify all expected sizing methods are defined."""
        expected = {"equal_weight", "risk_parity", "volatility_target", "kelly", "fixed"}
        actual = {m.value for m in PositionSizingMethod}
        assert actual == expected


class TestSignalType:
    """Tests for SignalType enum."""

    def test_all_signal_types_exist(self):
        """Verify all expected signal types are defined."""
        expected = {
            "relative_momentum",
            "absolute_momentum",
            "mean_reversion",
            "trend_following",
            "breakout",
            "custom",
        }
        actual = {s.value for s in SignalType}
        assert actual == expected


class TestUniverseType:
    """Tests for UniverseType enum."""

    def test_all_universe_types_exist(self):
        """Verify all expected universe types are defined."""
        expected = {"fixed", "dynamic", "sector", "index_constituents"}
        actual = {u.value for u in UniverseType}
        assert actual == expected
