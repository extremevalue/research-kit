"""
Regenerate the catalog index from entry files.

The index is a lightweight summary for fast queries.
It should never be edited manually - always regenerate from entries.

Usage:
    python scripts/catalog/generate_index.py
    python scripts/catalog/generate_index.py --verify  # Verify without overwriting
"""

import json
import argparse
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging_config import get_logger
from utils.schema_validator import validate_catalog_entry

logger = get_logger("catalog-index")

# Catalog location
CATALOG_DIR = Path(__file__).parent.parent.parent / "catalog"
ENTRIES_DIR = CATALOG_DIR / "entries"
INDEX_FILE = CATALOG_DIR / "index.json"


def load_all_entries() -> List[Dict[str, Any]]:
    """Load all entry files and return them."""
    entries = []
    errors = []

    if not ENTRIES_DIR.exists():
        logger.warning(f"Entries directory does not exist: {ENTRIES_DIR}")
        return entries

    for file in sorted(ENTRIES_DIR.glob("*.json")):
        try:
            with open(file, 'r') as f:
                entry = json.load(f)

            # Validate schema
            result = validate_catalog_entry(entry)
            if not result.valid:
                errors.append(f"{file.name}: Schema validation failed - {result.errors[:2]}")
                continue

            entries.append(entry)

        except json.JSONDecodeError as e:
            errors.append(f"{file.name}: JSON parse error - {e}")
        except Exception as e:
            errors.append(f"{file.name}: Error - {e}")

    if errors:
        logger.warning(f"Found {len(errors)} errors while loading entries:")
        for err in errors[:10]:  # Show first 10
            logger.warning(f"  {err}")
        if len(errors) > 10:
            logger.warning(f"  ... and {len(errors) - 10} more")

    return entries


def generate_index(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate index from entries."""
    by_type = {}
    by_status = {}
    entry_summaries = []

    for entry in entries:
        t = entry.get("type", "unknown")
        s = entry.get("status", "unknown")

        by_type[t] = by_type.get(t, 0) + 1
        by_status[s] = by_status.get(s, 0) + 1

        entry_summaries.append({
            "id": entry["id"],
            "name": entry["name"],
            "type": entry["type"],
            "status": entry["status"]
        })

    # Sort entries by ID
    entry_summaries.sort(key=lambda x: x["id"])

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_entries": len(entries),
        "by_type": dict(sorted(by_type.items())),
        "by_status": dict(sorted(by_status.items())),
        "entries": entry_summaries
    }


def write_index(index: Dict[str, Any]):
    """Write index to file."""
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    with open(INDEX_FILE, 'w') as f:
        json.dump(index, f, indent=2)

    logger.info(f"Wrote index with {index['total_entries']} entries to {INDEX_FILE}")


def verify_index() -> bool:
    """Verify current index matches entries."""
    if not INDEX_FILE.exists():
        logger.error("Index file does not exist")
        return False

    with open(INDEX_FILE, 'r') as f:
        current_index = json.load(f)

    entries = load_all_entries()
    expected_index = generate_index(entries)

    # Compare key fields
    issues = []

    if current_index.get("total_entries") != expected_index["total_entries"]:
        issues.append(f"Total entries mismatch: {current_index.get('total_entries')} vs {expected_index['total_entries']}")

    if current_index.get("by_type") != expected_index["by_type"]:
        issues.append("Type counts mismatch")

    if current_index.get("by_status") != expected_index["by_status"]:
        issues.append("Status counts mismatch")

    current_ids = {e["id"] for e in current_index.get("entries", [])}
    expected_ids = {e["id"] for e in expected_index["entries"]}

    missing = expected_ids - current_ids
    extra = current_ids - expected_ids

    if missing:
        issues.append(f"Missing from index: {missing}")
    if extra:
        issues.append(f"Extra in index: {extra}")

    if issues:
        logger.error("Index verification failed:")
        for issue in issues:
            logger.error(f"  {issue}")
        return False

    logger.info("Index verification passed")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate catalog index")
    parser.add_argument("--verify", action="store_true",
                       help="Verify index without overwriting")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be generated without writing")

    args = parser.parse_args()

    if args.verify:
        success = verify_index()
        exit(0 if success else 1)

    entries = load_all_entries()
    index = generate_index(entries)

    if args.dry_run:
        print("Would generate index:")
        print(json.dumps(index, indent=2))
        print(f"\nTotal: {index['total_entries']} entries")
        print(f"By type: {index['by_type']}")
        print(f"By status: {index['by_status']}")
    else:
        write_index(index)
        print(f"Generated index with {index['total_entries']} entries")
        print(f"By type: {index['by_type']}")
        print(f"By status: {index['by_status']}")
