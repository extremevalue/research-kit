"""Pydantic schemas for research-kit v2.0."""

from research_system.schemas.common import (
    EntryStatus,
    EntryType,
    ConfidenceLevel,
    ValidationStatus,
)
from research_system.schemas.strategy import (
    StrategyDefinition,
    StrategyMetadata,
    UniverseConfig,
    SignalConfig,
    FilterConfig,
    PositionSizingConfig,
    RebalanceConfig,
    RiskManagementConfig,
)
from research_system.schemas.validation import (
    ValidationResult,
    WindowResult,
    WindowMetrics,
    AggregateMetrics,
    PerformanceFingerprint,
)
from research_system.schemas.regime import RegimeTags, RegimePerformanceSummary
from research_system.schemas.proposal import (
    Proposal,
    ProposalType,
    ProposalStatus,
)
from research_system.schemas.regime import (
    MarketDirection,
    VolatilityLevel,
    RateEnvironment,
    RegimeDefinition,
)

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
]
