"""Tests for validation result schemas."""

import pytest
from pydantic import ValidationError

from research_system.schemas.common import ConfidenceLevel, ValidationStatus
from research_system.schemas.regime import (
    MarketDirection,
    RateEnvironment,
    RegimePerformanceSummary,
    RegimeTags,
    VolatilityLevel,
)
from research_system.schemas.validation import (
    AggregateMetrics,
    PerformanceFingerprint,
    ValidationResult,
    WindowMetrics,
    WindowResult,
)


class TestWindowMetrics:
    """Tests for WindowMetrics schema."""

    def test_required_fields(self):
        """Test that required fields must be provided."""
        # Should work with required fields
        metrics = WindowMetrics(cagr=0.15, sharpe=1.2, max_drawdown=0.12)
        assert metrics.cagr == 0.15
        assert metrics.sharpe == 1.2
        assert metrics.max_drawdown == 0.12

    def test_optional_fields_default_to_none(self):
        """Test that optional fields default to None."""
        metrics = WindowMetrics(cagr=0.15, sharpe=1.2, max_drawdown=0.12)
        assert metrics.sortino is None
        assert metrics.win_rate is None
        assert metrics.profit_factor is None
        assert metrics.trades is None
        assert metrics.volatility is None

    def test_all_fields_populated(self):
        """Test creating metrics with all fields."""
        metrics = WindowMetrics(
            cagr=0.15,
            sharpe=1.2,
            sortino=1.5,
            max_drawdown=0.12,
            win_rate=0.55,
            profit_factor=1.8,
            trades=42,
            volatility=0.18,
        )
        assert metrics.sortino == 1.5
        assert metrics.trades == 42


class TestWindowResult:
    """Tests for WindowResult schema."""

    def test_window_result_creation(self):
        """Test creating a window result."""
        result = WindowResult(
            window_id=1,
            start_date="2020-01-01",
            end_date="2020-12-31",
            metrics=WindowMetrics(cagr=0.15, sharpe=1.2, max_drawdown=0.12),
            regime_tags=RegimeTags(
                direction=MarketDirection.BULL,
                volatility=VolatilityLevel.NORMAL,
                rate_environment=RateEnvironment.FALLING,
            ),
        )
        assert result.window_id == 1
        assert result.start_date == "2020-01-01"
        assert result.metrics.cagr == 0.15

    def test_window_result_with_benchmark(self):
        """Test window result includes benchmark data."""
        result = WindowResult(
            window_id=1,
            start_date="2020-01-01",
            end_date="2020-12-31",
            metrics=WindowMetrics(cagr=0.15, sharpe=1.2, max_drawdown=0.12),
            regime_tags=RegimeTags(
                direction=MarketDirection.BULL,
                volatility=VolatilityLevel.NORMAL,
                rate_environment=RateEnvironment.FALLING,
            ),
            benchmark_cagr=0.10,
            benchmark_sharpe=0.8,
        )
        assert result.benchmark_cagr == 0.10
        assert result.benchmark_sharpe == 0.8


class TestAggregateMetrics:
    """Tests for AggregateMetrics schema."""

    def test_aggregate_metrics_creation(self):
        """Test creating aggregate metrics."""
        metrics = AggregateMetrics(
            mean_sharpe=1.1,
            sharpe_std=0.3,
            sharpe_95_ci_low=0.5,
            sharpe_95_ci_high=1.7,
            mean_cagr=0.12,
            cagr_std=0.05,
            mean_max_drawdown=0.15,
            worst_drawdown=0.25,
            consistency_score=0.75,
            p_value=0.03,
            p_value_adjusted=0.05,
        )
        assert metrics.mean_sharpe == 1.1
        assert metrics.consistency_score == 0.75

    def test_consistency_score_bounds(self):
        """Test that consistency_score must be between 0 and 1."""
        # Valid boundary values
        metrics = AggregateMetrics(
            mean_sharpe=1.0,
            sharpe_std=0.3,
            sharpe_95_ci_low=0.5,
            sharpe_95_ci_high=1.5,
            mean_cagr=0.1,
            cagr_std=0.05,
            mean_max_drawdown=0.1,
            worst_drawdown=0.2,
            consistency_score=0.0,  # Minimum valid
            p_value=0.05,
            p_value_adjusted=0.05,
        )
        assert metrics.consistency_score == 0.0

        metrics = AggregateMetrics(
            mean_sharpe=1.0,
            sharpe_std=0.3,
            sharpe_95_ci_low=0.5,
            sharpe_95_ci_high=1.5,
            mean_cagr=0.1,
            cagr_std=0.05,
            mean_max_drawdown=0.1,
            worst_drawdown=0.2,
            consistency_score=1.0,  # Maximum valid
            p_value=0.05,
            p_value_adjusted=0.05,
        )
        assert metrics.consistency_score == 1.0

    def test_consistency_score_invalid_bounds(self):
        """Test that invalid consistency_score raises error."""
        with pytest.raises(ValidationError):
            AggregateMetrics(
                mean_sharpe=1.0,
                sharpe_std=0.3,
                sharpe_95_ci_low=0.5,
                sharpe_95_ci_high=1.5,
                mean_cagr=0.1,
                cagr_std=0.05,
                mean_max_drawdown=0.1,
                worst_drawdown=0.2,
                consistency_score=1.5,  # Invalid - above 1
                p_value=0.05,
                p_value_adjusted=0.05,
            )


