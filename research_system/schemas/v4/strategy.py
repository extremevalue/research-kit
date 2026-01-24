"""V4 Strategy document schema models.

This module defines the comprehensive strategy schema for V4, supporting:
- Simple and regime-adaptive strategies
- Multiple position types (single-leg, multi-leg, pairs, spreads)
- Various entry types (technical, event-driven, statistical, fundamental, alternative, compound)
- Complex position management and exit paths
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


# =============================================================================
# ENUMS
# =============================================================================


class StrategyStatus(str, Enum):
    """Status of a strategy in the system."""

    PENDING = "pending"
    VALIDATING = "validating"
    VALIDATED = "validated"
    INVALIDATED = "invalidated"
    BLOCKED = "blocked"


class SourceType(str, Enum):
    """Type of source for a strategy."""

    ACADEMIC = "academic"
    PODCAST = "podcast"
    BLOG = "blog"
    PRACTITIONER = "practitioner"
    PERSONAL = "personal"


class AuthorTrackRecord(str, Enum):
    """Track record of the strategy author."""

    VERIFIED_FUND_MANAGER = "verified_fund_manager"
    ACADEMIC = "academic"
    RETAIL_VERIFIED = "retail_verified"
    RETAIL_UNVERIFIED = "retail_unverified"
    UNKNOWN = "unknown"


class LineageRelationship(str, Enum):
    """Relationship to parent strategy."""

    VARIANT = "variant"
    COMBINATION = "combination"
    REFINEMENT = "refinement"
    REVERSAL = "reversal"


class HypothesisType(str, Enum):
    """Types of trading hypotheses."""

    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    EVENT_DRIVEN = "event_driven"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    INCOME = "income"
    RELATIVE_VALUE = "relative_value"
    REGIME_ADAPTIVE = "regime_adaptive"


class AssetClass(str, Enum):
    """Asset classes."""

    EQUITY = "equity"
    FX = "fx"
    OPTIONS = "options"
    FUTURES = "futures"
    CRYPTO = "crypto"
    MULTI_ASSET = "multi_asset"
    ETF = "etf"


class Complexity(str, Enum):
    """Strategy complexity level."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class EdgeCategory(str, Enum):
    """Category of trading edge."""

    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"
    INFORMATIONAL = "informational"
    RISK_PREMIUM = "risk_premium"
    OTHER = "other"


