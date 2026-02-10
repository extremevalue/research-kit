"""V4 Validation module for strategy verification and walk-forward testing."""

from research_system.validation.verifier import (
    Verifier,
    VerificationResult,
    VerificationTest,
    VerificationStatus,
)
from research_system.validation.validator import (
    Validator,
    ValidationResult,
    ValidationGate,
    GateStatus,
    GateResult,
)
from research_system.validation.learner import (
    Learner,
    LearningsDocument,
    Learning,
)
from research_system.validation.ideator import (
    Ideator,
    StrategyIdea,
)
from research_system.validation.backtest import (
    BacktestExecutor,
    BacktestResult,
    WalkForwardResult,
    WalkForwardWindow,
)
from research_system.validation.runner import (
    Runner,
    RunResult,
)

# Backward-compat aliases
V4Verifier = Verifier
V4Validator = Validator
V4Learner = Learner
V4Ideator = Ideator
V4Runner = Runner
V4RunResult = RunResult

__all__ = [
    # Verifier
    "Verifier",
    "V4Verifier",
    "VerificationResult",
    "VerificationTest",
    "VerificationStatus",
    # Validator
    "Validator",
    "V4Validator",
    "ValidationResult",
    "ValidationGate",
    "GateStatus",
    "GateResult",
    # Learner
    "Learner",
    "V4Learner",
    "LearningsDocument",
    "Learning",
    # Ideator
    "Ideator",
    "V4Ideator",
    "StrategyIdea",
    # Backtest
    "BacktestExecutor",
    "BacktestResult",
    "WalkForwardResult",
    "WalkForwardWindow",
    # Runner
    "Runner",
    "V4Runner",
    "RunResult",
    "V4RunResult",
]
