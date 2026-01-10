"""Proposal schemas for human review queue."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ProposalType(str, Enum):
    """Type of proposal."""

    COMPOSITE_STRATEGY = "composite_strategy"
    ENHANCEMENT_LEVERAGE = "enhancement_leverage"
    ENHANCEMENT_OPTIONS = "enhancement_options"
    ENHANCEMENT_FUTURES = "enhancement_futures"
    ENHANCEMENT_SIZING = "enhancement_sizing"
    DATA_ACQUISITION = "data_acquisition"
    NEW_STRATEGY = "new_strategy"
    REFINED_HYPOTHESIS = "refined_hypothesis"


class ProposalStatus(str, Enum):
    """Status of proposal in queue."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class ProposalRationale(BaseModel):
    """Rationale for a proposal."""

    gap_identified: str | None = Field(None, description="What gap or opportunity was identified")
    proposed_solution: str = Field(..., description="How this proposal addresses it")
    expected_improvement: str | None = Field(None, description="Expected benefit")
    evidence: str | None = Field(None, description="Evidence supporting the proposal")


class SwitchingRule(BaseModel):
    """Rule for switching between strategies in composite."""

    condition: str = Field(..., description="Condition expression")
    use_strategy: str = Field(..., description="Strategy ID to use")


class SwitchingLogic(BaseModel):
    """Logic for composite strategy switching."""

    indicator: str = Field(..., description="Primary indicator for switching")
    rules: list[SwitchingRule] = Field(..., description="Ordered switching rules")


class DataRequirementDelta(BaseModel):
    """Data needed for proposal that isn't currently available."""

    needed: str = Field(..., description="What data is needed")
    unblocks: str = Field(..., description="What this data enables")
    source: str | None = Field(None, description="Potential data source")
    priority: str | None = Field(None, description="Priority level")


class Proposal(BaseModel):
    """A proposal awaiting human review."""

    id: str = Field(..., description="Unique proposal ID (e.g., PROP-001)")
    type: ProposalType
    status: ProposalStatus = Field(default=ProposalStatus.PENDING)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., description="Component that created this proposal")

    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed description")
    rationale: ProposalRationale

    # For composite strategies
    component_strategies: list[str] = Field(
        default_factory=list, description="Strategy IDs being combined"
    )
    switching_logic: SwitchingLogic | None = None

    # For enhancements
    parent_strategy: str | None = Field(None, description="Strategy being enhanced")
    enhancement_params: dict | None = Field(None, description="Parameters for enhancement")

    # For data acquisition
    data_requirements_delta: list[DataRequirementDelta] = Field(
        default_factory=list, description="New data requirements"
    )

    # Review fields
    review_notes: str | None = None
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    decision: str | None = None

    # Outcome
    resulting_entry_id: str | None = Field(None, description="Entry created if approved")


class Observation(BaseModel):
    """An observation extracted from validation results."""

    id: str = Field(..., description="Unique ID (e.g., OBS-001)")
    source_validation_id: str = Field(..., description="Validation that produced this")
    source_strategy_id: str = Field(..., description="Strategy that was validated")

    created_at: datetime = Field(default_factory=datetime.utcnow)

    observation_type: str = Field(
        ..., description="Type: regime_specific, failure_analysis, edge_case, etc."
    )
    title: str
    description: str

    # What we learned
    finding: str = Field(..., description="The key finding")
    implication: str | None = Field(None, description="What this means for future strategies")

    # Conditions
    regime_conditions: dict | None = Field(None, description="Regime conditions where this applies")

    # Links
    related_strategies: list[str] = Field(default_factory=list, description="Related strategy IDs")
    spawned_proposals: list[str] = Field(
        default_factory=list, description="Proposals created from this observation"
    )