class ProvenanceSource(str, Enum):
    """Source of edge rationale."""

    SOURCE_STATED = "source_stated"
    SOURCE_ENHANCED = "source_enhanced"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class ProvenanceConfidence(str, Enum):
    """Confidence in edge rationale."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class StrategyMode(str, Enum):
    """Mode of strategy operation."""

    SIMPLE = "simple"
    REGIME_ADAPTIVE = "regime_adaptive"


class UniverseType(str, Enum):
    """Type of trading universe."""

    STATIC = "static"
    FILTERED = "filtered"
    RESEARCH_DERIVED = "research_derived"
    SIGNAL_DERIVED = "signal_derived"


class UniverseBase(str, Enum):
    """Base universe for filtered type."""

    US_EQUITIES = "us_equities"
    SP500 = "sp500"
    NASDAQ100 = "nasdaq100"
    SECTOR_ETFS = "sector_etfs"
    FX_MAJORS = "fx_majors"
    COMMODITY_FUTURES = "commodity_futures"
    CRYPTO_MAJOR = "crypto_major"
    CUSTOM = "custom"


class FilterOperator(str, Enum):
    """Filter operators."""

    GT = "gt"
    LT = "lt"
    EQ = "eq"
    GTE = "gte"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"
    EXISTS = "exists"


class ResearchMethod(str, Enum):
    """Research methods for universe derivation."""

    CORRELATION_ANALYSIS = "correlation_analysis"
    FACTOR_ANALYSIS = "factor_analysis"
    CLUSTERING = "clustering"
    COINTEGRATION_TEST = "cointegration_test"
    PCA = "pca"
    CUSTOM = "custom"


class SignalRefresh(str, Enum):
    """Signal refresh frequency."""

    DAILY = "daily"
    WEEKLY = "weekly"
    INTRADAY = "intraday"
    ON_SIGNAL = "on_signal"


class EntryType(str, Enum):
    """Type of entry signal."""

    TECHNICAL = "technical"
    EVENT_DRIVEN = "event_driven"
    STATISTICAL = "statistical"
    FUNDAMENTAL = "fundamental"
    ALTERNATIVE_DATA = "alternative_data"
    COMPOUND = "compound"


class EventType(str, Enum):
    """Type of event for event-driven entry."""

    EARNINGS = "earnings"
    EX_DIVIDEND = "ex_dividend"
    ECONOMIC_RELEASE = "economic_release"
    IPO = "ipo"
    SPLIT = "split"
    CUSTOM = "custom"


class TimingReference(str, Enum):
    """Timing reference for events."""

    BEFORE = "before"
    AT = "at"
    AFTER = "after"


class StatisticalMetric(str, Enum):
    """Statistical metrics."""

    ZSCORE = "zscore"
    PERCENTILE = "percentile"
    DEVIATION = "deviation"
    SPREAD = "spread"
    IV_RV_RATIO = "iv_rv_ratio"
    CUSTOM = "custom"


class ThresholdDirection(str, Enum):
    """Direction for threshold comparison."""

    ABOVE = "above"
    BELOW = "below"
    OUTSIDE_BAND = "outside_band"


class AlternativeDataSource(str, Enum):
    """Alternative data sources."""

    SENTIMENT = "sentiment"
    NEWS = "news"
    SATELLITE = "satellite"
    WEB_TRAFFIC = "web_traffic"
    OPTIONS_FLOW = "options_flow"
    INSIDER_TRANSACTIONS = "insider_transactions"
    CUSTOM = "custom"


class CompoundLogic(str, Enum):
    """Logic for compound entry."""

    AND = "and"
    OR = "or"


class PositionType(str, Enum):
    """Type of position structure."""

    SINGLE_LEG = "single_leg"
    MULTI_LEG = "multi_leg"
    PAIRS = "pairs"
    SPREAD = "spread"
    CUSTOM = "custom"


class Direction(str, Enum):
    """Position direction."""

    LONG = "long"
    SHORT = "short"
    DYNAMIC = "dynamic"


class InstrumentSource(str, Enum):
    """Source of instrument selection."""

    STATIC = "static"
    FROM_UNIVERSE = "from_universe"
    FROM_SIGNAL = "from_signal"
    FROM_RESEARCH = "from_research"


class InstrumentSelection(str, Enum):
    """Instrument selection method."""

    ALL = "all"
    FILTERED = "filtered"
    RANKED = "ranked"


class InstrumentAssetType(str, Enum):
    """Asset type for instruments."""

    EQUITY = "equity"
    ETF = "etf"
    OPTION = "option"
    FUTURE = "future"
    FX = "fx"
    CRYPTO = "crypto"


class OptionType(str, Enum):
    """Option type."""

    CALL = "call"
    PUT = "put"
    STRADDLE = "straddle"
    STRANGLE = "strangle"


class StrikeSelection(str, Enum):
    """Strike selection method."""

    ATM = "atm"
    OTM_1 = "otm_1"
    OTM_2 = "otm_2"
    ITM_1 = "itm_1"
    DELTA_XX = "delta_XX"
    PCT_OTM_XX = "pct_otm_XX"
    CUSTOM = "custom"


class ExpirySelection(str, Enum):
    """Expiry selection method."""

    NEAREST_WEEKLY = "nearest_weekly"
    NEAREST_MONTHLY = "nearest_monthly"
    DAYS_XX = "days_XX"
    DAYS_30 = "days_30"
    SPECIFIC_DTE = "specific_dte"
    CUSTOM = "custom"


class AllocationMethod(str, Enum):
    """Allocation method."""

    FIXED_PCT = "fixed_pct"
    FIXED_AMOUNT = "fixed_amount"
    EQUAL_WEIGHT = "equal_weight"
    VOLATILITY_TARGET = "volatility_target"
    FROM_SIZING = "from_sizing"
    DELTA_NEUTRAL = "delta_neutral"


class SizingMethod(str, Enum):
    """Position sizing method."""

    EQUAL_WEIGHT = "equal_weight"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    RISK_PARITY = "risk_parity"
    KELLY = "kelly"
    FIXED_FRACTIONAL = "fixed_fractional"
    CUSTOM = "custom"


class ExitType(str, Enum):
    """Exit path type."""

    SIGNAL_REVERSAL = "signal_reversal"
    CONVERGENCE = "convergence"
    TIME_BASED = "time_based"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    TAKE_PROFIT = "take_profit"
    OPTION_EXPIRY = "option_expiry"
    OPTION_ASSIGNMENT = "option_assignment"
    VOLATILITY_EXIT = "volatility_exit"
    CUSTOM = "custom"


class StopType(str, Enum):
    """Stop loss type."""

    FIXED_PCT = "fixed_pct"
    ATR_MULTIPLE = "atr_multiple"
    SUPPORT_LEVEL = "support_level"
    TRAILING = "trailing"


class TrailType(str, Enum):
    """Trailing stop type."""

    PCT = "pct"
    ATR_MULTIPLE = "atr_multiple"
    CHANDELIER = "chandelier"


class TargetType(str, Enum):
    """Take profit target type."""

    FIXED_PCT = "fixed_pct"
    RISK_MULTIPLE = "risk_multiple"
    RESISTANCE_LEVEL = "resistance_level"


class ExpiryAction(str, Enum):
    """Action at option expiry."""

    LET_EXPIRE = "let_expire"
    ROLL = "roll"
    CLOSE_BEFORE = "close_before"


class ExitPriority(str, Enum):
    """Exit path priority."""

    FIRST_TRIGGERED = "first_triggered"
    BY_ORDER = "by_order"
    SIMULTANEOUS_EVAL = "simultaneous_eval"


class ManagementTriggerType(str, Enum):
    """Position management trigger type."""

    THRESHOLD = "threshold"
    TIME_INTERVAL = "time_interval"
    SIGNAL = "signal"


class ManagementActionType(str, Enum):
    """Position management action type."""

    REBALANCE = "rebalance"
    HEDGE = "hedge"
    ROLL = "roll"
    ADJUST = "adjust"
    CLOSE_PARTIAL = "close_partial"


class RegimeDetectionMethod(str, Enum):
    """Regime detection method."""

    VOLATILITY_REGIME = "volatility_regime"
    TREND_STRENGTH = "trend_strength"
    MOVING_AVERAGE_POSITION = "moving_average_position"
    HMM = "hmm"
    MANUAL_INDICATOR = "manual_indicator"
    CUSTOM = "custom"


class RegimeAction(str, Enum):
    """Action for a regime mode."""

    TRADE = "trade"
    FLAT = "flat"


class PriceDataType(str, Enum):
    """Price data type."""

    DAILY = "daily"
    INTRADAY_1MIN = "intraday_1min"
    INTRADAY_5MIN = "intraday_5min"
    TICK = "tick"


class FundamentalFrequency(str, Enum):
    """Fundamental data frequency."""

    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    TTM = "ttm"
    DAILY = "daily"


class OptionsDataType(str, Enum):
    """Options data type."""

    CHAINS = "chains"
    GREEKS = "greeks"
    IV = "iv"
    VOLUME = "volume"


class CalendarDataType(str, Enum):
    """Calendar data type."""

    EARNINGS = "earnings"
    DIVIDENDS = "dividends"
    ECONOMIC = "economic"
    SPLITS = "splits"
    CUSTOM = "custom"


class AssumptionCategory(str, Enum):
    """Assumption category."""

    MARKET = "market"
    DATA = "data"
    EXECUTION = "execution"
    MODEL = "model"


class RiskCategory(str, Enum):
    """Risk category."""

    MARKET = "market"
    LIQUIDITY = "liquidity"
    EXECUTION = "execution"
    MODEL = "model"
    DATA = "data"
    OPERATIONAL = "operational"
    REGULATORY = "regulatory"


class RiskSeverity(str, Enum):
    """Risk severity level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DayOfWeek(str, Enum):
    """Day of week."""

    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"
    SUN = "sun"


