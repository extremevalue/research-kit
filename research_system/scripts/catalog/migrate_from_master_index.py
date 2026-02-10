"""
Migrate entries from the old MASTER_INDEX.json to the new catalog structure.

This script:
1. Reads the existing MASTER_INDEX.json
2. Transforms entries to match the new schema
3. Validates each entry
4. Writes individual entry files
5. Generates the new index

Usage:
    python scripts/catalog/migrate_from_master_index.py /path/to/MASTER_INDEX.json
    python scripts/catalog/migrate_from_master_index.py /path/to/MASTER_INDEX.json --dry-run
    python scripts/catalog/migrate_from_master_index.py /path/to/MASTER_INDEX.json --validate-only
"""

import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import re

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging_config import get_logger
from utils.schema_validator import validate_catalog_entry

logger = get_logger("catalog-migrate")

# Catalog location
CATALOG_DIR = Path(__file__).parent.parent.parent / "catalog"
ENTRIES_DIR = CATALOG_DIR / "entries"


# Type mapping from old to new
TYPE_MAP = {
    "strategy": "strategy",
    "indicator": "indicator",
    "idea": "idea",
    "ideas": "idea",
    "learning": "learning",
    "tool": "tool",
    "data": "data",
    "DATA": "data",
    "LEARN": "learning",
    "STRAT": "strategy",
    "IND": "indicator",
    "IDEA": "idea",
    "TOOL": "tool"
}

# Status mapping from old to new
STATUS_MAP = {
    "UNTESTED": "UNTESTED",
    "IN_PROGRESS": "IN_PROGRESS",
    "VALIDATED": "VALIDATED",
    "CONDITIONAL": "CONDITIONAL",
    "INVALIDATED": "INVALIDATED",
    "FALSIFIED": "INVALIDATED",  # Map FALSIFIED to INVALIDATED
    "BLOCKED": "BLOCKED",
    "BACKLOGGED": "BLOCKED",
    "NOT_TESTABLE": "BLOCKED",
    "EXTERNALLY_VALIDATED": "VALIDATED",  # Map external to VALIDATED
    "INVALIDATED_BY_ANALOGY": "INVALIDATED",
    "VALIDATED_BY_ANALOGY": "VALIDATED",
    "LIVE_3M": "VALIDATED"
}


