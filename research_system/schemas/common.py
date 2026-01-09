"""Common types and enums shared across schemas."""

from enum import Enum


class EntryStatus(str, Enum):
    """Status of a catalog entry."""

    UNTESTED = "UNTESTED"
    VALIDATED = "VALIDATED"
    INVALIDATED = "INVALIDATED"
    BLOCKED = "BLOCKED"
    ARCHIVED = "ARCHIVED"


class EntryType(str, Enum):
    """Type of catalog entry."""

    STRAT = "STRAT"  # Complete trading strategy
    IDEA = "IDEA"  # Trading idea/concept
    IND = "IND"  # Indicator
    TOOL = "TOOL"  # Tool/utility
    LEARN = "LEARN"  # Learning/educational
    DATA = "DATA"  # Data source
    OBS = "OBS"  # Observation from validation


class ValidationStatus(str, Enum):
    """Result of validation."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    BLOCKED = "BLOCKED"


class ConfidenceLevel(str, Enum):
    """Confidence in validation result."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class StrategyTier(int, Enum):
    """Tier of strategy complexity."""

    TIER_1 = 1  # Templated - parameters only
    TIER_2 = 2  # Component-based with expressions
    TIER_3 = 3  # Custom code with review


class RebalanceFrequency(str, Enum):
    """How often to rebalance."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class PositionSizingMethod(str, Enum):
    """Position sizing methodology."""

    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    VOLATILITY_TARGET = "volatility_target"
    KELLY = "kelly"
    FIXED = "fixed"


class SignalType(str, Enum):
    """Type of trading signal."""

    RELATIVE_MOMENTUM = "relative_momentum"
    ABSOLUTE_MOMENTUM = "absolute_momentum"
    MEAN_REVERSION = "mean_reversion"
    TREND_FOLLOWING = "trend_following"
    BREAKOUT = "breakout"
    CUSTOM = "custom"


class UniverseType(str, Enum):
    """Type of trading universe."""

    FIXED = "fixed"
    DYNAMIC = "dynamic"
    SECTOR = "sector"
    INDEX_CONSTITUENTS = "index_constituents"
