"""
Catalog Management

Manages research catalog entries (indicators, strategies, ideas, etc.).
All entries are immutable after creation and validated against schema.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CatalogStats:
    """Statistics about the catalog."""
    total_entries: int
    by_type: Dict[str, int]
    by_status: Dict[str, int]
    generated_at: str


class CatalogEntry:
    """Represents a catalog entry."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    @property
    def id(self) -> str:
        return self._data["id"]

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def type(self) -> str:
        return self._data["type"]

    @property
    def status(self) -> str:
        return self._data["status"]

    @property
    def created_at(self) -> str:
        return self._data.get("created_at", "")

    @property
    def summary(self) -> Optional[str]:
        return self._data.get("summary")

    @property
    def hypothesis(self) -> Optional[str]:
        return self._data.get("hypothesis")

    @property
    def tags(self) -> List[str]:
        return self._data.get("tags", [])

    @property
    def validation_ref(self) -> Optional[str]:
        return self._data.get("validation_ref")

    def to_dict(self) -> Dict[str, Any]:
        return self._data.copy()


class CatalogQuery:
    """Fluent interface for querying the catalog."""

    def __init__(self, entries_path: Path):
        self._entries_path = entries_path
        self._filters: Dict[str, Any] = {}
        self._entries: Optional[List[Dict[str, Any]]] = None

    def _load_entries(self) -> List[Dict[str, Any]]:
        """Load all entry files."""
        if self._entries is not None:
            return self._entries

        entries = []
        if self._entries_path.exists():
            for file in self._entries_path.glob("*.json"):
                try:
                    with open(file, 'r') as f:
                        entries.append(json.load(f))
                except json.JSONDecodeError:
                    pass  # Skip invalid files

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
        if "type" in self._filters:
            if entry.get("type") != self._filters["type"]:
                return False

        if "status" in self._filters:
            if entry.get("status") != self._filters["status"]:
                return False

        if "id" in self._filters:
            if entry.get("id") != self._filters["id"]:
                return False

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

        if self._filters.get("has_validation"):
            if "validation_ref" not in entry:
                return False

        return True

    def count(self) -> int:
        """Count matching entries."""
        return len(self.execute())

    def first(self) -> Optional[Dict[str, Any]]:
        """Get first matching entry."""
        results = self.execute()
        return results[0] if results else None

    def ids(self) -> List[str]:
        """Get just the IDs of matching entries."""
        return [e["id"] for e in self.execute()]


