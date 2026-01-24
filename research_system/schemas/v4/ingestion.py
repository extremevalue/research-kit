"""V4 Ingestion quality scoring models.

This module defines the quality scoring system used during ingestion to filter
strategies before validation. It includes:
- Specificity scoring (can we actually backtest this?)
- Trust scoring (is it worth testing?)
- Red flag detection (hard and soft flags)
- Ingestion decision (accept, queue, archive, reject)
"""

from enum import Enum

from pydantic import BaseModel, Field, computed_field


# =============================================================================
# ENUMS
# =============================================================================


class RedFlagSeverity(str, Enum):
    """Severity of a red flag."""

    HARD = "hard"
    SOFT = "soft"


class IngestionDecision(str, Enum):
    """Decision from ingestion quality assessment."""

    ACCEPT = "accept"
    QUEUE = "queue"
    ARCHIVE = "archive"
    REJECT = "reject"


# =============================================================================
# SPECIFICITY SCORING
# =============================================================================


class SpecificityScore(BaseModel):
    """Specificity score: Can we actually backtest this strategy?

    A score of 0-8 based on whether key strategy components are defined.
    Strategies with score < 4 are typically too vague to test.
    """

    has_entry_rules: bool = Field(False, description="Are entry rules defined?")
    has_exit_rules: bool = Field(False, description="Are exit rules defined?")
    has_position_sizing: bool = Field(False, description="Is position sizing defined?")
    has_universe_definition: bool = Field(False, description="Is the universe defined?")
    has_backtest_period: bool = Field(False, description="Is a backtest period specified?")
    has_out_of_sample: bool = Field(False, description="Is OOS testing mentioned?")
    has_transaction_costs: bool = Field(False, description="Are transaction costs addressed?")
    has_code_or_pseudocode: bool = Field(False, description="Is code/pseudocode provided?")

    @computed_field
    @property
    def score(self) -> int:
        """Calculate the total specificity score (0-8)."""
        return sum([
            self.has_entry_rules,
            self.has_exit_rules,
            self.has_position_sizing,
            self.has_universe_definition,
            self.has_backtest_period,
            self.has_out_of_sample,
            self.has_transaction_costs,
            self.has_code_or_pseudocode,
        ])

    def passes_threshold(self, threshold: int = 4) -> bool:
        """Check if score meets minimum threshold."""
        return self.score >= threshold


# =============================================================================
# TRUST SCORING
# =============================================================================


class TrustScore(BaseModel):
    """Trust score: Is the strategy worth testing?

    A score of 0-100 based on multiple factors. Strategies with score < 50
    are typically archived rather than tested.

    Components:
    - Economic rationale (0-30): Is the "why" well-explained?
    - Out-of-sample evidence (0-25): Any OOS testing mentioned?
    - Implementation realism (0-20): Costs, capacity, execution addressed?
    - Source credibility (0-15): Track record, incentives, transparency
    - Novelty (0-10): New alpha or repackaged factor?
    - Red flag penalty (negative): -15 per red flag
    """

    economic_rationale: int = Field(
        0, ge=0, le=30, description="Economic rationale score (0-30)"
    )
    out_of_sample_evidence: int = Field(
        0, ge=0, le=25, description="Out-of-sample evidence score (0-25)"
    )
    implementation_realism: int = Field(
        0, ge=0, le=20, description="Implementation realism score (0-20)"
    )
    source_credibility: int = Field(
        0, ge=0, le=15, description="Source credibility score (0-15)"
    )
    novelty: int = Field(0, ge=0, le=10, description="Novelty score (0-10)")
    red_flag_penalty: int = Field(
        0, le=0, description="Red flag penalty (negative value)"
    )

    @computed_field
    @property
    def total(self) -> int:
        """Calculate the total trust score."""
        raw_total = (
            self.economic_rationale
            + self.out_of_sample_evidence
            + self.implementation_realism
            + self.source_credibility
            + self.novelty
            + self.red_flag_penalty
        )
        return max(0, min(100, raw_total))

    def passes_threshold(self, threshold: int = 50) -> bool:
        """Check if score meets minimum threshold."""
        return self.total >= threshold


# =============================================================================
# RED FLAGS
# =============================================================================


class RedFlag(BaseModel):
    """A detected red flag during ingestion.

    Red flags are warning signs that indicate a strategy may be:
    - Too good to be true (sharpe > 3, no losing periods)
    - Potentially fraudulent (selling courses, vague rationale)
    - Too risky to test (excessive parameters, high leverage)
    - Requiring investigation (single market, crowded factor)
    """

    flag: str = Field(..., description="Flag identifier")
    severity: RedFlagSeverity = Field(..., description="Flag severity")
    message: str = Field(..., description="Explanation of the flag")


