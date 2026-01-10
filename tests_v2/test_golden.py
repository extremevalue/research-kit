"""Golden tests for schema stability.

Golden tests compare the current serialization output against stored "golden"
files to detect unexpected changes in schema structure. If a schema changes
intentionally, update the golden file to match.

To update golden files after intentional schema changes:
    pytest tests_v2/test_golden.py --update-golden

Or manually update the JSON file in tests_v2/fixtures/golden/
"""

import json
from pathlib import Path

from tests_v2.fixtures.sample_strategies import create_tier1_momentum_strategy

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"


def load_golden(name: str) -> dict:
    """Load a golden JSON file."""
    golden_path = GOLDEN_DIR / f"{name}.json"
    with open(golden_path) as f:
        return json.load(f)


def save_golden(name: str, data: dict) -> None:
    """Save data as a golden JSON file."""
    golden_path = GOLDEN_DIR / f"{name}.json"
    golden_path.parent.mkdir(parents=True, exist_ok=True)
    with open(golden_path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def normalize_for_comparison(data: dict) -> dict:
    """Normalize data for comparison by removing timestamps."""
    result = json.loads(json.dumps(data, default=str))
    # Remove dynamic fields that change between runs
    if "metadata" in result:
        result["metadata"].pop("created_at", None)
    return result


class TestGoldenStrategy:
    """Golden tests for strategy schema serialization."""

    def test_tier1_momentum_strategy_schema_stability(self):
        """Test that Tier 1 momentum strategy serializes consistently.

        If this test fails, either:
        1. The schema changed unintentionally - fix the code
        2. The schema changed intentionally - update the golden file
        """
        strategy = create_tier1_momentum_strategy()
        current = normalize_for_comparison(strategy.model_dump())
        golden = normalize_for_comparison(load_golden("strategy_tier1_momentum"))

        # Compare field by field for better error messages
        assert set(current.keys()) == set(golden.keys()), (
            f"Schema fields changed. "
            f"Added: {set(current.keys()) - set(golden.keys())}. "
            f"Removed: {set(golden.keys()) - set(current.keys())}"
        )

        for key in golden:
            assert current[key] == golden[key], (
                f"Field '{key}' changed.\nExpected: {golden[key]}\nGot: {current[key]}"
            )

    def test_strategy_hash_stability(self):
        """Test that strategy hash computation is stable."""
        strategy1 = create_tier1_momentum_strategy()
        strategy2 = create_tier1_momentum_strategy()

        hash1 = strategy1.compute_hash()
        hash2 = strategy2.compute_hash()

        assert hash1 == hash2, "Same strategy should produce same hash"
        assert hash1.startswith("sha256:"), "Hash should have sha256 prefix"
        assert len(hash1) == 23, "Hash should be 'sha256:' + 16 hex chars"

    def test_json_roundtrip_preserves_all_fields(self):
        """Test that JSON serialization preserves all fields exactly."""
        strategy = create_tier1_momentum_strategy()

        # Serialize to JSON and back
        json_str = strategy.model_dump_json()
        restored = strategy.model_validate_json(json_str)

        # Compare all significant fields
        assert restored.tier == strategy.tier
        assert restored.metadata.id == strategy.metadata.id
        assert restored.metadata.name == strategy.metadata.name
        assert restored.metadata.tags == strategy.metadata.tags
        assert restored.strategy_type == strategy.strategy_type
        assert restored.universe.symbols == strategy.universe.symbols
        assert restored.signal.lookback_days == strategy.signal.lookback_days
        assert restored.position_sizing.method == strategy.position_sizing.method
        assert restored.rebalance.frequency == strategy.rebalance.frequency

    def test_schema_version_present(self):
        """Test that schema version is included in serialization."""
        strategy = create_tier1_momentum_strategy()
        data = strategy.model_dump()

        assert "schema_version" in data
        assert data["schema_version"] == "2.0"


class TestGoldenSchemaFields:
    """Tests that verify required schema fields exist."""

    def test_strategy_required_fields(self):
        """Test that all required strategy fields are present."""
        strategy = create_tier1_momentum_strategy()
        data = strategy.model_dump()

        required_fields = [
            "schema_version",
            "tier",
            "metadata",
            "strategy_type",
            "universe",
            "position_sizing",
            "rebalance",
        ]

        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from strategy"

    def test_metadata_required_fields(self):
        """Test that all required metadata fields are present."""
        strategy = create_tier1_momentum_strategy()
        metadata = strategy.model_dump()["metadata"]

        required_fields = ["id", "name"]

        for field in required_fields:
            assert field in metadata, f"Required field '{field}' missing from metadata"

    def test_universe_required_fields(self):
        """Test that all required universe fields are present."""
        strategy = create_tier1_momentum_strategy()
        universe = strategy.model_dump()["universe"]

        required_fields = ["type"]

        for field in required_fields:
            assert field in universe, f"Required field '{field}' missing from universe"