class Catalog:
    """
    Manages the research catalog.

    The catalog contains all research entries (indicators, strategies, ideas, etc.)
    stored as individual JSON files in the entries/ directory.
    """

    # Valid entry types and their ID prefixes
    TYPE_PREFIXES = {
        "indicator": "IND",
        "strategy": "STRAT",
        "idea": "IDEA",
        "task": "TASK",      # Methodology/research tasks (not tradeable)
        "action": "ACTION",  # Administrative actions (reject, archive, etc.)
        "learning": "LEARN",
        "tool": "TOOL",
        "data": "DATA"
    }

    # Valid statuses
    VALID_STATUSES = [
        "UNTESTED",
        "IN_PROGRESS",
        "VALIDATED",
        "CONDITIONAL",
        "INVALIDATED",
        "BLOCKED"
    ]

    def __init__(self, catalog_path: Path):
        """
        Initialize catalog manager.

        Args:
            catalog_path: Path to catalog directory (contains entries/ and index.json)
        """
        self.catalog_path = catalog_path
        self.entries_path = catalog_path / "entries"
        self.index_path = catalog_path / "index.json"

    def ensure_structure(self):
        """Ensure catalog directories exist."""
        self.catalog_path.mkdir(parents=True, exist_ok=True)
        self.entries_path.mkdir(parents=True, exist_ok=True)

    def query(self) -> CatalogQuery:
        """Start a query builder."""
        return CatalogQuery(self.entries_path)

    def get(self, entry_id: str) -> Optional[CatalogEntry]:
        """Get a single entry by ID."""
        entry_file = self.entries_path / f"{entry_id}.json"
        if not entry_file.exists():
            return None

        with open(entry_file, 'r') as f:
            data = json.load(f)
        return CatalogEntry(data)

    def get_raw(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get raw entry data by ID."""
        entry_file = self.entries_path / f"{entry_id}.json"
        if not entry_file.exists():
            return None

        with open(entry_file, 'r') as f:
            return json.load(f)

    def exists(self, entry_id: str) -> bool:
        """Check if an entry exists."""
        return (self.entries_path / f"{entry_id}.json").exists()

    def list_ids(self) -> List[str]:
        """List all entry IDs."""
        ids = []
        if self.entries_path.exists():
            for file in self.entries_path.glob("*.json"):
                ids.append(file.stem)
        return sorted(ids)

    def get_next_id(self, entry_type: str) -> str:
        """Get the next available ID for an entry type."""
        prefix = self.TYPE_PREFIXES.get(entry_type)
        if not prefix:
            raise ValueError(f"Unknown entry type: {entry_type}. "
                           f"Valid types: {list(self.TYPE_PREFIXES.keys())}")

        pattern = re.compile(rf"^{prefix}-(\d{{3}})\.json$")
        max_num = 0

        if self.entries_path.exists():
            for file in self.entries_path.iterdir():
                match = pattern.match(file.name)
                if match:
                    num = int(match.group(1))
                    max_num = max(max_num, num)

        next_num = max_num + 1
        return f"{prefix}-{next_num:03d}"

    def add(
        self,
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
    ) -> CatalogEntry:
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
            The created CatalogEntry

        Raises:
            ValueError: If validation fails or entry exists
        """
        self.ensure_structure()

        # Validate entry type
        if entry_type not in self.TYPE_PREFIXES:
            raise ValueError(f"Invalid type: {entry_type}. Valid: {list(self.TYPE_PREFIXES.keys())}")

        # Generate or validate ID
        if entry_id:
            if not re.match(r"^[A-Z]+-\d{3}$", entry_id):
                raise ValueError(f"Invalid ID format: {entry_id}. Expected: TYPE-NNN")
            if self.exists(entry_id):
                raise ValueError(f"Entry {entry_id} already exists")
        else:
            entry_id = self.get_next_id(entry_type)
            # Safety check: verify generated ID doesn't already exist
            # This handles edge cases like manual entries or race conditions
            prefix = self.TYPE_PREFIXES[entry_type]
            while self.exists(entry_id):
                num = int(entry_id.split("-")[1]) + 1
                entry_id = f"{prefix}-{num:03d}"

        now = datetime.utcnow().isoformat() + "Z"

        # Build entry
        entry_data = {
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
            entry_data["summary"] = summary
        if hypothesis:
            entry_data["hypothesis"] = hypothesis
        if tags:
            entry_data["tags"] = tags
        if data_requirements:
            entry_data["data_requirements"] = data_requirements
        if related_entries:
            entry_data["related_entries"] = related_entries
        if source_origin:
            entry_data["source"]["origin"] = source_origin

        # Write entry file
        entry_file = self.entries_path / f"{entry_id}.json"
        with open(entry_file, 'w') as f:
            json.dump(entry_data, f, indent=2)

        # Update index
        self._update_index(entry_data)

        return CatalogEntry(entry_data)

    def update_status(
        self,
        entry_id: str,
        new_status: str,
        validation_ref: Optional[str] = None,
        blocked_reason: Optional[str] = None
    ) -> CatalogEntry:
        """
        Update the status of an entry.

        This is one of the few allowed modifications to an entry.
        """
        if new_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {new_status}. Valid: {self.VALID_STATUSES}")

        entry_data = self.get_raw(entry_id)
        if not entry_data:
            raise ValueError(f"Entry not found: {entry_id}")

        entry_data["status"] = new_status
        entry_data["updated_at"] = datetime.utcnow().isoformat() + "Z"

        if validation_ref:
            entry_data["validation_ref"] = validation_ref

        if blocked_reason:
            entry_data["blocked_reason"] = blocked_reason

        # Write
        entry_file = self.entries_path / f"{entry_id}.json"
        with open(entry_file, 'w') as f:
            json.dump(entry_data, f, indent=2)

        # Update index
        self._update_index(entry_data)

        return CatalogEntry(entry_data)

    def set_maturity(
        self,
        entry_id: str,
        maturity_level: str,
        maturity_score: float,
        missing_elements: List[str],
        steps_needed: List[str]
    ) -> CatalogEntry:
        """
        Set maturity classification for an entry (R2).

        Args:
            entry_id: The entry to update
            maturity_level: raw, partial, or full
            maturity_score: 0.0 to 1.0
            missing_elements: List of what's missing
            steps_needed: Development steps needed
        """
        entry_data = self.get_raw(entry_id)
        if not entry_data:
            raise ValueError(f"Entry not found: {entry_id}")

        entry_data["maturity"] = {
            "level": maturity_level,
            "score": maturity_score,
            "missing": missing_elements,
            "steps_needed": steps_needed,
            "classified_at": datetime.utcnow().isoformat() + "Z"
        }
        entry_data["updated_at"] = datetime.utcnow().isoformat() + "Z"

        # Write
        entry_file = self.entries_path / f"{entry_id}.json"
        with open(entry_file, 'w') as f:
            json.dump(entry_data, f, indent=2)

        return CatalogEntry(entry_data)

    def add_derived(
        self,
        parent_id: str,
        name: str,
        hypothesis: str,
        entry_type: str = "idea",
        tags: Optional[List[str]] = None
    ) -> CatalogEntry:
        """
        Add a derived idea from an expert review.

        Creates a new catalog entry linked to a parent entry,
        typically capturing improvement suggestions from expert personas.

        Args:
            parent_id: ID of the parent entry this idea derives from
            name: Name for the new idea
            hypothesis: The improvement hypothesis/suggestion
            entry_type: Type of entry (default: idea)
            tags: Optional tags (defaults to ["derived", "expert-suggestion"])

        Returns:
            The created CatalogEntry
        """
        # Verify parent exists
        if not self.exists(parent_id):
            raise ValueError(f"Parent entry not found: {parent_id}")

        # Default tags
        if tags is None:
            tags = ["derived", "expert-suggestion"]

        # Create the derived entry using existing add method
        return self.add(
            entry_type=entry_type,
            name=name,
            source_files=[],  # Derived ideas have no source files
            summary=f"Derived from {parent_id} expert review",
            hypothesis=hypothesis,
            tags=tags,
            related_entries=[parent_id]
        )

    def _update_index(self, entry: Dict[str, Any]):
        """Update the catalog index with a new or modified entry."""
        if self.index_path.exists():
            with open(self.index_path, 'r') as f:
                index = json.load(f)
        else:
            index = {
                "generated_at": None,
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
        index["generated_at"] = datetime.utcnow().isoformat() + "Z"

        # Recalculate by_type and by_status
        index["by_type"] = {}
        index["by_status"] = {}
        for e in index["entries"]:
            t = e["type"]
            s = e["status"]
            index["by_type"][t] = index["by_type"].get(t, 0) + 1
            index["by_status"][s] = index["by_status"].get(s, 0) + 1

        # Write index
        with open(self.index_path, 'w') as f:
            json.dump(index, f, indent=2)

    def rebuild_index(self):
        """Rebuild the index from all entry files."""
        entries_summary = []

        if self.entries_path.exists():
            for file in sorted(self.entries_path.glob("*.json")):
                try:
                    with open(file, 'r') as f:
                        entry = json.load(f)
                    entries_summary.append({
                        "id": entry["id"],
                        "name": entry["name"],
                        "type": entry["type"],
                        "status": entry["status"]
                    })
                except (json.JSONDecodeError, KeyError):
                    pass  # Skip invalid files

        # Calculate stats
        by_type: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        for e in entries_summary:
            t = e["type"]
            s = e["status"]
            by_type[t] = by_type.get(t, 0) + 1
            by_status[s] = by_status.get(s, 0) + 1

        index = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_entries": len(entries_summary),
            "by_type": by_type,
            "by_status": by_status,
            "entries": entries_summary
        }

        with open(self.index_path, 'w') as f:
            json.dump(index, f, indent=2)

        return index

    def stats(self) -> CatalogStats:
        """Get catalog statistics."""
        if self.index_path.exists():
            with open(self.index_path, 'r') as f:
                index = json.load(f)
            return CatalogStats(
                total_entries=index.get("total_entries", 0),
                by_type=index.get("by_type", {}),
                by_status=index.get("by_status", {}),
                generated_at=index.get("generated_at", "unknown")
            )

        # Fallback: calculate from entries
        query = self.query()
        entries = query._load_entries()

        by_type: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        for e in entries:
            t = e.get("type", "unknown")
            s = e.get("status", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
            by_status[s] = by_status.get(s, 0) + 1

        return CatalogStats(
            total_entries=len(entries),
            by_type=by_type,
            by_status=by_status,
            generated_at="calculated"
        )

    def search(self, text: str, fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
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
        entries = self.query()._load_entries()
        results = []

        for entry in entries:
            for field in fields:
                value = entry.get(field, "")
                if value and text_lower in value.lower():
                    results.append(entry)
                    break

        return results