# Predefined hard red flags that trigger rejection
HARD_RED_FLAGS = {
    "sharpe_above_3": "Claimed Sharpe > 3.0 (non-HFT) - almost certainly overfit or fraud",
    "no_losing_periods": "'Never had a losing month/year' - statistically implausible",
    "works_all_conditions": "'Works in all market conditions' - nothing does",
    "author_selling": "Author selling courses/signals/newsletters - massive incentive bias",
    "convenient_start_date": "Backtest starts after known drawdown - cherry-picked period",
    "excessive_parameters": "More than 5 tunable parameters - overfitting machine",
}

# Predefined soft red flags that trigger investigation
SOFT_RED_FLAGS = {
    "unknown_rationale": "No rationale found after sub-agent research",
    "no_transaction_costs": "No discussion of costs/slippage",
    "no_drawdown_mentioned": "No drawdown discussed - may be hiding pain",
    "single_market": "Only tested in one geography",
    "single_regime": "Only tested in bull market",
    "small_sample": "Fewer than 30 independent observations",
    "high_leverage": "Requires leverage > 3x",
    "crowded_factor": "Relies on well-known factor",
    "magic_numbers": "Specific params without justification",
    "stopped_discussing": "Strategy no longer mentioned by source",
}


def create_hard_red_flag(flag_id: str, custom_message: str | None = None) -> RedFlag:
    """Create a hard red flag from a known flag ID."""
    message = custom_message or HARD_RED_FLAGS.get(flag_id, f"Unknown hard red flag: {flag_id}")
    return RedFlag(flag=flag_id, severity=RedFlagSeverity.HARD, message=message)


def create_soft_red_flag(flag_id: str, custom_message: str | None = None) -> RedFlag:
    """Create a soft red flag from a known flag ID."""
    message = custom_message or SOFT_RED_FLAGS.get(flag_id, f"Unknown soft red flag: {flag_id}")
    return RedFlag(flag=flag_id, severity=RedFlagSeverity.SOFT, message=message)


# =============================================================================
# INGESTION QUALITY
# =============================================================================


class IngestionQuality(BaseModel):
    """Complete ingestion quality assessment.

    This model contains all quality scoring results from the ingestion process,
    including specificity, trust scores, detected red flags, and the final decision.
    """

    specificity: SpecificityScore = Field(
        default_factory=SpecificityScore, description="Specificity score"
    )
    trust_score: TrustScore = Field(
        default_factory=TrustScore, description="Trust score"
    )
    red_flags: list[RedFlag] = Field(
        default_factory=list, description="Detected red flags"
    )
    decision: IngestionDecision = Field(
        IngestionDecision.QUEUE, description="Ingestion decision"
    )
    rejection_reason: str | None = Field(None, description="Reason if rejected")
    warnings: list[str] = Field(
        default_factory=list, description="Warnings for accepted strategies"
    )

    def has_hard_red_flags(self) -> bool:
        """Check if any hard red flags are present."""
        return any(rf.severity == RedFlagSeverity.HARD for rf in self.red_flags)

    def get_hard_red_flags(self) -> list[RedFlag]:
        """Get all hard red flags."""
        return [rf for rf in self.red_flags if rf.severity == RedFlagSeverity.HARD]

    def get_soft_red_flags(self) -> list[RedFlag]:
        """Get all soft red flags."""
        return [rf for rf in self.red_flags if rf.severity == RedFlagSeverity.SOFT]

    def compute_decision(
        self,
        specificity_threshold: int = 4,
        trust_threshold: int = 50,
    ) -> IngestionDecision:
        """Compute the ingestion decision based on scores and flags.

        Logic:
        1. If any hard red flags -> REJECT
        2. If specificity < threshold -> ARCHIVE (too vague)
        3. If trust < threshold -> ARCHIVE (not worth testing)
        4. If soft red flags but passes other thresholds -> ACCEPT with warnings
        5. Otherwise -> ACCEPT

        Args:
            specificity_threshold: Minimum specificity score (default 4)
            trust_threshold: Minimum trust score (default 50)

        Returns:
            The computed ingestion decision
        """
        # Check hard red flags first
        if self.has_hard_red_flags():
            hard_flags = self.get_hard_red_flags()
            self.rejection_reason = f"Hard red flags: {', '.join(rf.flag for rf in hard_flags)}"
            self.decision = IngestionDecision.REJECT
            return self.decision

        # Check specificity
        if not self.specificity.passes_threshold(specificity_threshold):
            self.rejection_reason = (
                f"Specificity score {self.specificity.score}/{specificity_threshold} "
                "- too vague to test"
            )
            self.decision = IngestionDecision.ARCHIVE
            return self.decision

        # Check trust score
        if not self.trust_score.passes_threshold(trust_threshold):
            self.rejection_reason = (
                f"Trust score {self.trust_score.total}/{trust_threshold} "
                "- not worth testing"
            )
            self.decision = IngestionDecision.ARCHIVE
            return self.decision

        # Check soft red flags
        soft_flags = self.get_soft_red_flags()
        if soft_flags:
            self.warnings = [rf.message for rf in soft_flags]
            self.decision = IngestionDecision.ACCEPT
            return self.decision

        # All checks passed
        self.decision = IngestionDecision.ACCEPT
        return self.decision
