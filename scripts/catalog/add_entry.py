"""
Add entries to the catalog with schema validation.

All catalog entries are immutable after creation.
Each entry is stored as a separate JSON file in catalog/entries/.

Usage:
    python scripts/catalog/add_entry.py --type indicator --name "My Indicator" --source archive/my_file.py

    or programmatically:
    from scripts.catalog.add_entry import add_catalog_entry
    entry = add_catalog_entry(type="indicator", name="My Indicator", source_files=["archive/my_file.py"])
"""

import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import re

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.schema_validator import require_valid_catalog_entry, validate_catalog_entry
from utils.logging_config import get_logger, LogContext

logger = get_logger("catalog-add")

# Catalog location
CATALOG_DIR = Path(__file__).parent.parent.parent / "catalog"
ENTRIES_DIR = CATALOG_DIR / "entries"
INDEX_FILE = CATALOG_DIR / "index.json"


def ensure_catalog_structure():
    """Ensure catalog directories exist."""
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    ENTRIES_DIR.mkdir(parents=True, exist_ok=True)


def get_next_id(entry_type: str) -> str:
    """
    Get the next available ID for an entry type.

    IDs follow the format: TYPE-NNN (e.g., IND-001, STRAT-042)
    """
    type_prefixes = {
        "indicator": "IND",
        "strategy": "STRAT",
        "idea": "IDEA",
        "learning": "LEARN",
        "tool": "TOOL",
        "data": "DATA"
    }

    prefix = type_prefixes.get(entry_type)
    if not prefix:
        raise ValueError(f"Unknown entry type: {entry_type}. "
                        f"Valid types: {list(type_prefixes.keys())}")

    # Find highest existing ID
    pattern = re.compile(rf"^{prefix}-(\d{{3}})\.json$")
    max_num = 0

    if ENTRIES_DIR.exists():
        for file in ENTRIES_DIR.iterdir():
            match = pattern.match(file.name)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)

    next_num = max_num + 1
    return f"{prefix}-{next_num:03d}"


