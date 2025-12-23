"""
Data availability checker for the Research Validation System.

Checks if required data is available before validation starts.
Enforces the data hierarchy: QC native -> Object Store -> Internal purchased -> curated -> experimental

Usage:
    from scripts.data.check_availability import check_data_requirements
    result = check_data_requirements(["spy_prices", "mcclellan_oscillator"])
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from scripts.utils.logging_config import get_logger

logger = get_logger("data-availability")

# Data registry location
REGISTRY_DIR = Path(__file__).parent.parent.parent / "data-registry"
REGISTRY_FILE = REGISTRY_DIR / "registry.json"


@dataclass
class DataCheck:
    """Result of checking a single data source."""
    data_id: str
    available: bool
    source: Optional[str] = None  # qc_native, qc_object_store, internal_purchased, etc.
    key_or_path: Optional[str] = None  # Object store key or local path
    error: Optional[str] = None
    usage_notes: Optional[str] = None
    column_indices: Optional[Dict[str, int]] = None


@dataclass
class DataCheckResult:
    """Result of checking all data requirements."""
    all_available: bool
    checks: List[DataCheck]
    recommended_sources: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "all_available": self.all_available,
            "checks": [
                {
                    "data_id": c.data_id,
                    "available": c.available,
                    "source": c.source,
                    "key_or_path": c.key_or_path,
                    "error": c.error,
                    "usage_notes": c.usage_notes,
                    "column_indices": c.column_indices
                }
                for c in self.checks
            ],
            "recommended_sources": self.recommended_sources,
            "timestamp": self.timestamp
        }


class DataRegistry:
    """Interface to the data registry."""

    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path or REGISTRY_FILE
        self._registry = None
        self._load_registry()

    def _load_registry(self):
        """Load the registry from disk."""
        if not self.registry_path.exists():
            raise FileNotFoundError(f"Registry not found: {self.registry_path}")

        with open(self.registry_path, 'r') as f:
            self._registry = json.load(f)

        # Index by ID for fast lookup
        self._sources_by_id = {
            source["id"]: source
            for source in self._registry.get("data_sources", [])
        }

        logger.debug(f"Loaded registry with {len(self._sources_by_id)} data sources")

    def get_source(self, data_id: str) -> Optional[Dict[str, Any]]:
        """Get a data source by ID."""
        return self._sources_by_id.get(data_id)

    def list_sources(self) -> List[str]:
        """List all data source IDs."""
        return list(self._sources_by_id.keys())

    def get_hierarchy(self) -> List[str]:
        """Get the data hierarchy order."""
        return self._registry.get("hierarchy_order", [
            "qc_native",
            "qc_object_store",
            "internal_purchased",
            "internal_curated",
            "internal_experimental"
        ])


def check_single_source(source: Dict[str, Any], registry: DataRegistry) -> DataCheck:
    """
    Check availability of a single data source following the hierarchy.

    Returns the first available source in hierarchy order.
    """
    data_id = source["id"]
    availability = source.get("availability", {})
    hierarchy = registry.get_hierarchy()

    for tier in hierarchy:
        tier_data = availability.get(tier)

        if tier_data is None:
            continue

        # Handle boolean (simple available flag)
        if isinstance(tier_data, bool):
            if tier_data:
                return DataCheck(
                    data_id=data_id,
                    available=True,
                    source=tier,
                    usage_notes=source.get("usage_notes"),
                    column_indices=source.get("column_indices")
                )
            continue

        # Handle dict with available flag
        if isinstance(tier_data, dict):
            if tier_data.get("available", False):
                key_or_path = tier_data.get("key") or tier_data.get("path") or tier_data.get("symbol")
                return DataCheck(
                    data_id=data_id,
                    available=True,
                    source=tier,
                    key_or_path=key_or_path,
                    usage_notes=source.get("usage_notes"),
                    column_indices=source.get("column_indices")
                )

    # Nothing available
    return DataCheck(
        data_id=data_id,
        available=False,
        error=f"No source available for {data_id} in any tier"
    )


def check_data_requirements(data_ids: List[str]) -> DataCheckResult:
    """
    Check if all required data is available.

    Args:
        data_ids: List of data source IDs from the registry

    Returns:
        DataCheckResult with availability status for each source
    """
    registry = DataRegistry()
    checks = []
    recommended_sources = {}

    for data_id in data_ids:
        source = registry.get_source(data_id)

        if source is None:
            checks.append(DataCheck(
                data_id=data_id,
                available=False,
                error=f"Data source '{data_id}' not found in registry. "
                      f"Available sources: {', '.join(registry.list_sources()[:10])}..."
            ))
            continue

        check = check_single_source(source, registry)
        checks.append(check)

        if check.available:
            recommended_sources[data_id] = check.source
            logger.info(f"Data '{data_id}' available via {check.source}")
        else:
            logger.warning(f"Data '{data_id}' NOT available: {check.error}")

    all_available = all(c.available for c in checks)

    return DataCheckResult(
        all_available=all_available,
        checks=checks,
        recommended_sources=recommended_sources
    )


def get_data_loading_code(data_id: str) -> Optional[str]:
    """
    Generate code snippet for loading a data source in QC algorithm.

    Args:
        data_id: Data source ID

    Returns:
        Python code snippet for loading the data, or None if not available
    """
    registry = DataRegistry()
    source = registry.get_source(data_id)

    if not source:
        return None

    check = check_single_source(source, registry)

    if not check.available:
        return None

    if check.source == "qc_native":
        symbol = check.key_or_path or data_id.upper()
        return f'''# QC Native: {data_id}
self.AddEquity("{symbol}", Resolution.Daily)'''

    elif check.source == "qc_object_store":
        key = check.key_or_path
        columns = source.get("columns", [])
        col_indices = source.get("column_indices", {})
        usage_notes = source.get("usage_notes", "")

        code = f'''# QC Object Store: {data_id}
# {usage_notes}
data = self.ObjectStore.Read("{key}")
lines = data.split("\\n")
# Columns: {columns}
# Column indices: {col_indices}
'''
        return code

    elif check.source.startswith("internal_"):
        path = check.key_or_path
        return f'''# Internal data: {data_id}
# Local path: {path}
# NOTE: Upload to QC Object Store for cloud backtesting'''

    return None


def validate_column_access(data_id: str, column_name: str) -> Optional[int]:
    """
    Get the correct column index for a data source.

    Use this to avoid the wrong-column bug that affected EXPLOIT-008.

    Args:
        data_id: Data source ID
        column_name: Name of column to access

    Returns:
        Column index, or None if not found
    """
    registry = DataRegistry()
    source = registry.get_source(data_id)

    if not source:
        logger.error(f"Data source not found: {data_id}")
        return None

    col_indices = source.get("column_indices", {})

    if column_name not in col_indices:
        logger.error(f"Column '{column_name}' not found in {data_id}. "
                    f"Available columns: {list(col_indices.keys())}")
        return None

    return col_indices[column_name]


if __name__ == "__main__":
    import sys

    print("Data Availability Checker")
    print("=" * 50)

    # Test with common data requirements
    test_ids = ["spy_prices", "mcclellan_oscillator", "tick_order_flow"]

    print(f"\nChecking availability for: {test_ids}")
    result = check_data_requirements(test_ids)

    print(f"\nAll available: {result.all_available}")
    print("\nDetails:")
    for check in result.checks:
        status = "✓" if check.available else "✗"
        source = check.source or "N/A"
        print(f"  {status} {check.data_id}: {source}")
        if check.error:
            print(f"      Error: {check.error}")
        if check.usage_notes:
            print(f"      Note: {check.usage_notes}")

    print("\nRecommended sources:", result.recommended_sources)

    # Test column validation
    print("\n" + "=" * 50)
    print("Column Index Validation")
    idx = validate_column_access("mcclellan_oscillator", "mcclellan_osc")
    print(f"McClellan oscillator column index: {idx}")

    # Test code generation
    print("\n" + "=" * 50)
    print("Sample Data Loading Code")
    code = get_data_loading_code("mcclellan_oscillator")
    if code:
        print(code)
