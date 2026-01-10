"""Validation result schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from research_system.schemas.common import ConfidenceLevel, ValidationStatus
from research_system.schemas.regime import RegimePerformanceSummary, RegimeTags


class WindowMetrics(BaseModel):
    """Performance metrics for a single walk-forward window."""

    cagr: float = Field(..., description="Compound annual growth rate")
    sharpe: float = Field(..., description="Sharpe ratio")
    sortino: float | None = Field(None, description="Sortino ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown (as positive number)")
    win_rate: float | None = Field(None, description="Win rate of trades")
    profit_factor: float | None = Field(None, description="Profit factor")
    trades: int | None = Field(None, description="Number of trades")
    volatility: float | None = Field(None, description="Annualized volatility")


class WindowResult(BaseModel):
    """Result for a single walk-forward window."""

    window_id: int = Field(..., description="Window number (1-indexed)")
    start_date: str = Field(..., description="Window start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Window end date (YYYY-MM-DD)")
    metrics: WindowMetrics
    regime_tags: RegimeTags
    benchmark_cagr: float | None = Field(None, description="Benchmark CAGR for comparison")
    benchmark_sharpe: float | None = Field(None, description="Benchmark Sharpe for comparison")


class AggregateMetrics(BaseModel):
    """Aggregate metrics across all windows."""

    mean_sharpe: float
    sharpe_std: float
    sharpe_95_ci_low: float
    sharpe_95_ci_high: float

    mean_cagr: float
    cagr_std: float

    mean_max_drawdown: float
    worst_drawdown: float

    consistency_score: float = Field(
        ..., ge=0, le=1, description="Fraction of windows with positive Sharpe"
    )

    p_value: float = Field(..., description="p-value for strategy vs benchmark")
    p_value_adjusted: float = Field(..., description="FDR-adjusted p-value")


class PerformanceFingerprint(BaseModel):
    """Summary of when strategy works best/worst."""

    best_regimes: list[str] = Field(
        default_factory=list, description="Regimes where strategy excels"
    )
    worst_regimes: list[str] = Field(
        default_factory=list, description="Regimes where strategy struggles"
    )
    untested_regimes: list[str] = Field(
        default_factory=list, description="Regimes with insufficient data"
    )
    recommended_use: str = Field(..., description="Natural language recommendation")
    avoid_when: str | None = Field(None, description="When to avoid using strategy")


class ValidationResult(BaseModel):
    """Complete validation result for a strategy."""

    strategy_id: str = Field(..., description="ID of validated strategy")
    strategy_definition_hash: str = Field(..., description="Hash of strategy definition")
    generated_code_hash: str = Field(..., description="Hash of generated backtest code")
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Walk-forward results
    walk_forward_results: list[WindowResult] = Field(
        ..., min_length=1, description="Results for each time window"
    )

    # Aggregated analysis
    aggregate_metrics: AggregateMetrics
    regime_performance: RegimePerformanceSummary
    performance_fingerprint: PerformanceFingerprint

    # Final verdict
    validation_status: ValidationStatus
    confidence: ConfidenceLevel

    # Optional notes
    notes: str | None = None
    blocking_reason: str | None = Field(None, description="Reason if status is BLOCKED")

    def is_valid(self) -> bool:
        """Check if strategy passed validation."""
        return self.validation_status == ValidationStatus.PASSED

    def meets_threshold(
        self,
        min_sharpe: float = 0.5,
        min_consistency: float = 0.6,
        max_p_value: float = 0.1,
    ) -> bool:
        """Check if strategy meets quality thresholds."""
        return (
            self.aggregate_metrics.mean_sharpe >= min_sharpe
            and self.aggregate_metrics.consistency_score >= min_consistency
            and self.aggregate_metrics.p_value_adjusted <= max_p_value
        )