# =============================================================================
# METADATA MODELS
# =============================================================================


class ClaimedPerformance(BaseModel):
    """Claimed performance metrics from source."""

    sharpe: float | None = Field(None, description="Claimed Sharpe ratio")
    cagr: float | None = Field(None, description="Claimed CAGR")
    max_drawdown: float | None = Field(None, description="Claimed max drawdown")
    sample_period: str | None = Field(None, description="Period of claimed performance")
    is_out_of_sample: bool | None = Field(None, description="Whether performance is out-of-sample")


class SourceCredibility(BaseModel):
    """Credibility assessment of the source."""

    source_type: SourceType = Field(..., description="Type of source")
    author_track_record: AuthorTrackRecord = Field(..., description="Author's track record")
    author_skin_in_game: bool = Field(..., description="Does author actually trade this?")
    author_conflicts: str | None = Field(None, description="Conflicts of interest")
    claimed_performance: ClaimedPerformance | None = Field(None, description="Claimed performance")


class StrategySource(BaseModel):
    """Source information for a strategy."""

    reference: str = Field(..., description="Where this came from")
    url: str | None = Field(None, description="URL if available")
    excerpt: str = Field(..., description="Key excerpt describing the strategy")
    hash: str = Field(..., description="SHA256 of source file")
    extracted_date: datetime = Field(..., description="When strategy was extracted")
    credibility: SourceCredibility | None = Field(None, description="Source credibility assessment")


