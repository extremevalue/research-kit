"""
Query the catalog.

Usage:
    python scripts/catalog/query.py --type indicator --status VALIDATED
    python scripts/catalog/query.py --id IND-002
    python scripts/catalog/query.py --tags breadth momentum
    python scripts/catalog/query.py --stats

    or programmatically:
    from scripts.catalog.query import CatalogQuery
    query = CatalogQuery()
    results = query.by_type("indicator").by_status("VALIDATED").execute()
"""

import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging_config import get_logger

logger = get_logger("catalog-query")

# Catalog location
CATALOG_DIR = Path(__file__).parent.parent.parent / "catalog"
ENTRIES_DIR = CATALOG_DIR / "entries"
INDEX_FILE = CATALOG_DIR / "index.json"


@dataclass
class CatalogStats:
    """Statistics about the catalog."""
    total_entries: int
    by_type: Dict[str, int]
    by_status: Dict[str, int]
    last_updated: str


class CatalogQuery:
    """Fluent interface for querying the catalog."""

    def __init__(self):
        self._filters = {}
        self._entries = None

    def _load_entries(self) -> List[Dict[str, Any]]:
        """Load all entry files."""
        if self._entries is not None:
            return self._entries

        entries = []
        if ENTRIES_DIR.exists():
            for file in ENTRIES_DIR.glob("*.json"):
                try:
                    with open(file, 'r') as f:
                        entries.append(json.load(f))
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse: {file}")

        self._entries = entries
        return entries

    def by_type(self, entry_type: str) -> 'CatalogQuery':
        """Filter by entry type."""
        self._filters["type"] = entry_type
        return self

    def by_status(self, status: str) -> 'CatalogQuery':
        """Filter by validation status."""
        self._filters["status"] = status
        return self

    def by_id(self, entry_id: str) -> 'CatalogQuery':
        """Filter by specific ID."""
        self._filters["id"] = entry_id
        return self

    def by_tags(self, tags: List[str], match_all: bool = False) -> 'CatalogQuery':
        """Filter by tags. If match_all=True, entry must have all tags."""
        self._filters["tags"] = {"values": tags, "match_all": match_all}
        return self

    def by_data_requirement(self, data_id: str) -> 'CatalogQuery':
        """Filter by data requirement."""
        self._filters["data_requirement"] = data_id
        return self

    def with_validation(self) -> 'CatalogQuery':
        """Only entries with validation_ref."""
        self._filters["has_validation"] = True
        return self

    def execute(self) -> List[Dict[str, Any]]:
        """Execute the query and return matching entries."""
        entries = self._load_entries()
        results = []

        for entry in entries:
            if self._matches(entry):
                results.append(entry)

        return results

    def _matches(self, entry: Dict[str, Any]) -> bool:
        """Check if entry matches all filters."""
        # Type filter
        if "type" in self._filters:
            if entry.get("type") != self._filters["type"]:
                return False

        # Status filter
        if "status" in self._filters:
            if entry.get("status") != self._filters["status"]:
                return False

        # ID filter
        if "id" in self._filters:
            if entry.get("id") != self._filters["id"]:
                return False

        # Tags filter
        if "tags" in self._filters:
            tag_filter = self._filters["tags"]
            entry_tags = set(entry.get("tags", []))
            filter_tags = set(tag_filter["values"])

            if tag_filter["match_all"]:
                if not filter_tags.issubset(entry_tags):
                    return False
            else:
                if not filter_tags.intersection(entry_tags):
                    return False

        # Data requirement filter
        if "data_requirement" in self._filters:
            data_reqs = entry.get("data_requirements", [])
            if self._filters["data_requirement"] not in data_reqs:
                return False

        # Has validation filter
        if self._filters.get("has_validation"):
            if "validation_ref" not in entry:
                return False

        return True

    def count(self) -> int:
        """Count matching entries without loading full data."""
        return len(self.execute())

    def first(self) -> Optional[Dict[str, Any]]:
        """Get first matching entry."""
        results = self.execute()
        return results[0] if results else None

    def ids(self) -> List[str]:
        """Get just the IDs of matching entries."""
        return [e["id"] for e in self.execute()]


