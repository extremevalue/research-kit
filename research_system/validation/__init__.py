"""V4 Validation module for strategy verification and walk-forward testing."""

from research_system.validation.verifier import (
    V4Verifier,
    VerificationResult,
    VerificationTest,
    VerificationStatus,
)
from research_system.validation.validator import (
    V4Validator,
    ValidationResult,
    ValidationGate,
    GateStatus,
    GateResult,
)
from research_system.validation.learner import (
    V4Learner,
    LearningsDocument,
    Learning,
)
from research_system.validation.ideator import (
    V4Ideator,
    StrategyIdea,
)
from research_system.validation.backtest import (
    BacktestExecutor,
    BacktestResult,
    WalkForwardResult,
    WalkForwardWindow,
)
from research_system.validation.v4_runner import (
    V4Runner,
    V4RunResult,
)

__all__ = [
    # Verifier
    "V4Verifier",
    "VerificationResult",
    "VerificationTest",
    "VerificationStatus",
    # Validator
    "V4Validator",
    "ValidationResult",
    "ValidationGate",
    "GateStatus",
    "GateResult",
    # Learner
    "V4Learner",
    "LearningsDocument",
    "Learning",
    # Ideator
    "V4Ideator",
    "StrategyIdea",
    # Backtest
    "BacktestExecutor",
    "BacktestResult",
    "WalkForwardResult",
    "WalkForwardWindow",
    # Runner
    "V4Runner",
    "V4RunResult",
]