class StrategyLineage(BaseModel):
    """Lineage information for derived strategies."""

    parents: list[str] = Field(..., description="Parent strategy IDs")
    relationship: LineageRelationship = Field(..., description="Relationship to parents")
    notes: str | None = Field(None, description="What was changed/combined")


class StrategyTags(BaseModel):
    """Tags for categorizing a strategy."""

    hypothesis_type: list[HypothesisType] = Field(
        default_factory=list, description="Types of hypothesis"
    )
    asset_class: list[AssetClass] = Field(default_factory=list, description="Asset classes")
    complexity: Complexity = Field(Complexity.MODERATE, description="Complexity level")


# =============================================================================
# HYPOTHESIS MODELS
# =============================================================================


class EdgeProvenance(BaseModel):
    """Provenance tracking for edge rationale."""

    source: ProvenanceSource = Field(..., description="Source of the rationale")
    confidence: ProvenanceConfidence = Field(..., description="Confidence level")
    research_notes: str | None = Field(None, description="How rationale was determined")
    factor_alignment: str | None = Field(None, description="Which known factor this aligns with")
    factor_alignment_tested: bool | None = Field(
        None, description="Has factor alignment been tested?"
    )


class StrategyEdge(BaseModel):
    """The 'why' framework for understanding the trading edge."""

    mechanism: str = Field(..., description="What drives returns")
    category: EdgeCategory = Field(..., description="Category of edge")
    why_exists: str = Field(..., description="Economic rationale")
    counterparty: str = Field(..., description="Who is on the other side")
    why_persists: str = Field(..., description="Why hasn't this been arbitraged away")
    decay_conditions: str = Field(..., description="When/why will this edge stop working")
    capacity_estimate: str | None = Field(None, description="Approximate capacity")
    provenance: EdgeProvenance | None = Field(None, description="Rationale provenance tracking")


class Hypothesis(BaseModel):
    """Strategy hypothesis."""

    summary: str = Field(..., max_length=200, description="One-line description")
    detail: str = Field(..., description="Full explanation")
    edge: StrategyEdge | None = Field(None, description="Edge framework")
    edge_source: str | None = Field(None, description="Legacy edge source field")


# =============================================================================
# UNIVERSE MODELS
# =============================================================================


class StaticInstrument(BaseModel):
    """A static instrument in the universe."""

    symbol: str = Field(..., description="Instrument symbol")
    asset_type: InstrumentAssetType = Field(..., description="Asset type")


class FilterCriterion(BaseModel):
    """A filter criterion for universe selection."""

    field: str = Field(..., description="Field to filter on")
    operator: FilterOperator = Field(..., description="Filter operator")
    value: Any = Field(..., description="Filter value")
    description: str | None = Field(None, description="Human-readable explanation")


class UniverseRequirement(BaseModel):
    """A data requirement for the universe."""

    requirement: str = Field(..., description="Requirement description")
    params: dict[str, Any] | None = Field(None, description="Requirement parameters")


class ResearchOutput(BaseModel):
    """Output from research phase."""

    name: str = Field(..., description="Output name")
    description: str = Field(..., description="Output description")
    selection_rule: str = Field(..., description="Selection rule")


class ResearchInputs(BaseModel):
    """Inputs for research-derived universe."""

    starting_universe: str = Field(..., description="Starting universe")
    data_required: list[str] = Field(default_factory=list, description="Required data")
    lookback: str = Field(..., description="Analysis lookback period")