class TestPerformanceFingerprint:
    """Tests for PerformanceFingerprint schema."""

    def test_fingerprint_creation(self):
        """Test creating a performance fingerprint."""
        fingerprint = PerformanceFingerprint(
            best_regimes=["bull_low_vol", "sideways_normal"],
            worst_regimes=["bear_high_vol"],
            untested_regimes=["bear_low_vol"],
            recommended_use="Use in trending markets with moderate volatility",
            avoid_when="High volatility bear markets",
        )
        assert len(fingerprint.best_regimes) == 2
        assert "bull_low_vol" in fingerprint.best_regimes

    def test_fingerprint_minimal(self):
        """Test fingerprint with only required fields."""
        fingerprint = PerformanceFingerprint(
            recommended_use="General purpose momentum strategy",
        )
        assert fingerprint.best_regimes == []
        assert fingerprint.avoid_when is None


class TestValidationResult:
    """Tests for ValidationResult schema."""

    def _create_valid_result(self, **overrides):
        """Helper to create a valid ValidationResult."""
        defaults = {
            "strategy_id": "STRAT-001",
            "strategy_definition_hash": "sha256:abc123",
            "generated_code_hash": "sha256:def456",
            "walk_forward_results": [
                WindowResult(
                    window_id=1,
                    start_date="2020-01-01",
                    end_date="2020-12-31",
                    metrics=WindowMetrics(cagr=0.15, sharpe=1.2, max_drawdown=0.12),
                    regime_tags=RegimeTags(
                        direction=MarketDirection.BULL,
                        volatility=VolatilityLevel.NORMAL,
                        rate_environment=RateEnvironment.FALLING,
                    ),
                ),
            ],
            "aggregate_metrics": AggregateMetrics(
                mean_sharpe=1.1,
                sharpe_std=0.3,
                sharpe_95_ci_low=0.5,
                sharpe_95_ci_high=1.7,
                mean_cagr=0.12,
                cagr_std=0.05,
                mean_max_drawdown=0.15,
                worst_drawdown=0.25,
                consistency_score=0.75,
                p_value=0.03,
                p_value_adjusted=0.05,
            ),
            "regime_performance": RegimePerformanceSummary(),
            "performance_fingerprint": PerformanceFingerprint(
                recommended_use="General use",
            ),
            "validation_status": ValidationStatus.PASSED,
            "confidence": ConfidenceLevel.HIGH,
        }
        defaults.update(overrides)
        return ValidationResult(**defaults)

    def test_validation_result_creation(self):
        """Test creating a full validation result."""
        result = self._create_valid_result()
        assert result.strategy_id == "STRAT-001"
        assert result.validation_status == ValidationStatus.PASSED

    def test_is_valid_method(self):
        """Test is_valid() returns correct status."""
        passed = self._create_valid_result(validation_status=ValidationStatus.PASSED)
        assert passed.is_valid() is True

        failed = self._create_valid_result(validation_status=ValidationStatus.FAILED)
        assert failed.is_valid() is False

        error = self._create_valid_result(validation_status=ValidationStatus.ERROR)
        assert error.is_valid() is False

    def test_meets_threshold_default(self):
        """Test meets_threshold with default parameters."""
        # Good strategy
        good = self._create_valid_result()
        assert good.meets_threshold() is True

        # Bad sharpe
        bad_sharpe = self._create_valid_result(
            aggregate_metrics=AggregateMetrics(
                mean_sharpe=0.3,  # Below 0.5 threshold
                sharpe_std=0.3,
                sharpe_95_ci_low=-0.1,
                sharpe_95_ci_high=0.7,
                mean_cagr=0.05,
                cagr_std=0.05,
                mean_max_drawdown=0.15,
                worst_drawdown=0.25,
                consistency_score=0.75,
                p_value=0.03,
                p_value_adjusted=0.05,
            ),
        )
        assert bad_sharpe.meets_threshold() is False

    def test_meets_threshold_custom(self):
        """Test meets_threshold with custom parameters."""
        result = self._create_valid_result()

        # Should pass with lenient thresholds
        assert result.meets_threshold(min_sharpe=0.5, min_consistency=0.5) is True

        # Should fail with strict thresholds
        assert result.meets_threshold(min_sharpe=2.0) is False

    def test_walk_forward_requires_at_least_one_window(self):
        """Test that at least one walk-forward window is required."""
        with pytest.raises(ValidationError):
            self._create_valid_result(walk_forward_results=[])

    def test_validation_result_json_roundtrip(self):
        """Test JSON serialization round-trip."""
        result = self._create_valid_result()
        json_str = result.model_dump_json()
        restored = ValidationResult.model_validate_json(json_str)

        assert restored.strategy_id == result.strategy_id
        assert restored.validation_status == result.validation_status
        assert restored.aggregate_metrics.mean_sharpe == result.aggregate_metrics.mean_sharpe

    def test_blocked_result_with_reason(self):
        """Test blocked result includes blocking reason."""
        result = self._create_valid_result(
            validation_status=ValidationStatus.BLOCKED,
            blocking_reason="Insufficient historical data for validation",
        )
        assert result.validation_status == ValidationStatus.BLOCKED
        assert "Insufficient" in result.blocking_reason
