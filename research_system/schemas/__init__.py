"""Pydantic schemas for research-kit v2.0."""

from research_system.schemas.common import (
    ConfidenceLevel,
    EntryStatus,
    EntryType,
    ValidationStatus,
)
from research_system.schemas.proposal import (
    Proposal,
    ProposalStatus,
    ProposalType,
)
from research_system.schemas.regime import (
    MarketDirection,
    RateEnvironment,
    RegimeDefinition,
    RegimePerformanceSummary,
    RegimeTags,
    VolatilityLevel,
)
from research_system.schemas.strategy import (
    FilterConfig,
    PositionSizingConfig,
    RebalanceConfig,
    RiskManagementConfig,
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

# V4 Strategy schema
from research_system.schemas.v4 import Strategy, V4Strategy

__all__ = [
    # Common
    "EntryStatus",
    "EntryType",
    "ConfidenceLevel",
    "ValidationStatus",
    # Strategy
    "StrategyDefinition",
    "StrategyMetadata",
    "UniverseConfig",
    "SignalConfig",
    "FilterConfig",
    "PositionSizingConfig",
    "RebalanceConfig",
    "RiskManagementConfig",
    # Validation
    "ValidationResult",
    "WindowResult",
    "WindowMetrics",
    "AggregateMetrics",
    "PerformanceFingerprint",
    # Proposal
    "Proposal",
    "ProposalType",
    "ProposalStatus",
    # Regime
    "MarketDirection",
    "VolatilityLevel",
    "RateEnvironment",
    "RegimeDefinition",
    "RegimeTags",
    "RegimePerformanceSummary",
    # V4 Strategy
    "Strategy",
    "V4Strategy",
]