class ResearchConfig(BaseModel):
    """Configuration for research-derived universe."""

    description: str = Field(..., description="Research description")
    method: ResearchMethod = Field(..., description="Research method")
    inputs: ResearchInputs = Field(..., description="Research inputs")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Method parameters")
    outputs: list[ResearchOutput] = Field(default_factory=list, description="Research outputs")
    tradeable: str = Field(..., description="Which output becomes the universe")


class SignalFilter(BaseModel):
    """Signal filter for signal-derived universe."""

    description: str = Field(..., description="Filter description")
    condition: str = Field(..., description="Filter condition")
    refresh: SignalRefresh = Field(..., description="Refresh frequency")


class Universe(BaseModel):
    """Trading universe configuration."""

    type: UniverseType = Field(..., description="Universe type")

    # For static type
    instruments: list[StaticInstrument] = Field(
        default_factory=list, description="Static instruments"
    )

    # For filtered type
    base: UniverseBase | None = Field(None, description="Base universe")
    custom_base: str | None = Field(None, description="Custom base description")
    criteria: list[FilterCriterion] = Field(
        default_factory=list, description="Filter criteria"
    )
    requires: list[UniverseRequirement] = Field(
        default_factory=list, description="Data requirements"
    )

    # For research_derived type
    research: ResearchConfig | None = Field(None, description="Research configuration")

    # For signal_derived type
    signal_filter: SignalFilter | None = Field(None, description="Signal filter")


# =============================================================================
# ENTRY MODELS
# =============================================================================


class TechnicalConfig(BaseModel):
    """Technical indicator entry configuration."""

    indicator: str = Field(..., description="Indicator name")
    params: dict[str, Any] = Field(default_factory=dict, description="Indicator parameters")
    condition: str = Field(..., description="Entry condition")


class EventTiming(BaseModel):
    """Event timing configuration."""

    reference: TimingReference = Field(..., description="Timing reference")
    offset: str = Field(..., description="Offset from event")


class EventConfig(BaseModel):
    """Event-driven entry configuration."""

    event_type: EventType = Field(..., description="Event type")
    custom_event: str | None = Field(None, description="Custom event description")
    timing: EventTiming = Field(..., description="Event timing")


class StatisticalThreshold(BaseModel):
    """Statistical threshold configuration."""

    entry: float = Field(..., description="Entry threshold")
    direction: ThresholdDirection = Field(..., description="Threshold direction")


class StatisticalConfig(BaseModel):
    """Statistical entry configuration."""

    metric: StatisticalMetric | str = Field(..., description="Statistical metric")
    params: dict[str, Any] = Field(default_factory=dict, description="Metric parameters")
    threshold: StatisticalThreshold = Field(..., description="Entry threshold")


class FundamentalConfig(BaseModel):
    """Fundamental entry configuration."""

    metrics: list[str] = Field(..., description="Fundamental metrics")
    condition: str = Field(..., description="Entry condition")


class AlternativeConfig(BaseModel):
    """Alternative data entry configuration."""

    data_source: AlternativeDataSource = Field(..., description="Data source")
    metric: str = Field(..., description="Metric to measure")
    condition: str = Field(..., description="Entry condition")


class CompoundCondition(BaseModel):
    """A condition in a compound entry."""

    type: EntryType = Field(..., description="Condition type")
    config: dict[str, Any] = Field(..., description="Type-specific configuration")


class CompoundConfig(BaseModel):
    """Compound entry configuration."""

    logic: CompoundLogic = Field(..., description="Combination logic")
    conditions: list[CompoundCondition] = Field(..., description="Conditions to combine")


class EntryFilter(BaseModel):
    """Entry filter."""

    name: str = Field(..., description="Filter name")
    description: str = Field(..., description="Filter description")
    condition: str = Field(..., description="Filter condition")


class EntryTiming(BaseModel):
    """Entry timing constraints."""

    allowed_days: list[DayOfWeek] | Literal["all"] = Field(
        "all", description="Allowed trading days"
    )
    allowed_hours: str = Field("all", description="Allowed trading hours")
    blackout_periods: list[str] = Field(
        default_factory=list, description="Blackout periods"
    )


class Entry(BaseModel):
    """Entry logic configuration."""

    type: EntryType = Field(..., description="Entry type")

    # Type-specific configurations
    technical: TechnicalConfig | None = Field(None, description="Technical config")
    event: EventConfig | None = Field(None, description="Event config")
    statistical: StatisticalConfig | None = Field(None, description="Statistical config")
    fundamental: FundamentalConfig | None = Field(None, description="Fundamental config")
    alternative: AlternativeConfig | None = Field(None, description="Alternative config")
    compound: CompoundConfig | None = Field(None, description="Compound config")

    # Common fields
    filters: list[EntryFilter] = Field(default_factory=list, description="Entry filters")
    timing: EntryTiming | None = Field(None, description="Timing constraints")


