"""
Validation orchestrator - main state machine for the validation pipeline.

Controls the flow of validation, enforces mandatory gates, and manages state.
The state machine ensures no step can be skipped:

HYPOTHESIS → DATA_AUDIT → IS_TESTING → STATISTICAL → REGIME → OOS → DETERMINATION

Usage:
    from scripts.validate.orchestrator import ValidationOrchestrator

    orchestrator = ValidationOrchestrator("IND-002")
    orchestrator.start()

    # Each step must complete before moving to next
    orchestrator.submit_hypothesis(hypothesis)
    orchestrator.run_data_audit()
    orchestrator.run_is_testing(backtest_results)
    orchestrator.run_statistical_analysis()
    orchestrator.run_regime_analysis()
    orchestrator.run_oos_testing(oos_results)  # ONE SHOT - no retries
    orchestrator.make_determination()
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from scripts.utils.logging_config import get_logger, LogContext
from scripts.utils.schema_validator import validate_hypothesis

logger = get_logger("orchestrator")

# Validation directories
VALIDATIONS_DIR = Path(__file__).parent.parent.parent / "validations"


class ValidationState(Enum):
    """States in the validation pipeline."""
    INITIALIZED = "initialized"
    HYPOTHESIS = "hypothesis"
    DATA_AUDIT = "data_audit"
    IS_TESTING = "is_testing"
    STATISTICAL = "statistical"
    REGIME = "regime"
    OOS_TESTING = "oos_testing"
    DETERMINATION = "determination"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class DeterminationStatus(Enum):
    """Final determination outcomes."""
    VALIDATED = "VALIDATED"
    CONDITIONAL = "CONDITIONAL"
    INVALIDATED = "INVALIDATED"


@dataclass
class StateTransition:
    """Record of a state transition."""
    from_state: str
    to_state: str
    timestamp: str
    passed: bool
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class ValidationMetadata:
    """Validation state tracking."""
    component_id: str
    current_state: ValidationState = ValidationState.INITIALIZED
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    state_history: List[StateTransition] = field(default_factory=list)
    locked_parameters: Dict[str, Any] = field(default_factory=dict)
    sanity_flags: List[Dict[str, Any]] = field(default_factory=list)
    determination: Optional[str] = None
    determination_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "current_state": self.current_state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "state_history": [
                {
                    "from_state": t.from_state,
                    "to_state": t.to_state,
                    "timestamp": t.timestamp,
                    "passed": t.passed,
                    "details": t.details,
                    "error": t.error
                }
                for t in self.state_history
            ],
            "locked_parameters": self.locked_parameters,
            "sanity_flags": self.sanity_flags,
            "determination": self.determination,
            "determination_reason": self.determination_reason
        }


class ValidationGateError(Exception):
    """Raised when a validation gate fails."""
    pass


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


class ValidationOrchestrator:
    """
    Orchestrates the validation pipeline with enforced state machine.

    Ensures:
    - Each gate must pass before proceeding
    - Parameters are locked before testing
    - OOS is one-shot (no retries)
    - All results are persisted
    """

    # Valid state transitions
    VALID_TRANSITIONS = {
        ValidationState.INITIALIZED: [ValidationState.HYPOTHESIS],
        ValidationState.HYPOTHESIS: [ValidationState.DATA_AUDIT, ValidationState.BLOCKED],
        ValidationState.DATA_AUDIT: [ValidationState.IS_TESTING, ValidationState.BLOCKED],
        ValidationState.IS_TESTING: [ValidationState.STATISTICAL, ValidationState.FAILED],
        ValidationState.STATISTICAL: [ValidationState.REGIME, ValidationState.FAILED],
        ValidationState.REGIME: [ValidationState.OOS_TESTING, ValidationState.FAILED],
        ValidationState.OOS_TESTING: [ValidationState.DETERMINATION],
        ValidationState.DETERMINATION: [ValidationState.COMPLETED],
    }

    def __init__(self, component_id: str, validation_dir: Optional[Path] = None):
        """
        Initialize orchestrator for a component.

        Args:
            component_id: Catalog entry ID (e.g., "IND-002")
            validation_dir: Optional custom validation directory
        """
        self.component_id = component_id
        self.validation_dir = validation_dir or (VALIDATIONS_DIR / component_id)
        self.validation_dir.mkdir(parents=True, exist_ok=True)

        self.metadata_file = self.validation_dir / "metadata.json"
        self.hypothesis_file = self.validation_dir / "hypothesis.json"

        # Load or create metadata
        if self.metadata_file.exists():
            self.metadata = self._load_metadata()
        else:
            self.metadata = ValidationMetadata(component_id=component_id)
            self._save_metadata()

        logger.info(f"Orchestrator initialized for {component_id}, state: {self.metadata.current_state.value}")

    def _load_metadata(self) -> ValidationMetadata:
        """Load metadata from disk."""
        with open(self.metadata_file, 'r') as f:
            data = json.load(f)

        metadata = ValidationMetadata(
            component_id=data["component_id"],
            current_state=ValidationState(data["current_state"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            locked_parameters=data.get("locked_parameters", {}),
            sanity_flags=data.get("sanity_flags", []),
            determination=data.get("determination"),
            determination_reason=data.get("determination_reason")
        )

        # Reconstruct state history
        for t in data.get("state_history", []):
            metadata.state_history.append(StateTransition(
                from_state=t["from_state"],
                to_state=t["to_state"],
                timestamp=t["timestamp"],
                passed=t["passed"],
                details=t.get("details"),
                error=t.get("error")
            ))

        return metadata

    def _save_metadata(self):
        """Save metadata to disk."""
        self.metadata.updated_at = datetime.utcnow().isoformat() + "Z"
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata.to_dict(), f, indent=2)

    def _transition_state(
        self,
        new_state: ValidationState,
        passed: bool = True,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Transition to a new state with validation."""
        current = self.metadata.current_state

        # Check if transition is valid
        if new_state not in self.VALID_TRANSITIONS.get(current, []):
            raise StateTransitionError(
                f"Invalid transition from {current.value} to {new_state.value}. "
                f"Valid transitions: {[s.value for s in self.VALID_TRANSITIONS.get(current, [])]}"
            )

        # Record transition
        transition = StateTransition(
            from_state=current.value,
            to_state=new_state.value,
            timestamp=datetime.utcnow().isoformat() + "Z",
            passed=passed,
            details=details,
            error=error
        )
        self.metadata.state_history.append(transition)
        self.metadata.current_state = new_state
        self._save_metadata()

        logger.info(f"State transition: {current.value} -> {new_state.value} (passed={passed})")

    @property
    def current_state(self) -> ValidationState:
        """Get current state."""
        return self.metadata.current_state

    def require_state(self, *required_states: ValidationState):
        """Ensure current state is one of the required states."""
        if self.metadata.current_state not in required_states:
            raise StateTransitionError(
                f"Invalid state: {self.metadata.current_state.value}. "
                f"Required: {[s.value for s in required_states]}"
            )

    def start(self) -> bool:
        """Start a new validation (reset if already exists)."""
        with LogContext(logger, "Start Validation", component_id=self.component_id):
            if self.metadata.current_state != ValidationState.INITIALIZED:
                logger.warning(f"Validation already started, current state: {self.metadata.current_state.value}")
                return False

            logger.info(f"Starting validation for {self.component_id}")
            return True

    def submit_hypothesis(self, hypothesis: Dict[str, Any]) -> bool:
        """
        Submit and lock hypothesis before testing.

        The hypothesis must include:
        - data_requirements: List of data source IDs
        - is_period: In-sample period {start, end}
        - oos_period: Out-of-sample period {start, end}
        - hypothesis_statement: Testable hypothesis

        Args:
            hypothesis: Hypothesis document

        Returns:
            True if hypothesis accepted, raises on error
        """
        with LogContext(logger, "Submit Hypothesis", component_id=self.component_id):
            self.require_state(ValidationState.INITIALIZED, ValidationState.HYPOTHESIS)

            # Validate hypothesis schema
            validation_result = validate_hypothesis(hypothesis)
            if not validation_result.valid:
                raise ValidationGateError(
                    f"Hypothesis validation failed: {validation_result.errors}"
                )

            # Lock parameters - these cannot change after this point
            self.metadata.locked_parameters = {
                "is_period": hypothesis.get("is_period"),
                "oos_period": hypothesis.get("oos_period"),
                "data_requirements": hypothesis.get("data_requirements"),
                "parameters": hypothesis.get("parameters", {}),
                "locked_at": datetime.utcnow().isoformat() + "Z"
            }

            # Save hypothesis
            with open(self.hypothesis_file, 'w') as f:
                json.dump(hypothesis, f, indent=2)

            self._transition_state(
                ValidationState.HYPOTHESIS,
                passed=True,
                details={"hypothesis_locked": True}
            )

            logger.info("Hypothesis submitted and parameters locked")
            return True

    def run_data_audit(self) -> bool:
        """
        Run mandatory data audit (Gate 1).

        Must pass before any testing can proceed.

        Returns:
            True if audit passed, raises ValidationGateError on failure
        """
        with LogContext(logger, "Data Audit", component_id=self.component_id):
            self.require_state(ValidationState.HYPOTHESIS)

            # Load hypothesis
            with open(self.hypothesis_file, 'r') as f:
                hypothesis = json.load(f)

            # Import and run audit
            from scripts.validate.data_audit import audit_data_requirements, save_audit_result

            audit_result = audit_data_requirements(self.component_id, hypothesis)
            save_audit_result(audit_result, self.validation_dir)

            if not audit_result.passed:
                self._transition_state(
                    ValidationState.BLOCKED,
                    passed=False,
                    details={"blocking_issues": audit_result.blocking_issues},
                    error="Data audit failed - blocking issues found"
                )
                raise ValidationGateError(
                    f"Data audit failed: {audit_result.blocking_issues}"
                )

            self._transition_state(
                ValidationState.DATA_AUDIT,
                passed=True,
                details={
                    "checks_passed": len([c for c in audit_result.checks if c.passed]),
                    "warnings": audit_result.warnings
                }
            )

            logger.info("Data audit passed")
            return True

    def submit_is_results(
        self,
        backtest_results: Dict[str, Any],
        baseline_results: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Submit in-sample backtest results.

        Args:
            backtest_results: Results from IS backtest
            baseline_results: Optional baseline for comparison

        Returns:
            True if results accepted
        """
        with LogContext(logger, "IS Testing", component_id=self.component_id):
            self.require_state(ValidationState.DATA_AUDIT)

            # Run sanity checks
            from scripts.validate.sanity_checks import check_backtest_sanity, save_sanity_result

            sanity_result = check_backtest_sanity(
                self.component_id,
                backtest_results,
                "is",
                baseline_results
            )
            save_sanity_result(sanity_result, self.validation_dir / "is_test")

            # Store any sanity flags
            if sanity_result.flags:
                self.metadata.sanity_flags.extend([f.to_dict() for f in sanity_result.flags])
                self._save_metadata()

            # Save IS results
            is_dir = self.validation_dir / "is_test"
            is_dir.mkdir(parents=True, exist_ok=True)

            results_file = is_dir / "results.json"
            with open(results_file, 'w') as f:
                json.dump({
                    "backtest_results": backtest_results,
                    "baseline_results": baseline_results,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, f, indent=2)

            # Check if results meet minimum thresholds
            alpha = backtest_results.get("alpha", 0) or backtest_results.get("annual_alpha", 0)
            sharpe = backtest_results.get("sharpe_ratio", 0) or backtest_results.get("sharpe", 0)

            # Convert if needed
            if abs(alpha) > 1:
                alpha = alpha / 100

            passed = True
            failure_reasons = []

            if alpha < 0.01:  # 1% minimum
                passed = False
                failure_reasons.append(f"Alpha {alpha:.2%} < 1% minimum")

            if baseline_results:
                baseline_sharpe = baseline_results.get("sharpe_ratio", 0)
                if sharpe - baseline_sharpe < 0.10:  # 0.10 Sharpe improvement
                    passed = False
                    failure_reasons.append(
                        f"Sharpe improvement {sharpe - baseline_sharpe:.2f} < 0.10 minimum"
                    )

            if not passed:
                self._transition_state(
                    ValidationState.FAILED,
                    passed=False,
                    details={"failure_reasons": failure_reasons},
                    error="IS testing did not meet minimum thresholds"
                )
                logger.warning(f"IS testing failed: {failure_reasons}")
                return False

            self._transition_state(
                ValidationState.IS_TESTING,
                passed=True,
                details={
                    "alpha": alpha,
                    "sharpe": sharpe,
                    "sanity_flags": len(sanity_result.flags)
                }
            )

            logger.info(f"IS testing complete: alpha={alpha:.2%}, sharpe={sharpe:.2f}")
            return True

    def run_statistical_analysis(self) -> bool:
        """
        Run statistical significance analysis.

        Returns:
            True if statistically significant
        """
        with LogContext(logger, "Statistical Analysis", component_id=self.component_id):
            self.require_state(ValidationState.IS_TESTING)

            # Load IS results
            is_results_file = self.validation_dir / "is_test" / "results.json"
            with open(is_results_file, 'r') as f:
                is_data = json.load(f)

            # Import and run analysis
            from scripts.validate.statistical_analysis import analyze_significance, save_statistical_result

            test_results = [{"name": "is_test", "results": is_data["backtest_results"]}]
            baseline = is_data.get("baseline_results")

            stat_result = analyze_significance(
                self.component_id,
                test_results,
                baseline,
                n_comparisons=1  # Single test for now
            )
            save_statistical_result(stat_result, self.validation_dir)

            if not stat_result.any_significant:
                self._transition_state(
                    ValidationState.FAILED,
                    passed=False,
                    details=stat_result.summary,
                    error="Results not statistically significant"
                )
                logger.warning("Statistical analysis failed: not significant")
                return False

            self._transition_state(
                ValidationState.STATISTICAL,
                passed=True,
                details=stat_result.summary
            )

            logger.info(f"Statistical analysis passed: p={stat_result.summary['lowest_p_value']:.4f}")
            return True

    def run_regime_analysis(self) -> bool:
        """
        Run regime-conditional performance analysis.

        Returns:
            True if regime analysis complete (informational, doesn't block)
        """
        with LogContext(logger, "Regime Analysis", component_id=self.component_id):
            self.require_state(ValidationState.STATISTICAL)

            # Import and run regime analysis
            from scripts.validate.regime_analysis import analyze_regimes, save_regime_result

            # Load IS results
            is_results_file = self.validation_dir / "is_test" / "results.json"
            with open(is_results_file, 'r') as f:
                is_data = json.load(f)

            regime_result = analyze_regimes(
                self.component_id,
                is_data["backtest_results"]
            )
            save_regime_result(regime_result, self.validation_dir)

            self._transition_state(
                ValidationState.REGIME,
                passed=True,
                details={
                    "regime_count": len(regime_result.regime_results),
                    "consistent_across_regimes": regime_result.consistent_across_regimes
                }
            )

            logger.info("Regime analysis complete")
            return True

    def submit_oos_results(self, oos_results: Dict[str, Any]) -> bool:
        """
        Submit out-of-sample results (ONE SHOT - no retries).

        This is the final test. Once submitted, the determination is made.
        There are no retries or adjustments allowed.

        Args:
            oos_results: Results from OOS backtest

        Returns:
            True (always proceeds to determination)
        """
        with LogContext(logger, "OOS Testing", component_id=self.component_id):
            self.require_state(ValidationState.REGIME)

            # Check if OOS already submitted (no retries!)
            oos_dir = self.validation_dir / "oos_test"
            results_file = oos_dir / "results.json"

            if results_file.exists():
                raise ValidationGateError(
                    "OOS results already submitted. NO RETRIES ALLOWED. "
                    "The OOS test is one-shot to prevent p-hacking."
                )

            # Run sanity checks
            from scripts.validate.sanity_checks import check_backtest_sanity, save_sanity_result

            sanity_result = check_backtest_sanity(
                self.component_id,
                oos_results,
                "oos"
            )

            oos_dir.mkdir(parents=True, exist_ok=True)
            save_sanity_result(sanity_result, oos_dir)

            # Store any sanity flags
            if sanity_result.flags:
                self.metadata.sanity_flags.extend([f.to_dict() for f in sanity_result.flags])

            # Save OOS results
            with open(results_file, 'w') as f:
                json.dump({
                    "oos_results": oos_results,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, f, indent=2)

            self._transition_state(
                ValidationState.OOS_TESTING,
                passed=True,
                details={"sanity_flags": len(sanity_result.flags)}
            )

            logger.info("OOS results submitted - proceeding to determination")
            return True

    def make_determination(self) -> DeterminationStatus:
        """
        Make final determination based on all evidence.

        Criteria:
        - VALIDATED: OOS alpha > 0%, p < 0.05, IS alpha > 1%
        - CONDITIONAL: Above but regime-specific or with caveats
        - INVALIDATED: Failed IS, statistical, or OOS

        Returns:
            DeterminationStatus enum
        """
        with LogContext(logger, "Determination", component_id=self.component_id):
            self.require_state(ValidationState.OOS_TESTING)

            # Load all results
            is_results_file = self.validation_dir / "is_test" / "results.json"
            oos_results_file = self.validation_dir / "oos_test" / "results.json"
            stat_file = self.validation_dir / "statistical_analysis.json"
            regime_file = self.validation_dir / "regime_analysis.json"

            with open(is_results_file, 'r') as f:
                is_data = json.load(f)
            with open(oos_results_file, 'r') as f:
                oos_data = json.load(f)
            with open(stat_file, 'r') as f:
                stat_data = json.load(f)

            # Check regime analysis if exists
            regime_consistent = True
            if regime_file.exists():
                with open(regime_file, 'r') as f:
                    regime_data = json.load(f)
                regime_consistent = regime_data.get("consistent_across_regimes", True)

            # Extract key metrics
            oos_results = oos_data["oos_results"]
            oos_alpha = oos_results.get("alpha", 0) or oos_results.get("annual_alpha", 0)
            if abs(oos_alpha) > 1:
                oos_alpha = oos_alpha / 100

            is_results = is_data["backtest_results"]
            is_alpha = is_results.get("alpha", 0) or is_results.get("annual_alpha", 0)
            if abs(is_alpha) > 1:
                is_alpha = is_alpha / 100

            stat_significant = stat_data.get("any_significant", False)

            # Determine outcome
            reasons = []

            if oos_alpha <= 0:
                status = DeterminationStatus.INVALIDATED
                reasons.append(f"OOS alpha {oos_alpha:.2%} <= 0%")
            elif not stat_significant:
                status = DeterminationStatus.INVALIDATED
                reasons.append("Not statistically significant")
            elif is_alpha < 0.01:
                status = DeterminationStatus.INVALIDATED
                reasons.append(f"IS alpha {is_alpha:.2%} < 1%")
            elif not regime_consistent:
                status = DeterminationStatus.CONDITIONAL
                reasons.append("Works in specific regimes only")
            elif len(self.metadata.sanity_flags) > 0:
                # Check if any critical flags
                critical_flags = [f for f in self.metadata.sanity_flags if f.get("severity") == "critical"]
                if critical_flags:
                    status = DeterminationStatus.INVALIDATED
                    reasons.append("Critical sanity flags raised")
                else:
                    status = DeterminationStatus.CONDITIONAL
                    reasons.append("Sanity flags require monitoring")
            else:
                status = DeterminationStatus.VALIDATED
                reasons.append(f"IS alpha: {is_alpha:.2%}, OOS alpha: {oos_alpha:.2%}")

            # Save determination
            self.metadata.determination = status.value
            self.metadata.determination_reason = "; ".join(reasons)

            determination_doc = {
                "status": status.value,
                "reasons": reasons,
                "is_alpha": is_alpha,
                "oos_alpha": oos_alpha,
                "stat_significant": stat_significant,
                "regime_consistent": regime_consistent,
                "sanity_flags": self.metadata.sanity_flags,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            determination_file = self.validation_dir / "determination.json"
            with open(determination_file, 'w') as f:
                json.dump(determination_doc, f, indent=2)

            self._transition_state(
                ValidationState.DETERMINATION,
                passed=True,
                details=determination_doc
            )

            # Final transition to completed
            self._transition_state(
                ValidationState.COMPLETED,
                passed=True
            )

            logger.info(f"DETERMINATION: {status.value} - {'; '.join(reasons)}")
            return status

    def get_status(self) -> Dict[str, Any]:
        """Get current validation status."""
        return {
            "component_id": self.component_id,
            "state": self.metadata.current_state.value,
            "determination": self.metadata.determination,
            "determination_reason": self.metadata.determination_reason,
            "sanity_flags": len(self.metadata.sanity_flags),
            "history_length": len(self.metadata.state_history),
            "locked_parameters": bool(self.metadata.locked_parameters)
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validation orchestrator")
    parser.add_argument("component_id", help="Component ID (e.g., IND-002)")
    parser.add_argument("--status", action="store_true", help="Show current status")

    args = parser.parse_args()

    orchestrator = ValidationOrchestrator(args.component_id)

    if args.status:
        status = orchestrator.get_status()
        print(json.dumps(status, indent=2))
    else:
        print(f"Orchestrator for {args.component_id}")
        print(f"Current state: {orchestrator.current_state.value}")
        print(f"Validation dir: {orchestrator.validation_dir}")
