"""Regime definitions and tagging schemas."""

from enum import Enum

from pydantic import BaseModel, Field


class MarketDirection(str, Enum):
    """Market direction regime."""

    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"


class VolatilityLevel(str, Enum):
    """Volatility regime."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class RateEnvironment(str, Enum):
    """Interest rate environment."""

    RISING = "rising"
    FLAT = "flat"
    FALLING = "falling"


class CapLeadership(str, Enum):
    """Market cap leadership."""

    LARGE = "large"
    SMALL = "small"
    MIXED = "mixed"


class SectorLeadership(str, Enum):
    """Sector leadership."""

    TECH = "tech"
    ENERGY = "energy"
    HEALTHCARE = "healthcare"
    FINANCIALS = "financials"
    CONSUMER = "consumer"
    INDUSTRIALS = "industrials"
    UTILITIES = "utilities"
    MATERIALS = "materials"
    REAL_ESTATE = "real_estate"
    COMMUNICATIONS = "communications"
    MIXED = "mixed"


class RegimeDefinition(BaseModel):
    """Configuration for how regimes are determined."""

    # Direction thresholds (SPY vs 200-day SMA)
    direction_bull_threshold: float = Field(0.05, description="Percent above SMA for bull")
    direction_bear_threshold: float = Field(-0.05, description="Percent below SMA for bear")

    # Volatility thresholds (VIX levels)
    volatility_low_threshold: float = Field(15.0, description="VIX below this = low")
    volatility_high_threshold: float = Field(25.0, description="VIX above this = high")

    # Rate thresholds (6-month change in basis points)
    rate_rising_threshold: float = Field(50.0, description="bps increase for rising")
    rate_falling_threshold: float = Field(-50.0, description="bps decrease for falling")

    # Cap leadership (IWM/SPY relative performance)
    cap_small_threshold: float = Field(
        0.05, description="IWM outperformance for small cap leadership"
    )
    cap_large_threshold: float = Field(
        -0.05, description="SPY outperformance for large cap leadership"
    )


class RegimeTags(BaseModel):
    """Regime tags for a specific time window."""

    direction: MarketDirection
    volatility: VolatilityLevel
    rate_environment: RateEnvironment
    sector_leader: SectorLeadership | None = None
    cap_leadership: CapLeadership | None = None

    def to_dict(self) -> dict[str, str]:
        """Convert to simple dict for storage."""
        result = {
            "direction": self.direction.value,
            "volatility": self.volatility.value,
            "rate_environment": self.rate_environment.value,
        }
        if self.sector_leader:
            result["sector_leader"] = self.sector_leader.value
        if self.cap_leadership:
            result["cap_leadership"] = self.cap_leadership.value
        return result


class RegimePerformanceEntry(BaseModel):
    """Performance in a specific regime."""

    mean_sharpe: float
    mean_cagr: float
    n_windows: int
    win_rate: float | None = None


class RegimePerformanceSummary(BaseModel):
    """Summary of performance across all regimes."""

    by_direction: dict[str, RegimePerformanceEntry] = Field(default_factory=dict)
    by_volatility: dict[str, RegimePerformanceEntry] = Field(default_factory=dict)
    by_rate_environment: dict[str, RegimePerformanceEntry] = Field(default_factory=dict)
    by_sector: dict[str, RegimePerformanceEntry] = Field(default_factory=dict)
    by_cap: dict[str, RegimePerformanceEntry] = Field(default_factory=dict)
