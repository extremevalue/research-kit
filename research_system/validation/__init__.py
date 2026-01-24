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

__all__ = [
    "V4Verifier",
    "VerificationResult",
    "VerificationTest",
    "VerificationStatus",
    "V4Validator",
    "ValidationResult",
    "ValidationGate",
    "GateStatus",
    "GateResult",
    "V4Learner",
    "LearningsDocument",
    "Learning",
]
