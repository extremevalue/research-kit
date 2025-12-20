"""Tests for data registry management."""

import pytest
from pathlib import Path

from research_system.core.data_registry import DataRegistry, DataSource


class TestDataRegistry:
    """Tests for DataRegistry class."""

    def test_list_empty(self, temp_workspace):
        """Test listing empty registry."""
        registry = DataRegistry(temp_workspace.data_registry_path)

        sources = registry.list()

        # May have default sources or be empty depending on init
        assert isinstance(sources, list)

    def test_add_source(self, temp_workspace):
        """Test adding a data source."""
        registry = DataRegistry(temp_workspace.data_registry_path)

        source = registry.add(
            source_id="test_data",
            name="Test Data Source",
            data_type="price_data"
        )

        assert source.id == "test_data"
        assert source.name == "Test Data Source"

    def test_get_source(self, temp_workspace):
        """Test getting a data source."""
        registry = DataRegistry(temp_workspace.data_registry_path)

        registry.add(
            source_id="test_data",
            name="Test Data Source",
            data_type="price_data"
        )

        retrieved = registry.get("test_data")

        assert retrieved is not None
        assert retrieved.id == "test_data"

    def test_get_nonexistent(self, temp_workspace):
        """Test getting nonexistent source returns None."""
        registry = DataRegistry(temp_workspace.data_registry_path)

        result = registry.get("nonexistent")

        assert result is None

    def test_check_availability(self, temp_workspace):
        """Test checking availability of multiple sources."""
        registry = DataRegistry(temp_workspace.data_registry_path)

        registry.add(
            source_id="available_data",
            name="Available Data",
            data_type="price_data"
        )

        # Update availability
        registry.update_availability(
            "available_data",
            tier="qc_native",
            available=True,
            key="Equity/USA/test"
        )

        results = registry.check_availability(["available_data", "missing_data"])

        assert "available_data" in results
        assert "missing_data" in results
        assert results["available_data"].available
        assert not results["missing_data"].available


class TestDataSource:
    """Tests for DataSource class."""

    def test_is_available_true(self, sample_data_source):
        """Test is_available returns True when available."""
        source = DataSource(
            id=sample_data_source["id"],
            name=sample_data_source["name"],
            data_type=sample_data_source["data_type"],
            description=sample_data_source.get("description"),
            availability=sample_data_source.get("availability", {}),
            coverage=sample_data_source.get("coverage")
        )

        assert source.is_available()

    def test_best_source(self, sample_data_source):
        """Test best_source returns highest priority tier."""
        source = DataSource(
            id=sample_data_source["id"],
            name=sample_data_source["name"],
            data_type=sample_data_source["data_type"],
            description=sample_data_source.get("description"),
            availability=sample_data_source.get("availability", {}),
            coverage=sample_data_source.get("coverage")
        )

        best = source.best_source()

        assert best.available
        assert best.source_tier == "qc_native"
