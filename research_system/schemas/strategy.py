"""Strategy definition schemas for Tier 1, 2, and 3 strategies."""

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from research_system.schemas.common import (
    PositionSizingMethod,
    RebalanceFrequency,
    SignalType,
    UniverseType,
)


class StrategyMetadata(BaseModel):
    """Metadata for a strategy definition."""

    id: str = Field(..., description="Unique identifier (e.g., STRAT-001)")
    name: str = Field(..., description="Human-readable name")
    description: str | None = Field(None, description="Detailed description")
    source_document: str | None = Field(None, description="Path to source document")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    parent_id: str | None = Field(None, description="Parent strategy for variants")
    tags: list[str] = Field(default_factory=list)


class UniverseConfig(BaseModel):
    """Configuration for trading universe."""

    type: UniverseType = Field(..., description="How universe is defined")
    symbols: list[str] = Field(default_factory=list, description="Fixed list of symbols")
    defensive_symbols: list[str] = Field(
        default_factory=list, description="Symbols to use in risk-off"
    )
    index: str | None = Field(None, description="Index for constituents-based universe")
    sector: str | None = Field(None, description="Sector filter")
    min_market_cap: float | None = Field(None, description="Minimum market cap filter")
    min_volume: float | None = Field(None, description="Minimum volume filter")


class SignalConfig(BaseModel):
    """Configuration for trading signal."""

    type: SignalType = Field(..., description="Type of signal")
    lookback_days: int = Field(..., ge=1, description="Lookback period in days")
    selection_method: str = Field("top_n", description="How to select from ranked assets")
    selection_n: int = Field(1, ge=1, description="Number to select")
    threshold: float | None = Field(None, description="Threshold for signal generation")


class FilterConfig(BaseModel):
    """Configuration for a filter/screen."""

    type: str = Field(..., description="Filter type")
    condition: str = Field(..., description="Condition to apply")
    lookback_days: int | None = Field(None, description="Lookback for filter")
    threshold: float | None = Field(None, description="Threshold value")


class PositionSizingConfig(BaseModel):
    """Configuration for position sizing."""

    method: PositionSizingMethod = Field(..., description="Sizing methodology")
    target_volatility: float | None = Field(None, description="Target volatility for vol targeting")
    max_position_size: float | None = Field(None, ge=0, le=1, description="Max weight per position")
    leverage: float = Field(1.0, ge=0, description="Leverage multiplier")


class RebalanceConfig(BaseModel):
    """Configuration for rebalancing."""

    frequency: RebalanceFrequency = Field(..., description="Rebalance frequency")
    on_signal_change: bool = Field(False, description="Also rebalance when signal changes")
    threshold: float | None = Field(None, description="Drift threshold to trigger rebalance")


class RegimeFilterConfig(BaseModel):
    """Configuration for regime-based filtering."""

    enabled: bool = Field(True, description="Whether regime filter is active")
    indicator: str = Field(..., description="Indicator to use for regime detection")
    threshold: float = Field(..., description="Threshold for regime change")
    action: str = Field(..., description="Action when regime detected")


class RiskManagementConfig(BaseModel):
    """Configuration for risk management."""

    regime_filter: RegimeFilterConfig | None = None
    stop_loss: float | None = Field(None, ge=0, le=1, description="Stop loss percentage")
    max_drawdown: float | None = Field(None, ge=0, le=1, description="Max drawdown before reducing")


class DerivedSignal(BaseModel):
    """A derived signal using expression language (Tier 2)."""

    id: str = Field(..., description="Signal identifier")
    expression: str = Field(..., description="Expression in DSL")


class DataRequirement(BaseModel):
    """External data requirement (Tier 2)."""

    id: str = Field(..., description="Data identifier for reference")
    source: str = Field(..., description="Data source (e.g., fred, yahoo)")
    series: str = Field(..., description="Series identifier")
    frequency: str = Field("daily", description="Data frequency")


class AllocationRule(BaseModel):
    """Allocation rule based on conditions (Tier 2)."""

    name: str = Field(..., description="Rule name")
    condition: str = Field(..., description="Condition expression")
    allocation: dict[str, float] = Field(..., description="Symbol -> weight mapping")


class StrategyDefinition(BaseModel):
    """Complete strategy definition supporting Tier 1, 2, and 3."""

    schema_version: str = Field("2.0", description="Schema version")
    tier: Literal[1, 2, 3] = Field(..., description="Strategy tier")

    metadata: StrategyMetadata
    strategy_type: str = Field(..., description="Strategy type identifier")

    # Core components (Tier 1)
    universe: UniverseConfig
    signal: SignalConfig | None = None
    filters: list[FilterConfig] = Field(default_factory=list)
    position_sizing: PositionSizingConfig
    rebalance: RebalanceConfig
    risk_management: RiskManagementConfig | None = None

    # Extended components (Tier 2)
    data_requirements: list[DataRequirement] = Field(default_factory=list)
    derived_signals: list[DerivedSignal] = Field(default_factory=list)
    allocation_rules: list[AllocationRule] = Field(default_factory=list)

    # Custom code (Tier 3)
    custom_code: str | None = Field(None, description="Custom code for Tier 3")
    review_required: bool = Field(False, description="Whether human review needed")
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None

    def compute_hash(self) -> str:
        """Compute hash of definition for versioning."""
        # Build hash from key fields only to avoid recursion
        key_data = {
            "tier": self.tier,
            "strategy_type": self.strategy_type,
            "universe": self.universe.model_dump(),
            "signal": self.signal.model_dump() if self.signal else None,
            "filters": [f.model_dump() for f in self.filters],
            "position_sizing": self.position_sizing.model_dump(),
            "rebalance": self.rebalance.model_dump(),
            "risk_management": self.risk_management.model_dump() if self.risk_management else None,
            "data_requirements": [d.model_dump() for d in self.data_requirements],
            "derived_signals": [s.model_dump() for s in self.derived_signals],
            "allocation_rules": [r.model_dump() for r in self.allocation_rules],
        }
        json_str = json.dumps(key_data, sort_keys=True, default=str)
        return f"sha256:{hashlib.sha256(json_str.encode()).hexdigest()[:16]}"

    def model_post_init(self, __context) -> None:
        """Validate tier-specific requirements."""
        if self.tier == 2 and not (self.derived_signals or self.allocation_rules):
            pass  # Allow Tier 2 without expressions for simple cases

        if self.tier == 3 and not self.custom_code:
            pass  # Allow Tier 3 placeholder

        if self.tier == 3:
            self.review_required = True