def get_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    """Get a single entry by ID."""
    entry_file = ENTRIES_DIR / f"{entry_id}.json"
    if not entry_file.exists():
        return None

    with open(entry_file, 'r') as f:
        return json.load(f)


def get_stats() -> CatalogStats:
    """Get catalog statistics."""
    if INDEX_FILE.exists():
        with open(INDEX_FILE, 'r') as f:
            index = json.load(f)
        return CatalogStats(
            total_entries=index.get("total_entries", 0),
            by_type=index.get("by_type", {}),
            by_status=index.get("by_status", {}),
            last_updated=index.get("last_updated", "unknown")
        )

    # Fallback: calculate from entries
    query = CatalogQuery()
    entries = query._load_entries()

    by_type = {}
    by_status = {}
    for e in entries:
        t = e.get("type", "unknown")
        s = e.get("status", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        by_status[s] = by_status.get(s, 0) + 1

    return CatalogStats(
        total_entries=len(entries),
        by_type=by_type,
        by_status=by_status,
        last_updated="calculated"
    )


def list_all_ids() -> List[str]:
    """List all entry IDs."""
    ids = []
    if ENTRIES_DIR.exists():
        for file in ENTRIES_DIR.glob("*.json"):
            ids.append(file.stem)
    return sorted(ids)


def search(text: str, fields: List[str] = None) -> List[Dict[str, Any]]:
    """
    Search entries by text in specified fields.

    Args:
        text: Text to search for (case-insensitive)
        fields: Fields to search in (default: name, summary, hypothesis)

    Returns:
        Matching entries
    """
    if fields is None:
        fields = ["name", "summary", "hypothesis"]

    text_lower = text.lower()
    query = CatalogQuery()
    entries = query._load_entries()
    results = []

    for entry in entries:
        for field in fields:
            value = entry.get(field, "")
            if value and text_lower in value.lower():
                results.append(entry)
                break

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the catalog")
    parser.add_argument("--type", help="Filter by type")
    parser.add_argument("--status", help="Filter by status")
    parser.add_argument("--id", help="Get specific entry by ID")
    parser.add_argument("--tags", nargs="+", help="Filter by tags")
    parser.add_argument("--search", help="Search text in name/summary/hypothesis")
    parser.add_argument("--stats", action="store_true", help="Show catalog statistics")
    parser.add_argument("--ids-only", action="store_true", help="Only show IDs")
    parser.add_argument("--count", action="store_true", help="Only show count")

    args = parser.parse_args()

    if args.stats:
        stats = get_stats()
        print(f"Total entries: {stats.total_entries}")
        print(f"Last updated: {stats.last_updated}")
        print("\nBy type:")
        for t, count in sorted(stats.by_type.items()):
            print(f"  {t}: {count}")
        print("\nBy status:")
        for s, count in sorted(stats.by_status.items()):
            print(f"  {s}: {count}")
        exit(0)

    if args.id:
        entry = get_entry(args.id)
        if entry:
            print(json.dumps(entry, indent=2))
        else:
            print(f"Entry not found: {args.id}")
        exit(0)

    if args.search:
        results = search(args.search)
        if args.count:
            print(len(results))
        elif args.ids_only:
            for e in results:
                print(e["id"])
        else:
            for e in results:
                print(f"{e['id']}: {e['name']}")
        exit(0)

    # Build query
    query = CatalogQuery()
    if args.type:
        query = query.by_type(args.type)
    if args.status:
        query = query.by_status(args.status)
    if args.tags:
        query = query.by_tags(args.tags)

    results = query.execute()

    if args.count:
        print(len(results))
    elif args.ids_only:
        for e in results:
            print(e["id"])
    else:
        for e in results:
            status = e.get("status", "?")
            print(f"{e['id']} [{status}]: {e['name']}")

        print(f"\nTotal: {len(results)} entries")