# =============================================================================
# POSITION MODELS
# =============================================================================


class OptionParams(BaseModel):
    """Option parameters for option legs."""

    option_type: OptionType = Field(..., description="Option type")
    strike_selection: StrikeSelection = Field(..., description="Strike selection method")
    strike_custom: str | None = Field(None, description="Custom strike description")
    expiry_selection: ExpirySelection = Field(..., description="Expiry selection method")
    expiry_custom: str | None = Field(None, description="Custom expiry description")


class LegInstrument(BaseModel):
    """Instrument specification for a leg."""

    source: InstrumentSource = Field(..., description="Instrument source")
    symbol: str | None = Field(None, description="Symbol for static source")
    selection: InstrumentSelection | None = Field(None, description="Selection method")
    rank_by: str | None = Field(None, description="Ranking metric")
    top_n: int | None = Field(None, description="Top N to select")
    reference: str | None = Field(None, description="Reference for signal/research")


class LegAllocation(BaseModel):
    """Allocation for a leg."""

    method: AllocationMethod = Field(..., description="Allocation method")
    value: float | str | None = Field(None, description="Allocation value")


class PositionLeg(BaseModel):
    """A leg of a position."""

    name: str = Field(..., description="Leg identifier")
    direction: Direction = Field(..., description="Position direction")
    instrument: LegInstrument = Field(..., description="Instrument specification")
    asset_type: InstrumentAssetType = Field(..., description="Asset type")
    option_params: OptionParams | None = Field(None, description="Option parameters")
    allocation: LegAllocation | None = Field(None, description="Allocation")


class PositionSizing(BaseModel):
    """Position sizing configuration."""

    method: SizingMethod = Field(..., description="Sizing method")
    params: dict[str, Any] = Field(default_factory=dict, description="Sizing parameters")


class PositionConstraints(BaseModel):
    """Position constraints."""

    max_positions: int | None = Field(None, description="Max number of positions")
    max_position_pct: float | None = Field(None, description="Max position percentage")
    max_sector_pct: float | None = Field(None, description="Max sector percentage")
    max_leverage: float | None = Field(None, description="Max leverage")
    max_concentration: float | None = Field(None, description="Max concentration")


class Position(BaseModel):
    """Position structure configuration."""

    type: PositionType = Field(..., description="Position type")
    legs: list[PositionLeg] = Field(..., min_length=1, description="Position legs")
    sizing: PositionSizing | None = Field(None, description="Sizing configuration")
    constraints: PositionConstraints | None = Field(None, description="Position constraints")


# =============================================================================
# EXIT MODELS
# =============================================================================


class ExitPath(BaseModel):
    """An exit path."""

    name: str = Field(..., description="Exit path name")
    type: ExitType = Field(..., description="Exit type")
    params: dict[str, Any] = Field(default_factory=dict, description="Type-specific params")
    condition_description: str | None = Field(None, description="Human-readable condition")
    action: str | None = Field(None, description="What happens when triggered")


class ExitFallback(BaseModel):
    """Fallback exit configuration."""

    type: ExitType = Field(..., description="Fallback exit type")
    hold_days: int | None = Field(None, description="Hold days for time-based")


class Exit(BaseModel):
    """Exit logic configuration."""

    paths: list[ExitPath] = Field(..., min_length=1, description="Exit paths")
    priority: ExitPriority = Field(
        ExitPriority.FIRST_TRIGGERED, description="Exit priority"
    )
    fallback: ExitFallback | None = Field(None, description="Fallback exit")


# =============================================================================
# POSITION MANAGEMENT MODELS
# =============================================================================


class ManagementTrigger(BaseModel):
    """Position management trigger."""

    type: ManagementTriggerType = Field(..., description="Trigger type")
    metric: str | None = Field(None, description="Metric for threshold trigger")
    condition: str | None = Field(None, description="Trigger condition")
    frequency: str | None = Field(None, description="Frequency for time trigger")
    signal: str | None = Field(None, description="Signal for signal trigger")


