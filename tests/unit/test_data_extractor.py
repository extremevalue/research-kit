"""Tests for data file extraction."""

import csv
import json
import pytest
from pathlib import Path

from research_system.ingest.data_extractor import (
    DataFileExtractor,
    DataFileInfo,
    DataExtractionResult,
    is_data_json
)


class TestCSVParsing:
    """Test CSV file parsing."""

    @pytest.fixture
    def extractor(self):
        return DataFileExtractor(llm_client=None)

    def test_parse_basic_csv(self, extractor, temp_dir):
        """Parse a basic CSV file."""
        csv_path = temp_dir / "test.csv"
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["date", "open", "high", "low", "close", "volume"])
            writer.writerow(["2024-01-01", "100", "105", "99", "104", "1000000"])
            writer.writerow(["2024-01-02", "104", "108", "103", "107", "1200000"])

        result = extractor.extract(csv_path)
        assert result.success is True
        assert result.file_info.columns == ["date", "open", "high", "low", "close", "volume"]
        assert result.file_info.row_count == 2
        assert len(result.file_info.sample_rows) == 2
        assert result.file_info.file_format == "csv"

    def test_detect_date_column(self, extractor, temp_dir):
        """Detect date column from column name."""
        csv_path = temp_dir / "test.csv"
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "value"])
            writer.writerow(["2024-01-01", "100"])
            writer.writerow(["2024-01-02", "101"])

        result = extractor.extract(csv_path)
        assert result.success is True
        assert result.file_info.date_column == "timestamp"

    def test_extract_date_range(self, extractor, temp_dir):
        """Extract date range from data."""
        csv_path = temp_dir / "test.csv"
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["date", "value"])
            writer.writerow(["2020-01-01", "100"])
            writer.writerow(["2020-06-15", "150"])
            writer.writerow(["2024-12-31", "200"])

        result = extractor.extract(csv_path)
        assert result.success is True
        assert result.file_info.date_range == ("2020-01-01", "2024-12-31")

    def test_handles_empty_csv(self, extractor, temp_dir):
        """Handle CSV with only headers."""
        csv_path = temp_dir / "empty.csv"
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["date", "value"])

        result = extractor.extract(csv_path)
        assert result.success is False
        assert "empty" in result.error.lower()

    def test_handles_semicolon_delimiter(self, extractor, temp_dir):
        """Handle CSV with semicolon delimiter."""
        csv_path = temp_dir / "test.csv"
        with open(csv_path, 'w', newline='') as f:
            f.write("date;value\n")
            f.write("2024-01-01;100\n")
            f.write("2024-01-02;101\n")

        result = extractor.extract(csv_path)
        assert result.success is True
        assert "date" in result.file_info.columns
        assert result.file_info.row_count == 2


class TestJSONParsing:
    """Test JSON data file parsing."""

    @pytest.fixture
    def extractor(self):
        return DataFileExtractor(llm_client=None)

    def test_parse_array_of_objects(self, extractor, temp_dir):
        """Parse JSON array of objects."""
        json_path = temp_dir / "data.json"
        with open(json_path, 'w') as f:
            json.dump([
                {"date": "2024-01-01", "value": 100},
                {"date": "2024-01-02", "value": 105},
                {"date": "2024-01-03", "value": 103}
            ], f)

        result = extractor.extract(json_path)
        assert result.success is True
        assert result.file_info.columns == ["date", "value"]
        assert result.file_info.row_count == 3
        assert result.file_info.file_format == "json"

    def test_rejects_non_array_json(self, extractor, temp_dir):
        """Reject JSON that is not an array."""
        json_path = temp_dir / "config.json"
        with open(json_path, 'w') as f:
            json.dump({"name": "test", "type": "config"}, f)

        result = extractor.extract(json_path)
        assert result.success is False
        assert "array" in result.error.lower()

    def test_rejects_array_of_primitives(self, extractor, temp_dir):
        """Reject JSON array of primitives."""
        json_path = temp_dir / "list.json"
        with open(json_path, 'w') as f:
            json.dump([1, 2, 3, 4, 5], f)

        result = extractor.extract(json_path)
        assert result.success is False


