"""
Validation pipeline components.

This module provides the mandatory gates and orchestration for the
research validation system.

Key Components:
    - data_audit: Gate 1 - Mandatory data checks before testing
    - sanity_checks: Flags exceptional results for review
    - statistical_analysis: Significance testing with Bonferroni correction
    - regime_analysis: Conditional performance analysis
    - orchestrator: State machine controlling the validation flow

Usage:
    from scripts.validate import ValidationOrchestrator
    from scripts.validate import audit_data_requirements
    from scripts.validate import check_backtest_sanity
    from scripts.validate import analyze_significance
    from scripts.validate import analyze_regimes
"""

from .data_audit import (
    audit_data_requirements,
    DataAuditResult,
    AuditCheck,
    AuditSeverity,
    save_audit_result,
)

from .sanity_checks import (
    check_backtest_sanity,
    SanityCheckResult,
    SanityFlag,
    FlagSeverity,
    save_sanity_result,
)

from .statistical_analysis import (
    analyze_significance,
    StatisticalAnalysisResult,
    TestResult,
    SignificanceLevel,
    calculate_bonferroni_threshold,
    save_statistical_result,
)

from .regime_analysis import (
    analyze_regimes,
    RegimeAnalysisResult,
    RegimePerformance,
    RegimeType,
    RegimeState,
    save_regime_result,
)

from .orchestrator import (
    ValidationOrchestrator,
    ValidationState,
    DeterminationStatus,
    ValidationGateError,
    StateTransitionError,
)

from .full_pipeline import (
    FullPipelineRunner,
    PipelineResult,
    BacktestResult,
    ExpertReview,
)

__all__ = [
    # Data Audit
    "audit_data_requirements",
    "DataAuditResult",
    "AuditCheck",
    "AuditSeverity",
    "save_audit_result",

    # Sanity Checks
    "check_backtest_sanity",
    "SanityCheckResult",
    "SanityFlag",
    "FlagSeverity",
    "save_sanity_result",

    # Statistical Analysis
    "analyze_significance",
    "StatisticalAnalysisResult",
    "TestResult",
    "SignificanceLevel",
    "calculate_bonferroni_threshold",
    "save_statistical_result",

    # Regime Analysis
    "analyze_regimes",
    "RegimeAnalysisResult",
    "RegimePerformance",
    "RegimeType",
    "RegimeState",
    "save_regime_result",

    # Orchestrator
    "ValidationOrchestrator",
    "ValidationState",
    "DeterminationStatus",
    "ValidationGateError",
    "StateTransitionError",

    # Full Pipeline
    "FullPipelineRunner",
    "PipelineResult",
    "BacktestResult",
    "ExpertReview",
]