class ManagementAction(BaseModel):
    """Position management action."""

    type: ManagementActionType = Field(..., description="Action type")
    params: dict[str, Any] = Field(default_factory=dict, description="Action parameters")


class ManagementRule(BaseModel):
    """Position management rule."""

    name: str = Field(..., description="Rule name")
    trigger: ManagementTrigger = Field(..., description="Rule trigger")
    action: ManagementAction = Field(..., description="Rule action")
    description: str | None = Field(None, description="Human-readable description")


class PositionManagement(BaseModel):
    """Position management configuration."""

    enabled: bool = Field(False, description="Whether management is enabled")
    rules: list[ManagementRule] = Field(default_factory=list, description="Management rules")


# =============================================================================
# REGIME MODELS
# =============================================================================


class RegimeIndicator(BaseModel):
    """A regime indicator."""

    name: str = Field(..., description="Indicator name")
    source: str = Field(..., description="Data source")
    period: int | None = Field(None, description="Indicator period")


class RegimeDetectionParams(BaseModel):
    """Regime detection parameters."""

    indicators: list[RegimeIndicator] = Field(
        default_factory=list, description="Indicators used"
    )
    rules: dict[str, str] = Field(default_factory=dict, description="Regime classification rules")
    metric: str | None = Field(None, description="Metric for volatility regime")
    thresholds: dict[str, float] | None = Field(None, description="Threshold values")
    indicator: str | None = Field(None, description="Indicator for trend strength")
    threshold: float | None = Field(None, description="Single threshold value")
    price_vs_ma: str | None = Field(None, description="Price vs MA comparison")


class RegimeDetection(BaseModel):
    """Regime detection configuration."""

    method: RegimeDetectionMethod = Field(..., description="Detection method")
    params: RegimeDetectionParams | None = Field(None, description="Detection parameters")
    lookback: str = Field(..., description="Lookback period")


class RegimeMode(BaseModel):
    """A regime mode with its own entry/position/exit."""

    name: str = Field(..., description="Mode name")
    condition: str = Field(..., description="When this mode is active")

    # Mode-specific configurations (optional if action is flat)
    entry: Entry | None = Field(None, description="Entry configuration")
    position: Position | None = Field(None, description="Position configuration")
    exit: Exit | None = Field(None, description="Exit configuration")

    # Or no trading
    action: RegimeAction = Field(RegimeAction.TRADE, description="Trade or go flat")


class RegimeTransitions(BaseModel):
    """Regime transition configuration."""

    min_regime_duration: str = Field(..., description="Minimum regime duration")
    signal_on_change: bool = Field(False, description="Exit positions on regime change")


class Regimes(BaseModel):
    """Regime-adaptive configuration."""

    detection: RegimeDetection = Field(..., description="Regime detection")
    modes: list[RegimeMode] = Field(..., min_length=1, description="Regime modes")
    transitions: RegimeTransitions | None = Field(None, description="Transition rules")


# =============================================================================
# DATA REQUIREMENTS MODELS
# =============================================================================


class PriceDataRequirement(BaseModel):
    """Price data requirement."""

    type: PriceDataType = Field(..., description="Data type")
    instruments: list[str] | Literal["from_universe"] = Field(
        ..., description="Instruments or from_universe"
    )
    history_required: str = Field(..., description="Required history")


class FundamentalDataRequirement(BaseModel):
    """Fundamental data requirement."""

    field: str = Field(..., description="Data field")
    frequency: FundamentalFrequency = Field(..., description="Data frequency")


class OptionsDataRequirement(BaseModel):
    """Options data requirement."""

    data_type: OptionsDataType = Field(..., description="Data type")
    description: str | None = Field(None, description="Additional description")


class CalendarDataRequirement(BaseModel):
    """Calendar data requirement."""

    type: CalendarDataType = Field(..., description="Calendar type")
    description: str | None = Field(None, description="Additional description")


class AlternativeDataRequirement(BaseModel):
    """Alternative data requirement."""

    source: str = Field(..., description="Data source")
    provider: str | None = Field(None, description="Data provider")


class DerivedCalculation(BaseModel):
    """Derived calculation requirement."""

    name: str = Field(..., description="Calculation name")
    description: str = Field(..., description="Calculation description")
    inputs: list[str] = Field(default_factory=list, description="Input data")


