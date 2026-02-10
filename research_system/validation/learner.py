"""V4 Strategy Learner - Extract learnings from validation results.

This module extracts insights and learnings from validation results
to help inform future strategy development.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Learning:
    """A single learning extracted from validation."""
    category: str  # e.g., "verification", "validation", "performance"
    type: str  # e.g., "success", "warning", "failure"
    insight: str
    recommendation: str | None = None
    source: str | None = None  # Which test/gate produced this


@dataclass
class LearningsDocument:
    """Complete learnings document for a strategy."""
    strategy_id: str
    strategy_name: str
    timestamp: datetime
    learnings: list[Learning] = field(default_factory=list)
    summary: str = ""
    validation_passed: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "timestamp": self.timestamp.isoformat(),
            "validation_passed": self.validation_passed,
            "summary": self.summary,
            "learnings": [
                {
                    "category": l.category,
                    "type": l.type,
                    "insight": l.insight,
                    "recommendation": l.recommendation,
                    "source": l.source,
                }
                for l in self.learnings
            ],
        }


class Learner:
    """Learner for extracting insights from V4 validation results."""

    def __init__(self, workspace):
        """Initialize learner.

        Args:
            workspace: V4Workspace instance
        """
        self.workspace = workspace

    def extract_learnings(
        self,
        strategy: dict,
        verification_results: list[dict] | None = None,
        validation_results: list[dict] | None = None,
    ) -> LearningsDocument:
        """Extract learnings from validation results.

        Args:
            strategy: Strategy dictionary
            verification_results: List of verification result dicts
            validation_results: List of validation result dicts

        Returns:
            LearningsDocument with extracted insights
        """
        doc = LearningsDocument(
            strategy_id=strategy.get("id", "unknown"),
            strategy_name=strategy.get("name", "Unknown Strategy"),
            timestamp=datetime.now(),
        )

        # Extract from verification results
        if verification_results:
            for vr in verification_results:
                self._extract_from_verification(doc, vr)

        # Extract from validation results
        if validation_results:
            for val in validation_results:
                self._extract_from_validation(doc, val)
                if val.get("overall_passed") is not None:
                    doc.validation_passed = val["overall_passed"]

        # Extract from strategy definition itself
        self._extract_from_strategy(doc, strategy)

        # Generate summary
        doc.summary = self._generate_summary(doc)

        return doc

    def _extract_from_verification(
        self, doc: LearningsDocument, result: dict
    ) -> None:
        """Extract learnings from verification result."""
        tests = result.get("tests", [])

        for test in tests:
            name = test.get("name", "unknown")
            status = test.get("status", "unknown")
            message = test.get("message", "")
            details = test.get("details", {})

            if status == "fail":
                doc.learnings.append(Learning(
                    category="verification",
                    type="failure",
                    insight=f"Verification failed: {message}",
                    recommendation=self._get_recommendation_for_test(name, details),
                    source=f"verification:{name}",
                ))
            elif status == "warn":
                doc.learnings.append(Learning(
                    category="verification",
                    type="warning",
                    insight=f"Verification warning: {message}",
                    recommendation=self._get_recommendation_for_test(name, details),
                    source=f"verification:{name}",
                ))
            elif status == "pass":
                doc.learnings.append(Learning(
                    category="verification",
                    type="success",
                    insight=f"Passed {name}: {message}",
                    source=f"verification:{name}",
                ))

    def _extract_from_validation(
        self, doc: LearningsDocument, result: dict
    ) -> None:
        """Extract learnings from validation result."""
        gates = result.get("gates", [])
        metrics = result.get("backtest_metrics", {})

        for gate in gates:
            gate_name = gate.get("gate", "unknown")
            status = gate.get("status", "unknown")
            threshold = gate.get("threshold")
            actual = gate.get("actual")
            message = gate.get("message", "")

            if status == "fail":
                doc.learnings.append(Learning(
                    category="validation",
                    type="failure",
                    insight=f"Gate failed: {message}",
                    recommendation=self._get_gate_recommendation(gate_name, actual, threshold),
                    source=f"validation:{gate_name}",
                ))
            elif status == "pass":
                doc.learnings.append(Learning(
                    category="validation",
                    type="success",
                    insight=f"Gate passed: {message}",
                    source=f"validation:{gate_name}",
                ))

        # Check for zero-trade backtests
        total_trades = metrics.get("total_trades", None) if metrics else None
        if total_trades == 0:
            doc.learnings.append(Learning(
                category="performance",
                type="warning",
                insight="Backtest executed 0 trades. All-zero metrics indicate a data feed problem or overly restrictive entry conditions, not a genuinely unprofitable strategy.",
                recommendation="Check data subscriptions, verify entry conditions trigger on historical data, and review generated algorithm code.",
                source="backtest_results",
            ))

        # Add performance insights
        if metrics:
            doc.learnings.append(Learning(
                category="performance",
                type="info",
                insight=f"Backtest metrics: Sharpe={metrics.get('sharpe_ratio', 'N/A')}, "
                        f"MaxDD={metrics.get('max_drawdown', 'N/A')}, "
                        f"WinRate={metrics.get('win_rate', 'N/A')}",
                source="validation:metrics",
            ))

    def _extract_from_strategy(self, doc: LearningsDocument, strategy: dict) -> None:
        """Extract learnings from strategy definition."""
        # Check for missing components
        if not strategy.get("data_requirements"):
            doc.learnings.append(Learning(
                category="strategy",
                type="warning",
                insight="Strategy lacks explicit data requirements",
                recommendation="Document data needs to ensure reproducibility",
                source="strategy:data_requirements",
            ))

        # Check hypothesis quality
        hypothesis = strategy.get("hypothesis", {})
        if hypothesis:
            # Look for V4 format (summary) or simple format (thesis)
            thesis = hypothesis.get("summary") or hypothesis.get("thesis")
            if thesis and len(thesis) > 50:
                doc.learnings.append(Learning(
                    category="strategy",
                    type="success",
                    insight="Strategy has a clear hypothesis documented",
                    source="strategy:hypothesis",
                ))

        # Check edge definition
        edge = hypothesis.get("edge") or strategy.get("edge", {})
        if edge and edge.get("why_exists"):
            doc.learnings.append(Learning(
                category="strategy",
                type="success",
                insight="Strategy has economic rationale documented",
                source="strategy:edge",
            ))

    def _get_recommendation_for_test(
        self, test_name: str, details: dict
    ) -> str | None:
        """Get recommendation for a verification test."""
        recommendations = {
            "look_ahead_bias": "Review entry/exit conditions for any use of future data",
            "survivorship_bias": "Consider using point-in-time data or all-stocks universe",
            "position_sizing": "Add explicit position sizing rules (fixed fractional, volatility-scaled, etc.)",
            "data_requirements": "List all required data fields in data_requirements section",
            "entry_defined": "Specify complete entry conditions with signals or technical config",
            "exit_defined": "Define exit paths including stop loss",
            "universe_defined": "Specify the universe with symbols or filter criteria",
        }
        return recommendations.get(test_name)

    def _get_gate_recommendation(
        self, gate_name: str, actual: float | None, threshold: float | None
    ) -> str | None:
        """Get recommendation for a failed validation gate."""
        if gate_name == "sharpe_ratio" and actual is not None and threshold is not None:
            if actual < 0:
                return "Strategy has negative returns - review hypothesis and entry/exit logic"
            elif actual < threshold:
                return f"Consider parameter optimization or regime filtering to improve Sharpe from {actual:.2f} to ≥{threshold}"
        elif gate_name == "max_drawdown":
            return "Consider tighter stop losses or position sizing to reduce drawdown"
        elif gate_name == "win_rate":
            return "Review entry signals for better timing or add confirmation filters"
        return None

    def _generate_summary(self, doc: LearningsDocument) -> str:
        """Generate summary from learnings."""
        successes = sum(1 for l in doc.learnings if l.type == "success")
        warnings = sum(1 for l in doc.learnings if l.type == "warning")
        failures = sum(1 for l in doc.learnings if l.type == "failure")

        if doc.validation_passed is True:
            status = "VALIDATED"
        elif doc.validation_passed is False:
            status = "INVALIDATED"
        else:
            status = "PENDING VALIDATION"

        parts = [
            f"Strategy {doc.strategy_id} ({doc.strategy_name}): {status}",
            f"Analysis: {successes} successes, {warnings} warnings, {failures} failures",
        ]

        if failures > 0:
            failure_insights = [l.insight for l in doc.learnings if l.type == "failure"]
            parts.append(f"Key issues: {'; '.join(failure_insights[:3])}")

        return " | ".join(parts)

    def load_results(self, strategy_id: str) -> tuple[list[dict], list[dict]]:
        """Load verification and validation results for a strategy.

        Args:
            strategy_id: Strategy ID to load results for

        Returns:
            Tuple of (verification_results, validation_results)
        """
        validations_path = self.workspace.path / "validations"

        verification_results = []
        validation_results = []

        if validations_path.exists():
            # Search flat YAML files (from verify/validate commands)
            verify_files = []
            for filepath in validations_path.glob(f"{strategy_id}_*.yaml"):
                if "_verify_" in filepath.name:
                    verify_files.append(filepath)
                elif "_validate_" in filepath.name:
                    with open(filepath) as f:
                        data = yaml.safe_load(f)
                    validation_results.append(data)

            # Only process the most recent verification file to avoid duplicates
            if verify_files:
                most_recent = sorted(verify_files)[-1]
                with open(most_recent) as f:
                    data = yaml.safe_load(f)
                verification_results.append(data)

            # Search subdirectory for run results (from run command)
            run_result_path = validations_path / strategy_id / "run_result.json"
            if run_result_path.exists():
                with open(run_result_path) as f:
                    run_data = json.load(f)

                validation_results.append(
                    self._adapt_run_result(run_data)
                )

        return verification_results, validation_results

    def _adapt_run_result(self, run_data: dict) -> dict:
        """Adapt a run result JSON into the validation result format.

        The run command saves results with a different schema than the
        validate command. This converts run results into the format
        expected by _extract_from_validation.

        Args:
            run_data: Raw run result dict from run_result.json

        Returns:
            Dict matching the validation result schema (gates,
            backtest_metrics, overall_passed)
        """
        # Convert gate_results to the gate format expected by _extract_from_validation
        gates = []
        for g in run_data.get("gate_results", []):
            gates.append({
                "gate": g.get("gate", "unknown"),
                "status": "pass" if g.get("passed") else "fail",
                "threshold": g.get("threshold"),
                "actual": g.get("actual"),
                "message": (
                    f"{g.get('gate', 'unknown')}: "
                    f"actual={g.get('actual')}, threshold={g.get('threshold')}"
                ),
            })

        # Extract backtest metrics from the nested backtest data
        backtest_metrics = {}
        backtest = run_data.get("backtest") or {}
        if backtest.get("aggregate_sharpe") is not None:
            backtest_metrics["sharpe_ratio"] = backtest["aggregate_sharpe"]
        if backtest.get("max_drawdown") is not None:
            backtest_metrics["max_drawdown"] = backtest["max_drawdown"]
        if backtest.get("consistency") is not None:
            backtest_metrics["win_rate"] = backtest["consistency"]

        # Map determination to overall_passed
        determination = run_data.get("determination", "PENDING")
        if determination == "VALIDATED":
            overall_passed = True
        elif determination == "INVALIDATED":
            overall_passed = False
        else:
            overall_passed = None

        return {
            "gates": gates,
            "backtest_metrics": backtest_metrics,
            "overall_passed": overall_passed,
            "source": "run",
            "determination": determination,
            "timestamp": run_data.get("timestamp"),
        }

    def save_learnings(
        self, doc: LearningsDocument, dry_run: bool = False
    ) -> Path | None:
        """Save learnings document.

        Args:
            doc: LearningsDocument to save
            dry_run: If True, don't actually save

        Returns:
            Path to saved file, or None if dry_run
        """
        if dry_run:
            return None

        learnings_path = self.workspace.path / "learnings"
        learnings_path.mkdir(parents=True, exist_ok=True)

        filename = f"{doc.strategy_id}_learnings_{doc.timestamp.strftime('%Y%m%d_%H%M%S')}.yaml"
        filepath = learnings_path / filename

        # Atomic write: temp file + rename
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=filepath.parent,
            suffix=".yaml.tmp",
            prefix=f".{doc.strategy_id}_",
        )
        try:
            with os.fdopen(tmp_fd, "w") as f:
                yaml.dump(doc.to_dict(), f, default_flow_style=False, sort_keys=False)
            os.replace(tmp_path, filepath)  # Atomic on POSIX
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        return filepath


# Backward-compat alias
V4Learner = Learner
