"""V4 Strategy Verifier - Run verification tests on strategies.

This module provides verification tests to check strategies for common issues
before running backtests, including:
- Look-ahead bias detection
- Survivorship bias checks
- Position sizing validation
- Data availability verification
- Parameter sanity checks
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class VerificationStatus(str, Enum):
    """Status of a verification test."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class VerificationTest:
    """Result of a single verification test."""
    name: str
    status: VerificationStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Complete verification result for a strategy."""
    strategy_id: str
    timestamp: datetime
    tests: list[VerificationTest] = field(default_factory=list)
    overall_status: VerificationStatus = VerificationStatus.PASS

    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.status == VerificationStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for t in self.tests if t.status == VerificationStatus.FAIL)

    @property
    def warnings(self) -> int:
        return sum(1 for t in self.tests if t.status == VerificationStatus.WARN)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "strategy_id": self.strategy_id,
            "timestamp": self.timestamp.isoformat(),
            "overall_status": self.overall_status.value,
            "summary": {
                "passed": self.passed,
                "failed": self.failed,
                "warnings": self.warnings,
                "total": len(self.tests),
            },
            "tests": [
                {
                    "name": t.name,
                    "status": t.status.value,
                    "message": t.message,
                    "details": t.details,
                }
                for t in self.tests
            ],
        }


class Verifier:
    """Verifier for V4 strategies."""

    # Keywords that suggest look-ahead bias
    LOOK_AHEAD_KEYWORDS = [
        "tomorrow", "next_day", "future", "will_be", "forward",
        "t+1", "t+2", "next_bar", "next_close", "tomorrow_open",
    ]

    # Keywords that suggest survivorship bias concerns
    SURVIVORSHIP_KEYWORDS = [
        "sp500", "s&p500", "index_constituents", "current_members",
        "top_", "largest_", "market_cap_rank",
    ]

    def __init__(self, workspace):
        """Initialize verifier with workspace.

        Args:
            workspace: V4Workspace instance
        """
        self.workspace = workspace

    def verify(self, strategy: dict) -> VerificationResult:
        """Run all verification tests on a strategy.

        Args:
            strategy: Strategy dictionary loaded from YAML

        Returns:
            VerificationResult with all test outcomes
        """
        result = VerificationResult(
            strategy_id=strategy.get("id", "unknown"),
            timestamp=datetime.now(),
        )

        # Run all verification tests
        result.tests.append(self._check_look_ahead_bias(strategy))
        result.tests.append(self._check_survivorship_bias(strategy))
        result.tests.append(self._check_position_sizing(strategy))
        result.tests.append(self._check_data_requirements(strategy))
        result.tests.append(self._check_entry_defined(strategy))
        result.tests.append(self._check_exit_defined(strategy))
        result.tests.append(self._check_universe_defined(strategy))

        # Determine overall status
        if any(t.status == VerificationStatus.FAIL for t in result.tests):
            result.overall_status = VerificationStatus.FAIL
        elif any(t.status == VerificationStatus.WARN for t in result.tests):
            result.overall_status = VerificationStatus.WARN
        else:
            result.overall_status = VerificationStatus.PASS

        return result

    def _check_look_ahead_bias(self, strategy: dict) -> VerificationTest:
        """Check for potential look-ahead bias in strategy definition."""
        issues = []

        # Check entry conditions
        entry = strategy.get("entry", {})
        entry_str = str(entry).lower()
        for keyword in self.LOOK_AHEAD_KEYWORDS:
            if keyword in entry_str:
                issues.append(f"Entry contains '{keyword}' - possible look-ahead bias")

        # Check exit conditions
        exit_info = strategy.get("exit", {})
        exit_str = str(exit_info).lower()
        for keyword in self.LOOK_AHEAD_KEYWORDS:
            if keyword in exit_str:
                issues.append(f"Exit contains '{keyword}' - possible look-ahead bias")

        # Check technical config
        tech = entry.get("technical", {})
        if tech:
            condition = str(tech.get("condition", "")).lower()
            for keyword in self.LOOK_AHEAD_KEYWORDS:
                if keyword in condition:
                    issues.append(f"Technical condition contains '{keyword}'")

        if issues:
            return VerificationTest(
                name="look_ahead_bias",
                status=VerificationStatus.WARN,
                message=f"Found {len(issues)} potential look-ahead bias issue(s)",
                details={"issues": issues},
            )

        return VerificationTest(
            name="look_ahead_bias",
            status=VerificationStatus.PASS,
            message="No obvious look-ahead bias detected",
        )

    def _check_survivorship_bias(self, strategy: dict) -> VerificationTest:
        """Check for potential survivorship bias in universe definition."""
        issues = []

        universe = strategy.get("universe", {})
        universe_str = str(universe).lower()

        for keyword in self.SURVIVORSHIP_KEYWORDS:
            if keyword in universe_str:
                issues.append(f"Universe contains '{keyword}' - may have survivorship bias")

        # Check if using dynamic universe without point-in-time data
        if universe.get("type") == "dynamic":
            filters = universe.get("filters", [])
            has_pit = any("point_in_time" in str(f).lower() for f in filters)
            if not has_pit:
                issues.append("Dynamic universe without point-in-time flag")

        if issues:
            return VerificationTest(
                name="survivorship_bias",
                status=VerificationStatus.WARN,
                message=f"Found {len(issues)} potential survivorship bias issue(s)",
                details={"issues": issues},
            )

        return VerificationTest(
            name="survivorship_bias",
            status=VerificationStatus.PASS,
            message="No obvious survivorship bias detected",
        )

    def _check_position_sizing(self, strategy: dict) -> VerificationTest:
        """Check if position sizing is properly defined."""
        position = strategy.get("position", {})

        if not position:
            return VerificationTest(
                name="position_sizing",
                status=VerificationStatus.WARN,
                message="No position sizing defined",
                details={"recommendation": "Add position sizing rules"},
            )

        sizing = position.get("sizing", {})
        if not sizing:
            # Check if there's a simple size field
            if position.get("size") or position.get("allocation"):
                return VerificationTest(
                    name="position_sizing",
                    status=VerificationStatus.PASS,
                    message="Position sizing defined",
                )
            return VerificationTest(
                name="position_sizing",
                status=VerificationStatus.WARN,
                message="Position sizing method not specified",
                details={"recommendation": "Add sizing.method to position"},
            )

        method = sizing.get("method")
        if not method:
            return VerificationTest(
                name="position_sizing",
                status=VerificationStatus.WARN,
                message="Position sizing method not specified",
            )

        return VerificationTest(
            name="position_sizing",
            status=VerificationStatus.PASS,
            message=f"Position sizing defined: {method}",
        )

    def _check_data_requirements(self, strategy: dict) -> VerificationTest:
        """Check if data requirements are specified."""
        data_reqs = strategy.get("data_requirements", {})

        if not data_reqs:
            return VerificationTest(
                name="data_requirements",
                status=VerificationStatus.WARN,
                message="No data requirements specified",
                details={"recommendation": "List required data in data_requirements"},
            )

        primary = data_reqs.get("primary", [])
        if not primary:
            return VerificationTest(
                name="data_requirements",
                status=VerificationStatus.WARN,
                message="No primary data requirements listed",
            )

        return VerificationTest(
            name="data_requirements",
            status=VerificationStatus.PASS,
            message=f"{len(primary)} primary data requirement(s) specified",
        )

    def _check_entry_defined(self, strategy: dict) -> VerificationTest:
        """Check if entry conditions are properly defined."""
        entry = strategy.get("entry", {})

        if not entry:
            return VerificationTest(
                name="entry_defined",
                status=VerificationStatus.FAIL,
                message="No entry conditions defined",
            )

        # Check for entry type
        entry_type = entry.get("type")
        if not entry_type:
            return VerificationTest(
                name="entry_defined",
                status=VerificationStatus.WARN,
                message="Entry type not specified",
            )

        # Check for signals or technical config
        has_signals = bool(entry.get("signals"))
        has_technical = bool(entry.get("technical"))
        has_fundamental = bool(entry.get("fundamental"))

        if not (has_signals or has_technical or has_fundamental):
            return VerificationTest(
                name="entry_defined",
                status=VerificationStatus.WARN,
                message="Entry has type but no signal/technical/fundamental config",
            )

        return VerificationTest(
            name="entry_defined",
            status=VerificationStatus.PASS,
            message=f"Entry defined with type: {entry_type}",
        )

    def _check_exit_defined(self, strategy: dict) -> VerificationTest:
        """Check if exit conditions are properly defined."""
        exit_info = strategy.get("exit", {})

        if not exit_info:
            return VerificationTest(
                name="exit_defined",
                status=VerificationStatus.FAIL,
                message="No exit conditions defined",
            )

        paths = exit_info.get("paths", [])
        if not paths:
            return VerificationTest(
                name="exit_defined",
                status=VerificationStatus.WARN,
                message="No exit paths defined",
            )

        # Check for stop loss
        has_stop = any("stop" in str(p).lower() for p in paths)
        if not has_stop:
            return VerificationTest(
                name="exit_defined",
                status=VerificationStatus.WARN,
                message=f"{len(paths)} exit path(s) defined but no stop loss",
                details={"recommendation": "Consider adding a stop loss exit path"},
            )

        return VerificationTest(
            name="exit_defined",
            status=VerificationStatus.PASS,
            message=f"{len(paths)} exit path(s) defined including stop loss",
        )

    def _check_universe_defined(self, strategy: dict) -> VerificationTest:
        """Check if universe is properly defined."""
        universe = strategy.get("universe", {})

        if not universe:
            return VerificationTest(
                name="universe_defined",
                status=VerificationStatus.FAIL,
                message="No universe defined",
            )

        universe_type = universe.get("type")
        if not universe_type:
            return VerificationTest(
                name="universe_defined",
                status=VerificationStatus.WARN,
                message="Universe type not specified",
            )

        # Check for symbols in static universe
        if universe_type == "static":
            symbols = universe.get("symbols", []) or universe.get("instruments", [])
            if not symbols:
                return VerificationTest(
                    name="universe_defined",
                    status=VerificationStatus.WARN,
                    message="Static universe with no symbols defined",
                )
            return VerificationTest(
                name="universe_defined",
                status=VerificationStatus.PASS,
                message=f"Static universe with {len(symbols)} symbol(s)",
            )

        return VerificationTest(
            name="universe_defined",
            status=VerificationStatus.PASS,
            message=f"Universe type: {universe_type}",
        )

    def save_result(self, result: VerificationResult, dry_run: bool = False) -> Path | None:
        """Save verification result to validations directory.

        Args:
            result: VerificationResult to save
            dry_run: If True, don't actually save

        Returns:
            Path to saved file, or None if dry_run
        """
        if dry_run:
            return None

        # Create validations directory if needed
        validations_path = self.workspace.path / "validations"
        validations_path.mkdir(parents=True, exist_ok=True)

        # Save result
        filename = f"{result.strategy_id}_verify_{result.timestamp.strftime('%Y%m%d_%H%M%S')}.yaml"
        filepath = validations_path / filename

        with open(filepath, "w") as f:
            yaml.dump(result.to_dict(), f, default_flow_style=False, sort_keys=False)

        return filepath


# Backward-compat alias
V4Verifier = Verifier