class DataRequirements(BaseModel):
    """All data requirements."""

    price_data: list[PriceDataRequirement] = Field(
        default_factory=list, description="Price data requirements"
    )
    fundamental_data: list[FundamentalDataRequirement] = Field(
        default_factory=list, description="Fundamental data requirements"
    )
    options_data: list[OptionsDataRequirement] = Field(
        default_factory=list, description="Options data requirements"
    )
    calendar_data: list[CalendarDataRequirement] = Field(
        default_factory=list, description="Calendar data requirements"
    )
    alternative_data: list[AlternativeDataRequirement] = Field(
        default_factory=list, description="Alternative data requirements"
    )
    derived_calculations: list[DerivedCalculation] = Field(
        default_factory=list, description="Derived calculations"
    )


# =============================================================================
# ASSUMPTIONS AND RISKS
# =============================================================================


class Assumption(BaseModel):
    """A strategy assumption."""

    category: AssumptionCategory = Field(..., description="Assumption category")
    assumption: str = Field(..., description="The assumption")
    impact_if_wrong: str = Field(..., description="Impact if assumption is wrong")


class Risk(BaseModel):
    """A strategy risk."""

    category: RiskCategory = Field(..., description="Risk category")
    risk: str = Field(..., description="The risk")
    severity: RiskSeverity = Field(..., description="Risk severity")
    mitigation: str = Field(..., description="Risk mitigation")


# =============================================================================
# BACKTEST PARAMETERS
# =============================================================================


class BacktestParams(BaseModel):
    """Backtest parameters."""

    start_date: str | Literal["default"] = Field("default", description="Start date")
    end_date: str | Literal["default"] = Field("default", description="End date")
    initial_capital: float | Literal["default"] = Field(
        "default", description="Initial capital"
    )
    commission: float | Literal["default"] = Field("default", description="Commission")
    slippage: float | Literal["default"] = Field("default", description="Slippage")
    margin_requirement: float | None = Field(None, description="Margin requirement")


# =============================================================================
# MAIN STRATEGY MODEL
# =============================================================================


class V4Strategy(BaseModel):
    """Complete V4 strategy document.

    This is the main model that represents a full strategy document according
    to the V4 schema specification.
    """

    # Metadata
    id: str = Field(..., description="System-assigned ID")
    name: str = Field(..., description="Human-readable name")
    created: datetime = Field(..., description="Creation timestamp")
    status: StrategyStatus = Field(StrategyStatus.PENDING, description="Strategy status")

    source: StrategySource = Field(..., description="Source information")
    lineage: StrategyLineage | None = Field(None, description="Lineage information")
    tags: StrategyTags = Field(default_factory=StrategyTags, description="Strategy tags")

    # Hypothesis
    hypothesis: Hypothesis = Field(..., description="Strategy hypothesis")

    # Strategy mode
    strategy_mode: StrategyMode = Field(..., description="Strategy mode")

    # Universe
    universe: Universe = Field(..., description="Trading universe")

    # Entry/Position/Exit (for simple mode)
    entry: Entry | None = Field(None, description="Entry logic")
    position: Position | None = Field(None, description="Position structure")
    exit: Exit | None = Field(None, description="Exit logic")

    # Position management
    position_management: PositionManagement = Field(
        default_factory=PositionManagement, description="Position management"
    )

    # Regimes (for regime_adaptive mode)
    regimes: Regimes | None = Field(None, description="Regime configuration")

    # Data requirements
    data_requirements: DataRequirements = Field(
        default_factory=DataRequirements, description="Data requirements"
    )

    # Assumptions and risks
    assumptions: list[Assumption] = Field(
        default_factory=list, description="Strategy assumptions"
    )
    risks: list[Risk] = Field(default_factory=list, description="Strategy risks")

    # Backtest parameters
    backtest_params: BacktestParams | None = Field(None, description="Backtest parameters")

    @model_validator(mode="after")
    def validate_strategy_mode(self) -> "V4Strategy":
        """Validate that simple mode has entry/position/exit and regime_adaptive has regimes."""
        if self.strategy_mode == StrategyMode.SIMPLE:
            if self.entry is None and self.regimes is None:
                raise ValueError(
                    "Simple mode strategy must have entry, position, and exit defined"
                )
        elif self.strategy_mode == StrategyMode.REGIME_ADAPTIVE:
            if self.regimes is None:
                raise ValueError(
                    "Regime-adaptive strategy must have regimes defined"
                )
        return self

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
