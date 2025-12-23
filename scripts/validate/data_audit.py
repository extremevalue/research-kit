"""
Mandatory data audit before any validation testing.

This is Gate 1 in the validation pipeline - ALL checks must pass before
any backtesting can proceed. This prevents:
- Look-ahead bias (using same-day data for EOD signals)
- Wrong column reads (EXPLOIT-008 bug class)
- Insufficient history for statistical significance
- Data alignment issues across sources

Usage:
    from scripts.validate.data_audit import audit_data_requirements
    result = audit_data_requirements("IND-002", hypothesis)
    if not result.passed:
        raise ValidationGateError(result.blocking_issues)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum

from scripts.utils.logging_config import get_logger, LogContext
from scripts.data.check_availability import check_data_requirements, DataRegistry, validate_column_access

logger = get_logger("data-audit")

# Minimum requirements
MIN_IS_YEARS = 15  # Minimum in-sample period
MIN_OOS_YEARS = 4  # Minimum out-of-sample period
MIN_TOTAL_YEARS = 19  # Total history needed


class AuditSeverity(Enum):
    """Severity of audit findings."""
    BLOCKING = "blocking"  # Must fix before proceeding
    WARNING = "warning"    # Should review but can proceed
    INFO = "info"          # Informational only


@dataclass
class AuditCheck:
    """Result of a single audit check."""
    name: str
    passed: bool
    severity: AuditSeverity
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class DataAuditResult:
    """Complete data audit result."""
    component_id: str
    passed: bool
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    checks: List[AuditCheck] = field(default_factory=list)
    blocking_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "passed": self.passed,
            "timestamp": self.timestamp,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "severity": c.severity.value,
                    "message": c.message,
                    "details": c.details
                }
                for c in self.checks
            ],
            "blocking_issues": self.blocking_issues,
            "warnings": self.warnings
        }


def check_lookahead_bias(
    hypothesis: Dict[str, Any],
    data_sources: List[Dict[str, Any]]
) -> AuditCheck:
    """
    Check for potential look-ahead bias in data usage.

    Key checks:
    - EOD indicators must use T-1 data (previous day)
    - Intraday signals need proper timestamp handling
    - Economic data needs release date verification
    """
    issues = []

    # Check hypothesis for signal timing
    signal_timing = hypothesis.get("signal_timing", "eod")
    data_lag = hypothesis.get("data_lag_days", 0)

    for source in data_sources:
        source_id = source.get("id", "unknown")
        usage_notes = source.get("usage_notes", "")

        # EOD indicators should use T-1
        if signal_timing == "eod" and data_lag == 0:
            if "T-1" in usage_notes or "days_back" in usage_notes:
                issues.append(f"{source_id}: EOD signal but data requires T-1 lag")

        # Check for known problematic patterns
        if "same-day" in str(hypothesis).lower() and "breadth" in source_id.lower():
            issues.append(f"{source_id}: Same-day breadth data creates look-ahead bias")

    if issues:
        return AuditCheck(
            name="lookahead_bias",
            passed=False,
            severity=AuditSeverity.BLOCKING,
            message="Potential look-ahead bias detected",
            details={"issues": issues}
        )

    return AuditCheck(
        name="lookahead_bias",
        passed=True,
        severity=AuditSeverity.INFO,
        message="No look-ahead bias detected",
        details={"signal_timing": signal_timing, "data_lag": data_lag}
    )


def check_column_mapping(
    hypothesis: Dict[str, Any],
    data_sources: List[Dict[str, Any]]
) -> AuditCheck:
    """
    Verify column mappings are correct for all data sources.

    Prevents the EXPLOIT-008 bug where column 1 was read instead of column 4.
    """
    issues = []
    verified_columns = []

    # Extract column references from hypothesis
    column_refs = hypothesis.get("column_references", {})

    for source in data_sources:
        source_id = source.get("id", "unknown")
        expected_columns = source.get("column_indices", {})

        if not expected_columns:
            issues.append(f"{source_id}: No column indices defined in registry")
            continue

        # Check if hypothesis references match registry
        for col_name, col_ref in column_refs.items():
            if col_ref.get("source") == source_id:
                expected_idx = expected_columns.get(col_name)
                ref_idx = col_ref.get("index")

                if expected_idx is None:
                    issues.append(f"{source_id}: Column '{col_name}' not in registry")
                elif ref_idx is not None and ref_idx != expected_idx:
                    issues.append(
                        f"{source_id}: Column '{col_name}' index mismatch - "
                        f"hypothesis uses {ref_idx}, registry says {expected_idx}"
                    )
                else:
                    verified_columns.append(f"{source_id}.{col_name}={expected_idx}")

    if issues:
        return AuditCheck(
            name="column_mapping",
            passed=False,
            severity=AuditSeverity.BLOCKING,
            message="Column mapping errors detected",
            details={"issues": issues, "verified": verified_columns}
        )

    return AuditCheck(
        name="column_mapping",
        passed=True,
        severity=AuditSeverity.INFO,
        message=f"Column mappings verified: {len(verified_columns)} columns",
        details={"verified": verified_columns}
    )


def check_sufficient_history(
    hypothesis: Dict[str, Any],
    data_sources: List[Dict[str, Any]]
) -> AuditCheck:
    """
    Verify sufficient historical data exists for IS + OOS testing.

    Requirements:
    - Minimum 15 years for in-sample
    - Minimum 4 years for out-of-sample
    - Data must cover the required periods
    """
    issues = []

    is_start = hypothesis.get("is_period", {}).get("start", "2005-01-01")
    is_end = hypothesis.get("is_period", {}).get("end", "2019-12-31")
    oos_start = hypothesis.get("oos_period", {}).get("start", "2020-01-01")
    oos_end = hypothesis.get("oos_period", {}).get("end", "2024-12-31")

    # Calculate periods
    try:
        is_years = (datetime.fromisoformat(is_end) - datetime.fromisoformat(is_start)).days / 365.25
        oos_years = (datetime.fromisoformat(oos_end) - datetime.fromisoformat(oos_start)).days / 365.25
    except (ValueError, TypeError):
        return AuditCheck(
            name="sufficient_history",
            passed=False,
            severity=AuditSeverity.BLOCKING,
            message="Invalid date format in hypothesis periods",
            details={"is_start": is_start, "is_end": is_end, "oos_start": oos_start, "oos_end": oos_end}
        )

    if is_years < MIN_IS_YEARS:
        issues.append(f"In-sample period {is_years:.1f} years < minimum {MIN_IS_YEARS} years")

    if oos_years < MIN_OOS_YEARS:
        issues.append(f"Out-of-sample period {oos_years:.1f} years < minimum {MIN_OOS_YEARS} years")

    # Check each data source covers required period
    for source in data_sources:
        source_id = source.get("id", "unknown")
        coverage = source.get("coverage", {})

        source_start = coverage.get("start_date")
        source_end = coverage.get("end_date")

        if not source_start or not source_end:
            issues.append(f"{source_id}: Coverage dates not defined")
            continue

        if source_start > is_start:
            issues.append(f"{source_id}: Data starts {source_start}, need {is_start}")

        if source_end < oos_end:
            issues.append(f"{source_id}: Data ends {source_end}, need {oos_end}")

    if issues:
        return AuditCheck(
            name="sufficient_history",
            passed=False,
            severity=AuditSeverity.BLOCKING,
            message="Insufficient historical data",
            details={
                "issues": issues,
                "is_years": is_years,
                "oos_years": oos_years,
                "required_is_years": MIN_IS_YEARS,
                "required_oos_years": MIN_OOS_YEARS
            }
        )

    return AuditCheck(
        name="sufficient_history",
        passed=True,
        severity=AuditSeverity.INFO,
        message=f"Sufficient history: {is_years:.1f}y IS + {oos_years:.1f}y OOS",
        details={"is_years": is_years, "oos_years": oos_years}
    )


def check_data_alignment(
    data_sources: List[Dict[str, Any]]
) -> AuditCheck:
    """
    Verify data sources can be aligned properly.

    Checks:
    - Frequency compatibility (daily vs intraday)
    - Calendar alignment (trading days vs calendar days)
    - Timezone consistency
    """
    issues = []
    frequencies = set()

    for source in data_sources:
        source_id = source.get("id", "unknown")
        coverage = source.get("coverage", {})

        freq = coverage.get("frequency", "daily")
        frequencies.add(freq)

        # Check calendar type
        calendar = coverage.get("calendar", "trading_days")
        if calendar == "calendar_days" and len(data_sources) > 1:
            issues.append(f"{source_id}: Uses calendar days, may misalign with trading day data")

    # Check frequency compatibility
    if len(frequencies) > 1:
        if "minute" in frequencies and "daily" in frequencies:
            issues.append(f"Mixed frequencies detected: {frequencies}. Ensure proper aggregation.")

    if issues:
        return AuditCheck(
            name="data_alignment",
            passed=True,  # Warnings, not blocking
            severity=AuditSeverity.WARNING,
            message="Data alignment warnings",
            details={"issues": issues, "frequencies": list(frequencies)}
        )

    return AuditCheck(
        name="data_alignment",
        passed=True,
        severity=AuditSeverity.INFO,
        message=f"Data alignment OK: {frequencies}",
        details={"frequencies": list(frequencies)}
    )


def check_survivorship_bias(
    hypothesis: Dict[str, Any],
    data_sources: List[Dict[str, Any]]
) -> AuditCheck:
    """
    Check for potential survivorship bias.

    Key concerns:
    - Testing on current index constituents only
    - Ignoring delisted securities
    - Using point-in-time vs current classifications
    """
    issues = []
    warnings = []

    # Check if testing on indices
    test_universe = hypothesis.get("test_universe", "")

    if "spy" in test_universe.lower() or "sp500" in test_universe.lower():
        warnings.append("Testing on S&P 500 - ensure using point-in-time constituents")

    if "etf" in test_universe.lower():
        warnings.append("ETF testing may have survivorship bias from failed ETFs")

    # Check data sources for survivorship handling
    for source in data_sources:
        source_id = source.get("id", "unknown")

        if "constituents" in source_id.lower():
            if not source.get("point_in_time", False):
                issues.append(f"{source_id}: Not marked as point-in-time data")

    if issues:
        return AuditCheck(
            name="survivorship_bias",
            passed=False,
            severity=AuditSeverity.BLOCKING,
            message="Survivorship bias risk detected",
            details={"issues": issues, "warnings": warnings}
        )

    if warnings:
        return AuditCheck(
            name="survivorship_bias",
            passed=True,
            severity=AuditSeverity.WARNING,
            message="Survivorship bias warnings",
            details={"warnings": warnings}
        )

    return AuditCheck(
        name="survivorship_bias",
        passed=True,
        severity=AuditSeverity.INFO,
        message="No survivorship bias concerns detected"
    )


def check_data_availability(
    hypothesis: Dict[str, Any]
) -> AuditCheck:
    """
    Verify all required data is available in the registry.

    Uses the data hierarchy to find best available source.
    """
    data_requirements = hypothesis.get("data_requirements", [])

    if not data_requirements:
        return AuditCheck(
            name="data_availability",
            passed=False,
            severity=AuditSeverity.BLOCKING,
            message="No data requirements specified in hypothesis"
        )

    result = check_data_requirements(data_requirements)

    if not result.all_available:
        missing = [c.data_id for c in result.checks if not c.available]
        return AuditCheck(
            name="data_availability",
            passed=False,
            severity=AuditSeverity.BLOCKING,
            message=f"Missing data sources: {missing}",
            details=result.to_dict()
        )

    return AuditCheck(
        name="data_availability",
        passed=True,
        severity=AuditSeverity.INFO,
        message=f"All {len(data_requirements)} data sources available",
        details={
            "sources": result.recommended_sources,
            "checks": [
                {"id": c.data_id, "source": c.source, "key": c.key_or_path}
                for c in result.checks
            ]
        }
    )


def audit_data_requirements(
    component_id: str,
    hypothesis: Dict[str, Any]
) -> DataAuditResult:
    """
    Run complete data audit for a validation.

    ALL blocking checks must pass before testing can proceed.

    Args:
        component_id: Catalog entry ID (e.g., "IND-002")
        hypothesis: Hypothesis document with data requirements

    Returns:
        DataAuditResult with pass/fail status and details
    """
    with LogContext(logger, "Data Audit", component_id=component_id):
        logger.info(f"Starting data audit for {component_id}")

        result = DataAuditResult(component_id=component_id, passed=True)

        # Load data sources from registry
        try:
            registry = DataRegistry()
            data_ids = hypothesis.get("data_requirements", [])
            data_sources = [
                registry.get_source(did) for did in data_ids
                if registry.get_source(did) is not None
            ]
        except FileNotFoundError as e:
            result.passed = False
            result.blocking_issues.append(f"Data registry not found: {e}")
            return result

        # Run all checks
        checks = [
            check_data_availability(hypothesis),
            check_lookahead_bias(hypothesis, data_sources),
            check_column_mapping(hypothesis, data_sources),
            check_sufficient_history(hypothesis, data_sources),
            check_data_alignment(data_sources),
            check_survivorship_bias(hypothesis, data_sources),
        ]

        for check in checks:
            result.checks.append(check)

            if not check.passed:
                if check.severity == AuditSeverity.BLOCKING:
                    result.passed = False
                    result.blocking_issues.append(f"{check.name}: {check.message}")
                elif check.severity == AuditSeverity.WARNING:
                    result.warnings.append(f"{check.name}: {check.message}")

            # Log result
            status = "PASS" if check.passed else "FAIL"
            logger.info(f"  {check.name}: {status} - {check.message}")

        if result.passed:
            logger.info(f"Data audit PASSED for {component_id}")
        else:
            logger.error(f"Data audit FAILED for {component_id}: {result.blocking_issues}")

        return result


def save_audit_result(result: DataAuditResult, output_dir: Path) -> Path:
    """Save audit result to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "data_audit.json"

    with open(output_file, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)

    logger.info(f"Saved audit result to {output_file}")
    return output_file


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run data audit for a component")
    parser.add_argument("component_id", help="Component ID (e.g., IND-002)")
    parser.add_argument("--hypothesis", type=Path, help="Path to hypothesis.json")
    parser.add_argument("--output", type=Path, help="Output directory")

    args = parser.parse_args()

    # Load hypothesis
    if args.hypothesis and args.hypothesis.exists():
        with open(args.hypothesis) as f:
            hypothesis = json.load(f)
    else:
        # Example hypothesis for testing
        hypothesis = {
            "data_requirements": ["spy_prices", "mcclellan_oscillator"],
            "signal_timing": "eod",
            "data_lag_days": 1,
            "is_period": {"start": "2005-01-01", "end": "2019-12-31"},
            "oos_period": {"start": "2020-01-01", "end": "2024-12-31"},
            "test_universe": "SPY"
        }

    result = audit_data_requirements(args.component_id, hypothesis)

    print(f"\nData Audit Result: {'PASSED' if result.passed else 'FAILED'}")
    print(f"Timestamp: {result.timestamp}")

    print("\nChecks:")
    for check in result.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"  [{status}] {check.name}: {check.message}")

    if result.blocking_issues:
        print("\nBlocking Issues:")
        for issue in result.blocking_issues:
            print(f"  - {issue}")

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    if args.output:
        save_audit_result(result, args.output)
