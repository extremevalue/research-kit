"""Tests for catalog management."""

import pytest
from pathlib import Path

from research_system.core.catalog import Catalog, CatalogEntry


class TestCatalog:
    """Tests for Catalog class."""

    def test_add_entry(self, temp_workspace):
        """Test adding a new entry."""
        catalog = Catalog(temp_workspace.catalog_path)

        entry = catalog.add(
            entry_type="indicator",
            name="Test Indicator",
            source_files=["test.py"]
        )

        assert entry.id.startswith("IND-")
        assert entry.status == "UNTESTED"
        assert entry.type == "indicator"
        assert entry.name == "Test Indicator"

    def test_add_strategy(self, temp_workspace):
        """Test adding a strategy entry."""
        catalog = Catalog(temp_workspace.catalog_path)

        entry = catalog.add(
            entry_type="strategy",
            name="Test Strategy",
            source_files=["strategy.py"]
        )

        assert entry.id.startswith("STRAT-")
        assert entry.type == "strategy"

    def test_get_entry(self, temp_workspace):
        """Test retrieving an entry."""
        catalog = Catalog(temp_workspace.catalog_path)

        added = catalog.add(
            entry_type="indicator",
            name="Test Indicator",
            source_files=["test.py"]
        )

        retrieved = catalog.get(added.id)

        assert retrieved is not None
        assert retrieved.id == added.id
        assert retrieved.name == "Test Indicator"

    def test_get_nonexistent(self, temp_workspace):
        """Test getting a nonexistent entry returns None."""
        catalog = Catalog(temp_workspace.catalog_path)

        result = catalog.get("NONEXISTENT-999")

        assert result is None

    def test_update_status(self, temp_workspace):
        """Test status updates."""
        catalog = Catalog(temp_workspace.catalog_path)

        entry = catalog.add(
            entry_type="indicator",
            name="Test",
            source_files=["test.py"]
        )

        updated = catalog.update_status(entry.id, "IN_PROGRESS")

        assert updated.status == "IN_PROGRESS"

        # Verify persisted
        retrieved = catalog.get(entry.id)
        assert retrieved.status == "IN_PROGRESS"

    def test_query_by_type(self, temp_workspace):
        """Test querying by type."""
        catalog = Catalog(temp_workspace.catalog_path)

        # Add entries of different types
        catalog.add(entry_type="indicator", name="Ind1", source_files=["a.py"])
        catalog.add(entry_type="strategy", name="Strat1", source_files=["b.py"])
        catalog.add(entry_type="indicator", name="Ind2", source_files=["c.py"])

        indicators = catalog.query().by_type("indicator").execute()

        assert len(indicators) == 2
        assert all(e["type"] == "indicator" for e in indicators)

    def test_query_by_status(self, temp_workspace):
        """Test querying by status."""
        catalog = Catalog(temp_workspace.catalog_path)

        e1 = catalog.add(entry_type="indicator", name="Ind1", source_files=["a.py"])
        catalog.add(entry_type="indicator", name="Ind2", source_files=["b.py"])

        catalog.update_status(e1.id, "IN_PROGRESS")

        in_progress = catalog.query().by_status("IN_PROGRESS").execute()

        assert len(in_progress) == 1
        assert in_progress[0]["id"] == e1.id

    def test_stats(self, temp_workspace):
        """Test catalog statistics."""
        catalog = Catalog(temp_workspace.catalog_path)

        catalog.add(entry_type="indicator", name="Ind1", source_files=["a.py"])
        catalog.add(entry_type="strategy", name="Strat1", source_files=["b.py"])
        catalog.add(entry_type="indicator", name="Ind2", source_files=["c.py"])

        stats = catalog.stats()

        assert stats.total_entries == 3
        assert stats.by_type["indicator"] == 2
        assert stats.by_type["strategy"] == 1

    def test_search(self, temp_workspace):
        """Test searching entries."""
        catalog = Catalog(temp_workspace.catalog_path)

        catalog.add(entry_type="indicator", name="McClellan Oscillator", source_files=["a.py"])
        catalog.add(entry_type="strategy", name="Momentum Strategy", source_files=["b.py"])
        catalog.add(entry_type="indicator", name="RSI Filter", source_files=["c.py"])

        results = catalog.search("momentum")

        assert len(results) >= 1
        assert any("Momentum" in r["name"] for r in results)
