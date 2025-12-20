"""
Schema validation utilities for the Research Validation System.

Provides functions to validate JSON data against JSON Schema definitions.
All writes to catalog, validations, and data registry must pass validation.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

try:
    import jsonschema
    from jsonschema import Draft7Validator, ValidationError
except ImportError:
    raise ImportError("jsonschema package required. Install with: pip install jsonschema")


# Schema directory relative to this file
SCHEMA_DIR = Path(__file__).parent.parent.parent / "schemas"


@dataclass
class ValidationResult:
    """Result of schema validation."""
    valid: bool
    errors: List[str]
    schema_name: str
    validated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "schema_name": self.schema_name,
            "validated_at": self.validated_at
        }


class SchemaValidator:
    """Validates JSON data against schema definitions."""

    # Cache for loaded schemas
    _schema_cache: Dict[str, Dict[str, Any]] = {}

    # Available schemas
    SCHEMAS = {
        "catalog-entry": "catalog-entry.schema.json",
        "validation-result": "validation-result.schema.json",
        "data-source": "data-source.schema.json",
        "hypothesis": "hypothesis.schema.json",
        "persona-output": "persona-output.schema.json",
        "synthesis-output": "synthesis-output.schema.json",
        "backtest-result": "backtest-result.schema.json",
    }

    def __init__(self, schema_dir: Optional[Path] = None):
        """Initialize validator with schema directory."""
        self.schema_dir = schema_dir or SCHEMA_DIR
        if not self.schema_dir.exists():
            raise FileNotFoundError(f"Schema directory not found: {self.schema_dir}")

    def _load_schema(self, schema_name: str) -> Dict[str, Any]:
        """Load and cache a schema by name."""
        if schema_name in self._schema_cache:
            return self._schema_cache[schema_name]

        if schema_name not in self.SCHEMAS:
            raise ValueError(f"Unknown schema: {schema_name}. Available: {list(self.SCHEMAS.keys())}")

        schema_path = self.schema_dir / self.SCHEMAS[schema_name]
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        with open(schema_path, 'r') as f:
            schema = json.load(f)

        self._schema_cache[schema_name] = schema
        return schema

    def validate(self, data: Dict[str, Any], schema_name: str) -> ValidationResult:
        """
        Validate data against a named schema.

        Args:
            data: JSON-serializable dict to validate
            schema_name: Name of schema (e.g., 'catalog-entry', 'hypothesis')

        Returns:
            ValidationResult with valid=True if passes, errors list if fails
        """
        schema = self._load_schema(schema_name)
        validator = Draft7Validator(schema)

        errors = []
        for error in validator.iter_errors(data):
            # Build readable error path
            path = " -> ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
            errors.append(f"{path}: {error.message}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            schema_name=schema_name,
            validated_at=datetime.utcnow().isoformat() + "Z"
        )

    def validate_file(self, file_path: Path, schema_name: str) -> ValidationResult:
        """Validate a JSON file against a schema."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        return self.validate(data, schema_name)

    def is_valid(self, data: Dict[str, Any], schema_name: str) -> bool:
        """Quick check if data is valid (no error details)."""
        return self.validate(data, schema_name).valid

    def require_valid(self, data: Dict[str, Any], schema_name: str) -> None:
        """
        Validate and raise exception if invalid.

        Use this as a gate before writing data.
        """
        result = self.validate(data, schema_name)
        if not result.valid:
            error_summary = "; ".join(result.errors[:5])  # First 5 errors
            if len(result.errors) > 5:
                error_summary += f"... and {len(result.errors) - 5} more"
            raise ValueError(f"Schema validation failed for {schema_name}: {error_summary}")


# Convenience functions for common validations

_default_validator: Optional[SchemaValidator] = None

def get_validator() -> SchemaValidator:
    """Get or create the default validator instance."""
    global _default_validator
    if _default_validator is None:
        _default_validator = SchemaValidator()
    return _default_validator


def validate_catalog_entry(data: Dict[str, Any]) -> ValidationResult:
    """Validate a catalog entry."""
    return get_validator().validate(data, "catalog-entry")


def validate_hypothesis(data: Dict[str, Any]) -> ValidationResult:
    """Validate a hypothesis."""
    return get_validator().validate(data, "hypothesis")


def validate_validation_result(data: Dict[str, Any]) -> ValidationResult:
    """Validate a validation result/metadata."""
    return get_validator().validate(data, "validation-result")


def validate_data_source(data: Dict[str, Any]) -> ValidationResult:
    """Validate a data source registry entry."""
    return get_validator().validate(data, "data-source")


def validate_backtest_result(data: Dict[str, Any]) -> ValidationResult:
    """Validate a backtest result."""
    return get_validator().validate(data, "backtest-result")


def validate_persona_output(data: Dict[str, Any]) -> ValidationResult:
    """Validate persona agent output."""
    return get_validator().validate(data, "persona-output")


def validate_synthesis_output(data: Dict[str, Any]) -> ValidationResult:
    """Validate synthesis output."""
    return get_validator().validate(data, "synthesis-output")


def require_valid_catalog_entry(data: Dict[str, Any]) -> None:
    """Validate catalog entry or raise exception."""
    get_validator().require_valid(data, "catalog-entry")


def require_valid_hypothesis(data: Dict[str, Any]) -> None:
    """Validate hypothesis or raise exception."""
    get_validator().require_valid(data, "hypothesis")


if __name__ == "__main__":
    # Self-test
    import sys

    print("Testing schema validator...")
    validator = SchemaValidator()

    # Test valid catalog entry
    valid_entry = {
        "id": "IND-001",
        "name": "Test Indicator",
        "type": "indicator",
        "status": "UNTESTED",
        "created_at": "2025-01-01T00:00:00Z",
        "source": {
            "files": ["archive/test.py"],
            "ingested_at": "2025-01-01T00:00:00Z"
        }
    }

    result = validator.validate(valid_entry, "catalog-entry")
    print(f"Valid entry test: {'PASS' if result.valid else 'FAIL'}")

    # Test invalid entry (missing required field)
    invalid_entry = {
        "id": "IND-001",
        "name": "Test",
        # missing type, status, created_at, source
    }

    result = validator.validate(invalid_entry, "catalog-entry")
    print(f"Invalid entry test: {'PASS' if not result.valid else 'FAIL'}")
    if result.errors:
        print(f"  Errors caught: {len(result.errors)}")

    # Test invalid ID pattern
    bad_id_entry = {
        "id": "invalid-id",  # Wrong pattern
        "name": "Test",
        "type": "indicator",
        "status": "UNTESTED",
        "created_at": "2025-01-01T00:00:00Z",
        "source": {
            "files": ["test.py"],
            "ingested_at": "2025-01-01T00:00:00Z"
        }
    }

    result = validator.validate(bad_id_entry, "catalog-entry")
    print(f"Bad ID pattern test: {'PASS' if not result.valid else 'FAIL'}")

    print("\nAll tests completed.")
