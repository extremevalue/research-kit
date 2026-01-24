"""V4 Validation result models.

This module defines the validation result schema for V4 strategies, including:
- Validation status and run information
- Verification tests (pre-validation checks)
- Validation gates (thresholds to pass)
- Performance results and window metrics
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================


class ValidationStatus(str, Enum):
    """Status of validation."""

    NULL = "null"
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"


class VerificationTestStatus(str, Enum):
    """Status of a verification test."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# VERIFICATION TESTS
# =============================================================================


class VerificationTest(BaseModel):
    """A verification test result.

    Verification tests are run BEFORE validation to catch issues like:
    - Look-ahead bias
    - Survivorship bias
    - Position sizing errors
    - Data availability issues
    - Parameter sanity
    """

    test: str = Field(..., description="Test name/identifier")
    status: VerificationTestStatus = Field(..., description="Test result status")
    message: str = Field(..., description="Result message or details")


# Predefined verification tests
VERIFICATION_TESTS = [
    "look_ahead_bias",
    "survivorship_bias",
    "position_sizing",
    "data_availability",
    "parameter_sanity",
    "hardcoded_values",
]


def create_verification_test(
    test_name: str,
    passed: bool,
    message: str = "",
) -> VerificationTest:
    """Create a verification test result."""
    status = VerificationTestStatus.PASSED if passed else VerificationTestStatus.FAILED
    return VerificationTest(test=test_name, status=status, message=message)


def create_skipped_test(test_name: str, reason: str = "") -> VerificationTest:
    """Create a skipped verification test result."""
    return VerificationTest(
        test=test_name,
        status=VerificationTestStatus.SKIPPED,
        message=reason or "Test skipped",
    )


# =============================================================================
# VALIDATION GATES
# =============================================================================


class ValidationGates(BaseModel):
    """Validation gates/thresholds that a strategy must pass.

    These are the minimum performance criteria a strategy must meet
    to be considered validated.
    """

    min_sharpe: float = Field(0.5, description="Minimum Sharpe ratio")
    min_consistency: float = Field(0.6, description="Minimum consistency score")
    max_drawdown: float = Field(0.3, description="Maximum allowed drawdown")
    min_trades: int = Field(30, description="Minimum number of trades")

    def check_sharpe(self, sharpe: float) -> bool:
        """Check if Sharpe ratio meets threshold."""
        return sharpe >= self.min_sharpe

    def check_consistency(self, consistency: float) -> bool:
        """Check if consistency meets threshold."""
        return consistency >= self.min_consistency

    def check_drawdown(self, drawdown: float) -> bool:
        """Check if drawdown is within threshold (drawdown should be positive)."""
        return drawdown <= self.max_drawdown

    def check_trades(self, trades: int) -> bool:
        """Check if trade count meets threshold."""
        return trades >= self.min_trades


# =============================================================================
# VALIDATION RESULTS
# =============================================================================


class ValidationResults(BaseModel):
    """Performance results from validation.

    Contains the aggregate metrics from walk-forward validation.
    """

    sharpe: float | None = Field(None, description="Sharpe ratio")
    cagr: float | None = Field(None, description="Compound annual growth rate")
    total_return: float | None = Field(None, description="Total return")
    consistency: float | None = Field(
        None, description="Percentage of windows profitable"
    )
    max_drawdown: float | None = Field(None, description="Maximum drawdown")
    total_trades: int | None = Field(None, description="Total number of trades")
    win_rate: float | None = Field(None, description="Win rate")
    profit_factor: float | None = Field(None, description="Profit factor")


class ValidationWindow(BaseModel):
    """Performance metrics for a single validation window.

    Walk-forward validation tests strategy across multiple time windows
    to ensure robustness.
    """

    period: str = Field(..., description="Window period (e.g., '2020-01-01 to 2021-12-31')")
    sharpe: float | None = Field(None, description="Window Sharpe ratio")
    return_pct: float | None = Field(None, alias="return", description="Window return")
    max_drawdown: float | None = Field(None, description="Window max drawdown")
    trades: int | None = Field(None, description="Number of trades in window")

    class Config:
        """Pydantic configuration."""

        populate_by_name = True


# =============================================================================
# MAIN VALIDATION MODEL
# =============================================================================


class Validation(BaseModel):
    """Complete validation result for a strategy.

    This model contains all validation information including:
    - Current status
    - Verification test results
    - Applied gates/thresholds
    - Performance results
    - Window-by-window metrics
    - Notes
    """

    status: ValidationStatus | None = Field(None, description="Validation status")
    run_date: datetime | None = Field(None, description="When validation was run")

    verification_tests: list[VerificationTest] = Field(
        default_factory=list, description="Verification test results"
    )

    gates_applied: ValidationGates = Field(
        default_factory=ValidationGates, description="Applied validation gates"
    )

    results: ValidationResults = Field(
        default_factory=ValidationResults, description="Performance results"
    )

    windows: list[ValidationWindow] = Field(
        default_factory=list, description="Window-by-window results"
    )

    notes: str | None = Field(None, description="Additional notes")

    def is_validated(self) -> bool:
        """Check if strategy passed validation."""
        return self.status == ValidationStatus.PASSED

    def all_verification_tests_passed(self) -> bool:
        """Check if all verification tests passed."""
        return all(
            test.status == VerificationTestStatus.PASSED
            for test in self.verification_tests
            if test.status != VerificationTestStatus.SKIPPED
        )

    def passes_gates(self) -> bool:
        """Check if results pass all validation gates."""
        if self.results.sharpe is None:
            return False

        checks = [
            self.gates_applied.check_sharpe(self.results.sharpe),
        ]

        if self.results.consistency is not None:
            checks.append(self.gates_applied.check_consistency(self.results.consistency))

        if self.results.max_drawdown is not None:
            checks.append(self.gates_applied.check_drawdown(self.results.max_drawdown))

        if self.results.total_trades is not None:
            checks.append(self.gates_applied.check_trades(self.results.total_trades))

        return all(checks)

    def get_failed_verification_tests(self) -> list[VerificationTest]:
        """Get list of failed verification tests."""
        return [
            test
            for test in self.verification_tests
            if test.status == VerificationTestStatus.FAILED
        ]

    def compute_consistency(self) -> float | None:
        """Compute consistency score from windows."""
        if not self.windows:
            return None

        profitable_windows = sum(
            1 for w in self.windows if w.return_pct is not None and w.return_pct > 0
        )
        return profitable_windows / len(self.windows)