def transform_entry(old_entry: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Transform an old format entry to the new schema.

    Returns:
        Tuple of (transformed_entry, list_of_warnings)
        transformed_entry is None if entry cannot be migrated
    """
    warnings = []

    # Get ID
    entry_id = old_entry.get("id")
    if not entry_id:
        return None, ["Missing ID"]

    # Validate ID format
    if not re.match(r"^[A-Z]+-\d{3}$", entry_id):
        warnings.append(f"Non-standard ID format: {entry_id}")
        # Try to fix common issues
        if "-" not in entry_id:
            return None, [f"Cannot parse ID: {entry_id}"]

    # Get and map type
    old_type = old_entry.get("type", "").lower()
    new_type = TYPE_MAP.get(old_type)
    if not new_type:
        # Try to infer from ID prefix
        prefix = entry_id.split("-")[0]
        new_type = TYPE_MAP.get(prefix)
        if not new_type:
            warnings.append(f"Unknown type '{old_type}', defaulting to 'idea'")
            new_type = "idea"

    # Get and map status
    old_status = old_entry.get("status", "UNTESTED")
    new_status = STATUS_MAP.get(old_status, "UNTESTED")
    if old_status not in STATUS_MAP:
        warnings.append(f"Unknown status '{old_status}', defaulting to UNTESTED")

    # Get name
    name = old_entry.get("name", entry_id)
    if not name or len(name) < 1:
        name = entry_id

    # Get source files
    source_files = old_entry.get("source_files", [])
    if isinstance(source_files, str):
        source_files = [source_files]
    if not source_files:
        # Try alternate field names
        source_files = old_entry.get("files", [])
        if isinstance(source_files, str):
            source_files = [source_files]
    if not source_files:
        source_files = [f"archive/legacy/{entry_id}.json"]
        warnings.append("No source files found, using placeholder")

    # Build new entry
    now = datetime.utcnow().isoformat() + "Z"
    created_at = old_entry.get("created_at") or old_entry.get("date_added") or now

    new_entry = {
        "id": entry_id,
        "name": name,
        "type": new_type,
        "status": new_status,
        "created_at": created_at,
        "updated_at": now,
        "source": {
            "files": source_files,
            "ingested_at": created_at
        }
    }

    # Optional fields
    if old_entry.get("summary"):
        new_entry["summary"] = old_entry["summary"][:500]  # Limit length

    if old_entry.get("hypothesis"):
        new_entry["hypothesis"] = old_entry["hypothesis"]

    if old_entry.get("tags"):
        tags = old_entry["tags"]
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        new_entry["tags"] = tags

    # Map data requirements if present
    data_reqs = old_entry.get("data_requirements") or old_entry.get("requires_data")
    if data_reqs:
        if isinstance(data_reqs, str):
            data_reqs = [data_reqs]
        new_entry["data_requirements"] = data_reqs

    # Preserve validation reference if exists
    if old_entry.get("qc_validation") or old_entry.get("validation_path"):
        val_path = old_entry.get("validation_path") or f"validations/{entry_id}/"
        new_entry["validation_ref"] = val_path

    return new_entry, warnings


def migrate_entries(
    master_index_path: Path,
    dry_run: bool = False,
    validate_only: bool = False
) -> Dict[str, Any]:
    """
    Migrate entries from MASTER_INDEX.json.

    Returns:
        Summary of migration results
    """
    # Load old index
    with open(master_index_path, 'r') as f:
        old_data = json.load(f)

    old_entries = old_data.get("entries", [])
    logger.info(f"Found {len(old_entries)} entries to migrate")

    # Process entries
    results = {
        "total": len(old_entries),
        "successful": 0,
        "failed": 0,
        "warnings": 0,
        "failures": [],
        "entry_warnings": []
    }

    new_entries = []

    for old_entry in old_entries:
        entry_id = old_entry.get("id", "unknown")

        new_entry, warnings = transform_entry(old_entry)

        if new_entry is None:
            results["failed"] += 1
            results["failures"].append({
                "id": entry_id,
                "reason": warnings[0] if warnings else "Unknown error"
            })
            continue

        if warnings:
            results["warnings"] += len(warnings)
            results["entry_warnings"].append({
                "id": entry_id,
                "warnings": warnings
            })

        # Validate new entry
        validation = validate_catalog_entry(new_entry)
        if not validation.valid:
            results["failed"] += 1
            results["failures"].append({
                "id": entry_id,
                "reason": f"Schema validation failed: {validation.errors[:2]}"
            })
            continue

        new_entries.append(new_entry)
        results["successful"] += 1

    if validate_only:
        logger.info(f"Validation complete: {results['successful']} valid, {results['failed']} invalid")
        return results

    if dry_run:
        logger.info(f"Dry run complete: would migrate {results['successful']} entries")
        return results

    # Write entries
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    ENTRIES_DIR.mkdir(parents=True, exist_ok=True)

    for entry in new_entries:
        entry_file = ENTRIES_DIR / f"{entry['id']}.json"
        with open(entry_file, 'w') as f:
            json.dump(entry, f, indent=2)

    logger.info(f"Wrote {len(new_entries)} entry files to {ENTRIES_DIR}")

    # Generate index
    from generate_index import generate_index, write_index
    index = generate_index(new_entries)
    write_index(index)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate from MASTER_INDEX.json")
    parser.add_argument("master_index", type=Path, help="Path to MASTER_INDEX.json")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be migrated without writing")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate entries, don't write anything")
    parser.add_argument("--show-warnings", action="store_true",
                       help="Show all warnings")

    args = parser.parse_args()

    if not args.master_index.exists():
        print(f"Error: File not found: {args.master_index}")
        exit(1)

    results = migrate_entries(
        args.master_index,
        dry_run=args.dry_run,
        validate_only=args.validate_only
    )

    print("\nMigration Results:")
    print(f"  Total entries: {results['total']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Warnings: {results['warnings']}")

    if results["failures"]:
        print("\nFailures:")
        for f in results["failures"][:10]:
            print(f"  {f['id']}: {f['reason']}")
        if len(results["failures"]) > 10:
            print(f"  ... and {len(results['failures']) - 10} more")

    if args.show_warnings and results["entry_warnings"]:
        print("\nWarnings:")
        for w in results["entry_warnings"][:20]:
            print(f"  {w['id']}: {', '.join(w['warnings'])}")
        if len(results["entry_warnings"]) > 20:
            print(f"  ... and {len(results['entry_warnings']) - 20} more")