def add_catalog_entry(
    entry_type: str,
    name: str,
    source_files: List[str],
    summary: Optional[str] = None,
    hypothesis: Optional[str] = None,
    tags: Optional[List[str]] = None,
    data_requirements: Optional[List[str]] = None,
    related_entries: Optional[List[str]] = None,
    source_origin: Optional[str] = None,
    entry_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a new entry to the catalog.

    Args:
        entry_type: One of: indicator, strategy, idea, learning, tool, data
        name: Human-readable name
        source_files: List of archive paths to source files
        summary: One-line description
        hypothesis: Testable hypothesis (if applicable)
        tags: Categorization tags
        data_requirements: IDs from data registry needed for validation
        related_entries: IDs of related catalog entries
        source_origin: Original source (e.g., paper, blog, code)
        entry_id: Optional specific ID (for migration)

    Returns:
        The created entry dict

    Raises:
        ValueError: If validation fails
    """
    ensure_catalog_structure()

    # Generate or validate ID
    if entry_id:
        # Validate format
        if not re.match(r"^[A-Z]+-\d{3}$", entry_id):
            raise ValueError(f"Invalid ID format: {entry_id}. Expected: TYPE-NNN")
        # Check for collision
        entry_file = ENTRIES_DIR / f"{entry_id}.json"
        if entry_file.exists():
            raise ValueError(f"Entry {entry_id} already exists")
    else:
        entry_id = get_next_id(entry_type)

    now = datetime.utcnow().isoformat() + "Z"

    # Build entry
    entry = {
        "id": entry_id,
        "name": name,
        "type": entry_type,
        "status": "UNTESTED",
        "created_at": now,
        "updated_at": now,
        "source": {
            "files": source_files,
            "ingested_at": now
        }
    }

    # Add optional fields
    if summary:
        entry["summary"] = summary
    if hypothesis:
        entry["hypothesis"] = hypothesis
    if tags:
        entry["tags"] = tags
    if data_requirements:
        entry["data_requirements"] = data_requirements
    if related_entries:
        entry["related_entries"] = related_entries
    if source_origin:
        entry["source"]["origin"] = source_origin

    # Validate against schema
    with LogContext(logger, "Schema validation", entry_id=entry_id):
        try:
            require_valid_catalog_entry(entry)
        except ValueError as e:
            logger.error(f"Schema validation failed: {e}")
            raise

    # Write entry file
    entry_file = ENTRIES_DIR / f"{entry_id}.json"
    with open(entry_file, 'w') as f:
        json.dump(entry, f, indent=2)

    logger.info(f"Created catalog entry: {entry_id} ({name})")

    # Update index
    update_index(entry)

    return entry


def update_index(entry: Dict[str, Any]):
    """Update the catalog index with a new or modified entry."""
    if INDEX_FILE.exists():
        with open(INDEX_FILE, 'r') as f:
            index = json.load(f)
    else:
        index = {
            "last_updated": None,
            "total_entries": 0,
            "by_type": {},
            "by_status": {},
            "entries": []
        }

    # Update entry in index
    entry_summary = {
        "id": entry["id"],
        "name": entry["name"],
        "type": entry["type"],
        "status": entry["status"]
    }

    # Remove existing entry if present
    index["entries"] = [e for e in index["entries"] if e["id"] != entry["id"]]
    index["entries"].append(entry_summary)

    # Update counts
    index["total_entries"] = len(index["entries"])
    index["last_updated"] = datetime.utcnow().isoformat() + "Z"

    # Recalculate by_type and by_status
    index["by_type"] = {}
    index["by_status"] = {}
    for e in index["entries"]:
        t = e["type"]
        s = e["status"]
        index["by_type"][t] = index["by_type"].get(t, 0) + 1
        index["by_status"][s] = index["by_status"].get(s, 0) + 1

    # Write index
    with open(INDEX_FILE, 'w') as f:
        json.dump(index, f, indent=2)


def entry_exists(entry_id: str) -> bool:
    """Check if an entry exists."""
    entry_file = ENTRIES_DIR / f"{entry_id}.json"
    return entry_file.exists()


def get_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    """Load an entry by ID."""
    entry_file = ENTRIES_DIR / f"{entry_id}.json"
    if not entry_file.exists():
        return None

    with open(entry_file, 'r') as f:
        return json.load(f)


def update_entry_status(entry_id: str, new_status: str, validation_ref: Optional[str] = None) -> Dict[str, Any]:
    """
    Update the status of an entry.

    This is one of the few allowed modifications to an entry.
    """
    valid_statuses = ["UNTESTED", "IN_PROGRESS", "VALIDATED", "CONDITIONAL", "INVALIDATED", "BLOCKED"]
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status: {new_status}. Valid: {valid_statuses}")

    entry = get_entry(entry_id)
    if not entry:
        raise ValueError(f"Entry not found: {entry_id}")

    old_status = entry["status"]
    entry["status"] = new_status
    entry["updated_at"] = datetime.utcnow().isoformat() + "Z"

    if validation_ref:
        entry["validation_ref"] = validation_ref

    # Validate
    require_valid_catalog_entry(entry)

    # Write
    entry_file = ENTRIES_DIR / f"{entry_id}.json"
    with open(entry_file, 'w') as f:
        json.dump(entry, f, indent=2)

    # Update index
    update_index(entry)

    logger.info(f"Updated {entry_id} status: {old_status} -> {new_status}")

    return entry


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a catalog entry")
    parser.add_argument("--type", required=True,
                       choices=["indicator", "strategy", "idea", "learning", "tool", "data"],
                       help="Entry type")
    parser.add_argument("--name", required=True, help="Entry name")
    parser.add_argument("--source", required=True, nargs="+", help="Source file paths")
    parser.add_argument("--summary", help="One-line summary")
    parser.add_argument("--hypothesis", help="Testable hypothesis")
    parser.add_argument("--tags", nargs="+", help="Tags")
    parser.add_argument("--data-requirements", nargs="+", help="Data source IDs")
    parser.add_argument("--origin", help="Source origin (paper, blog, etc.)")

    args = parser.parse_args()

    entry = add_catalog_entry(
        entry_type=args.type,
        name=args.name,
        source_files=args.source,
        summary=args.summary,
        hypothesis=args.hypothesis,
        tags=args.tags,
        data_requirements=args.data_requirements,
        source_origin=args.origin
    )

    print(f"Created entry: {entry['id']}")
    print(json.dumps(entry, indent=2))