class TestIsDataJSON:
    """Test is_data_json detection function."""

    def test_detects_data_json(self, temp_dir):
        """Detect JSON data file (array of uniform objects)."""
        json_path = temp_dir / "data.json"
        with open(json_path, 'w') as f:
            json.dump([
                {"date": "2024-01-01", "value": 100},
                {"date": "2024-01-02", "value": 105}
            ], f)

        assert is_data_json(json_path) is True

    def test_rejects_document_json(self, temp_dir):
        """Reject document-style JSON."""
        json_path = temp_dir / "document.json"
        with open(json_path, 'w') as f:
            json.dump({
                "type": "strategy",
                "name": "Test Strategy",
                "summary": "A test strategy"
            }, f)

        assert is_data_json(json_path) is False

    def test_rejects_single_object_array(self, temp_dir):
        """Reject array with single object (can't verify uniformity)."""
        json_path = temp_dir / "single.json"
        with open(json_path, 'w') as f:
            json.dump([{"value": 100}], f)

        assert is_data_json(json_path) is False

    def test_rejects_non_uniform_objects(self, temp_dir):
        """Reject array with non-uniform objects."""
        json_path = temp_dir / "mixed.json"
        with open(json_path, 'w') as f:
            json.dump([
                {"date": "2024-01-01", "value": 100},
                {"timestamp": "2024-01-02", "price": 105}  # Different keys
            ], f)

        assert is_data_json(json_path) is False


class TestDateColumnDetection:
    """Test date column detection logic."""

    @pytest.fixture
    def extractor(self):
        return DataFileExtractor(llm_client=None)

    def test_detects_date_column(self, extractor):
        """Detect common date column names."""
        assert extractor._detect_date_column(["date", "price"], []) == "date"
        assert extractor._detect_date_column(["timestamp", "value"], []) == "timestamp"
        assert extractor._detect_date_column(["datetime", "close"], []) == "datetime"
        assert extractor._detect_date_column(["dt", "volume"], []) == "dt"

    def test_detects_partial_match(self, extractor):
        """Detect date columns with partial matches."""
        assert extractor._detect_date_column(["trade_date", "price"], []) == "trade_date"
        assert extractor._detect_date_column(["created_timestamp", "value"], []) == "created_timestamp"

    def test_returns_none_when_no_date(self, extractor):
        """Return None when no date column found."""
        assert extractor._detect_date_column(["price", "volume", "symbol"], []) is None


class TestUnsupportedFiles:
    """Test handling of unsupported file types."""

    @pytest.fixture
    def extractor(self):
        return DataFileExtractor(llm_client=None)

    def test_rejects_unsupported_extension(self, extractor, temp_dir):
        """Reject files with unsupported extensions."""
        txt_path = temp_dir / "data.txt"
        txt_path.write_text("some text data")

        result = extractor.extract(txt_path)
        assert result.success is False
        assert "unsupported" in result.error.lower()

    def test_supported_extensions(self, extractor):
        """Verify supported extensions."""
        assert ".csv" in DataFileExtractor.SUPPORTED_EXTENSIONS
        assert ".xls" in DataFileExtractor.SUPPORTED_EXTENSIONS
        assert ".xlsx" in DataFileExtractor.SUPPORTED_EXTENSIONS
        assert ".parquet" in DataFileExtractor.SUPPORTED_EXTENSIONS
        assert ".json" in DataFileExtractor.SUPPORTED_EXTENSIONS


class TestMetadataGeneration:
    """Test metadata generation without LLM."""

    @pytest.fixture
    def extractor(self):
        return DataFileExtractor(llm_client=None)

    def test_generates_fallback_metadata(self, extractor, temp_dir):
        """Generate fallback metadata when no LLM available."""
        csv_path = temp_dir / "mcclellan_oscillator.csv"
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["date", "oscillator", "summation_index"])
            writer.writerow(["2024-01-01", "50.5", "1000"])

        result = extractor.extract(csv_path)
        assert result.success is True
        assert result.metadata is not None
        assert result.metadata["name"] == "Mcclellan Oscillator"  # From filename
        assert result.metadata["type"] == "unknown"  # No LLM to classify
        assert "3 columns" in result.metadata["description"]
