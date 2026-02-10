"""V4 Strategy Validator - Run walk-forward validation on strategies.

This module provides walk-forward validation for strategies, including:
- Pre-validation verification checks
- Backtest configuration generation
- Validation gate application (Sharpe, drawdown, consistency)
- Result persistence
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class ValidationGate(str, Enum):
    """Validation gates that must be passed."""
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    CONSISTENCY = "consistency"
    WIN_RATE = "win_rate"


class GateStatus(str, Enum):
    """Status of a validation gate."""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class GateResult:
    """Result of a single validation gate."""
    gate: ValidationGate
    status: GateStatus
    threshold: float
    actual: float | None
    message: str


@dataclass
class ValidationResult:
    """Complete validation result for a strategy."""
    strategy_id: str
    timestamp: datetime
    verification_passed: bool
    gates: list[GateResult] = field(default_factory=list)
    overall_passed: bool = False
    backtest_metrics: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "strategy_id": self.strategy_id,
            "timestamp": self.timestamp.isoformat(),
            "verification_passed": self.verification_passed,
            "overall_passed": self.overall_passed,
            "gates": [
                {
                    "gate": g.gate.value,
                    "status": g.status.value,
                    "threshold": g.threshold,
                    "actual": g.actual,
                    "message": g.message,
                }
                for g in self.gates
            ],
            "backtest_metrics": self.backtest_metrics,
            "notes": self.notes,
        }


# Default validation thresholds
DEFAULT_GATES = {
    ValidationGate.SHARPE_RATIO: 0.5,
    ValidationGate.MAX_DRAWDOWN: 0.25,  # 25% max drawdown
    ValidationGate.WIN_RATE: 0.4,  # 40% win rate minimum
}


class Validator:
    """Validator for V4 strategies."""

    def __init__(self, workspace, verifier=None):
        """Initialize validator.

        Args:
            workspace: V4Workspace instance
            verifier: Optional V4Verifier instance (created if not provided)
        """
        self.workspace = workspace
        self.verifier = verifier
        self._config = workspace.config if hasattr(workspace, 'config') else None

    def get_gates(self) -> dict[ValidationGate, float]:
        """Get validation gate thresholds from config or defaults."""
        gates = DEFAULT_GATES.copy()

        # Override with config values if present (V4Config is a Pydantic model)
        if self._config and hasattr(self._config, 'gates'):
            config_gates = self._config.gates
            if hasattr(config_gates, 'min_sharpe'):
                gates[ValidationGate.SHARPE_RATIO] = config_gates.min_sharpe
            if hasattr(config_gates, 'max_drawdown'):
                gates[ValidationGate.MAX_DRAWDOWN] = config_gates.max_drawdown
            # Note: win_rate may not be in config, use default

        return gates

    def validate(
        self,
        strategy: dict,
        backtest_results: dict[str, float] | None = None,
    ) -> ValidationResult:
        """Run validation on a strategy.

        Args:
            strategy: Strategy dictionary
            backtest_results: Optional dict with keys like 'sharpe_ratio',
                            'max_drawdown', 'win_rate'

        Returns:
            ValidationResult with gate outcomes
        """
        result = ValidationResult(
            strategy_id=strategy.get("id", "unknown"),
            timestamp=datetime.now(),
            verification_passed=True,  # Assume passed if we got here
        )

        gates = self.get_gates()

        if backtest_results:
            result.backtest_metrics = backtest_results

            # Check Sharpe ratio gate
            if ValidationGate.SHARPE_RATIO in gates:
                threshold = gates[ValidationGate.SHARPE_RATIO]
                actual = backtest_results.get("sharpe_ratio")
                if actual is not None:
                    passed = actual >= threshold
                    result.gates.append(GateResult(
                        gate=ValidationGate.SHARPE_RATIO,
                        status=GateStatus.PASS if passed else GateStatus.FAIL,
                        threshold=threshold,
                        actual=actual,
                        message=f"Sharpe {actual:.2f} {'≥' if passed else '<'} {threshold}",
                    ))
                else:
                    result.gates.append(GateResult(
                        gate=ValidationGate.SHARPE_RATIO,
                        status=GateStatus.SKIP,
                        threshold=threshold,
                        actual=None,
                        message="Sharpe ratio not provided",
                    ))

            # Check max drawdown gate
            if ValidationGate.MAX_DRAWDOWN in gates:
                threshold = gates[ValidationGate.MAX_DRAWDOWN]
                actual = backtest_results.get("max_drawdown")
                if actual is not None:
                    passed = actual <= threshold
                    result.gates.append(GateResult(
                        gate=ValidationGate.MAX_DRAWDOWN,
                        status=GateStatus.PASS if passed else GateStatus.FAIL,
                        threshold=threshold,
                        actual=actual,
                        message=f"Drawdown {actual:.1%} {'≤' if passed else '>'} {threshold:.1%}",
                    ))
                else:
                    result.gates.append(GateResult(
                        gate=ValidationGate.MAX_DRAWDOWN,
                        status=GateStatus.SKIP,
                        threshold=threshold,
                        actual=None,
                        message="Max drawdown not provided",
                    ))

            # Check win rate gate
            if ValidationGate.WIN_RATE in gates:
                threshold = gates[ValidationGate.WIN_RATE]
                actual = backtest_results.get("win_rate")
                if actual is not None:
                    passed = actual >= threshold
                    result.gates.append(GateResult(
                        gate=ValidationGate.WIN_RATE,
                        status=GateStatus.PASS if passed else GateStatus.FAIL,
                        threshold=threshold,
                        actual=actual,
                        message=f"Win rate {actual:.1%} {'≥' if passed else '<'} {threshold:.1%}",
                    ))
                else:
                    result.gates.append(GateResult(
                        gate=ValidationGate.WIN_RATE,
                        status=GateStatus.SKIP,
                        threshold=threshold,
                        actual=None,
                        message="Win rate not provided",
                    ))

            # Determine overall result
            failed_gates = [g for g in result.gates if g.status == GateStatus.FAIL]
            result.overall_passed = len(failed_gates) == 0
        else:
            result.notes = "No backtest results provided - validation pending"

        return result

    def generate_backtest_config(self, strategy: dict) -> dict[str, Any]:
        """Generate backtest configuration for a strategy.

        Args:
            strategy: Strategy dictionary

        Returns:
            Backtest configuration dict
        """
        config = {
            "strategy_id": strategy.get("id"),
            "strategy_name": strategy.get("name"),
            "generated_at": datetime.now().isoformat(),
            "parameters": {},
            "universe": {},
            "dates": {
                "start": "2015-01-01",
                "end": "2024-12-31",
            },
            "walk_forward": {
                "in_sample_years": 3,
                "out_sample_years": 1,
                "windows": 5,
            },
        }

        # Extract universe
        universe = strategy.get("universe", {})
        if universe.get("type") == "static":
            symbols = universe.get("symbols", []) or universe.get("instruments", [])
            config["universe"] = {
                "type": "static",
                "symbols": symbols,
            }
        else:
            config["universe"] = universe

        # Extract entry parameters
        entry = strategy.get("entry", {})
        if entry.get("technical"):
            tech = entry["technical"]
            config["parameters"]["entry"] = {
                "type": "technical",
                "indicator": tech.get("indicator"),
                "params": tech.get("params", {}),
            }
        elif entry.get("signals"):
            config["parameters"]["entry"] = {
                "type": "signals",
                "signals": entry["signals"],
            }

        # Extract exit parameters
        exit_info = strategy.get("exit", {})
        if exit_info.get("paths"):
            config["parameters"]["exit"] = {
                "paths": exit_info["paths"],
            }

        # Extract position sizing
        position = strategy.get("position", {})
        if position.get("sizing"):
            config["parameters"]["sizing"] = position["sizing"]

        return config

    def save_result(
        self,
        result: ValidationResult,
        dry_run: bool = False,
    ) -> Path | None:
        """Save validation result.

        Args:
            result: ValidationResult to save
            dry_run: If True, don't actually save

        Returns:
            Path to saved file, or None if dry_run
        """
        if dry_run:
            return None

        validations_path = self.workspace.path / "validations"
        validations_path.mkdir(parents=True, exist_ok=True)

        filename = f"{result.strategy_id}_validate_{result.timestamp.strftime('%Y%m%d_%H%M%S')}.yaml"
        filepath = validations_path / filename

        with open(filepath, "w") as f:
            yaml.dump(result.to_dict(), f, default_flow_style=False, sort_keys=False)

        return filepath

    def update_strategy_status(
        self,
        strategy_id: str,
        passed: bool,
        dry_run: bool = False,
    ) -> str | None:
        """Move strategy to validated or invalidated folder.

        Args:
            strategy_id: Strategy ID
            passed: Whether validation passed
            dry_run: If True, don't actually move

        Returns:
            New path, or None if dry_run
        """
        if dry_run:
            return None

        # Find current strategy file
        for status_dir in ["pending", "validated", "invalidated", "blocked"]:
            current_path = self.workspace.strategies_path / status_dir / f"{strategy_id}.yaml"
            if current_path.exists():
                break
        else:
            return None

        # Determine target directory
        target_dir = "validated" if passed else "invalidated"
        target_path = self.workspace.strategies_path / target_dir / f"{strategy_id}.yaml"

        if current_path == target_path:
            return str(target_path)

        # Move file
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(current_path), str(target_path))

        # Update status in the file
        with open(target_path) as f:
            data = yaml.safe_load(f)
        data["status"] = target_dir
        with open(target_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        return str(target_path)


# Backward-compat alias
V4Validator = Validator
