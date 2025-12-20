"""
Generate systematic combination matrix for testing.

Creates all valid indicator + strategy combinations for validation:
- Each validated indicator paired with each base strategy
- Multiple filter roles (entry, exit, both)
- Parameter variations

Usage:
    from scripts.combinations.generate_matrix import generate_combinations
    combinations = generate_combinations(catalog)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from itertools import product

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging_config import get_logger

logger = get_logger("combination-matrix")


# Base strategies available for combination testing
BASE_STRATEGIES = [
    {
        "id": "SMA_CROSSOVER",
        "name": "SMA Crossover",
        "description": "Long when fast SMA > slow SMA",
        "parameters": {
            "sma_fast": 50,
            "sma_slow": 200
        }
    },
    {
        "id": "RSI_MEAN_REVERSION",
        "name": "RSI Mean Reversion",
        "description": "Buy oversold, sell overbought",
        "parameters": {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70
        }
    },
    {
        "id": "MOMENTUM",
        "name": "12-Month Momentum",
        "description": "Long when 12-month return is positive",
        "parameters": {
            "momentum_period": 252
        }
    },
    {
        "id": "BUY_AND_HOLD",
        "name": "Buy and Hold",
        "description": "Always invested in SPY",
        "parameters": {}
    }
]

# Filter roles to test
FILTER_ROLES = ["entry", "exit", "both"]

# Common parameter variations for indicators
PARAMETER_VARIATIONS = {
    "threshold_oscillator": [
        {"threshold": -50, "direction": "above"},
        {"threshold": 0, "direction": "above"},
        {"threshold": 50, "direction": "below"},
    ],
    "threshold_ratio": [
        {"threshold": 0.8, "direction": "above"},
        {"threshold": 1.0, "direction": "above"},
        {"threshold": 1.2, "direction": "below"},
    ],
    "threshold_binary": [
        {"threshold": 0, "direction": "above"},
        {"threshold": 0, "direction": "below"},
    ]
}


@dataclass
class Combination:
    """A specific indicator + strategy combination."""
    id: str
    indicator_id: str
    indicator_name: str
    base_strategy: str
    filter_role: str
    filter_column: str
    filter_threshold: float
    filter_direction: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: float = 0.0
    expected_value: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "indicator_id": self.indicator_id,
            "indicator_name": self.indicator_name,
            "base_strategy": self.base_strategy,
            "filter_role": self.filter_role,
            "filter_column": self.filter_column,
            "filter_threshold": self.filter_threshold,
            "filter_direction": self.filter_direction,
            "parameters": self.parameters,
            "priority": self.priority,
            "expected_value": self.expected_value
        }


@dataclass
class CombinationMatrix:
    """Complete matrix of combinations to test."""
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    total_combinations: int = 0
    combinations: List[Combination] = field(default_factory=list)
    by_indicator: Dict[str, int] = field(default_factory=dict)
    by_strategy: Dict[str, int] = field(default_factory=dict)
    by_role: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_combinations": self.total_combinations,
            "combinations": [c.to_dict() for c in self.combinations],
            "by_indicator": self.by_indicator,
            "by_strategy": self.by_strategy,
            "by_role": self.by_role
        }


def get_indicator_config(indicator: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get filter configuration for an indicator.

    Returns column name, threshold type, and default values.
    """
    indicator_id = indicator.get("id", "")
    indicator_type = indicator.get("type", "indicator")

    # Default configuration
    config = {
        "column": "value",
        "threshold_type": "threshold_binary",
        "default_threshold": 0,
        "default_direction": "above"
    }

    # Customize based on known indicators
    if "mcclellan" in indicator_id.lower():
        config["column"] = "mcclellan_osc"
        config["threshold_type"] = "threshold_oscillator"
        config["default_threshold"] = 0
    elif "breadth" in indicator_id.lower() or "advance" in indicator_id.lower():
        config["column"] = "ratio"
        config["threshold_type"] = "threshold_ratio"
        config["default_threshold"] = 1.0
    elif "high_low" in indicator_id.lower():
        config["column"] = "net_new_highs"
        config["threshold_type"] = "threshold_binary"
        config["default_threshold"] = 0
    elif "vix" in indicator_id.lower():
        config["column"] = "vix"
        config["threshold_type"] = "threshold_binary"
        config["default_threshold"] = 20
        config["default_direction"] = "below"  # Low VIX = risk-on

    return config


def generate_combinations_for_indicator(
    indicator: Dict[str, Any],
    base_strategies: List[Dict[str, Any]] = None,
    filter_roles: List[str] = None,
    include_variations: bool = True
) -> List[Combination]:
    """
    Generate all combinations for a single indicator.

    Args:
        indicator: Indicator entry from catalog
        base_strategies: List of base strategies (default: BASE_STRATEGIES)
        filter_roles: List of filter roles (default: FILTER_ROLES)
        include_variations: Include parameter variations

    Returns:
        List of Combination objects
    """
    if base_strategies is None:
        base_strategies = BASE_STRATEGIES
    if filter_roles is None:
        filter_roles = FILTER_ROLES

    indicator_id = indicator.get("id", "unknown")
    indicator_name = indicator.get("name", indicator_id)
    config = get_indicator_config(indicator)

    combinations = []
    combo_count = 0

    # Get threshold variations
    if include_variations:
        variations = PARAMETER_VARIATIONS.get(
            config["threshold_type"],
            [{"threshold": config["default_threshold"], "direction": config["default_direction"]}]
        )
    else:
        variations = [{"threshold": config["default_threshold"], "direction": config["default_direction"]}]

    # Generate combinations
    for strategy, role, variation in product(base_strategies, filter_roles, variations):
        combo_count += 1
        combo_id = f"{indicator_id}_{strategy['id']}_{role}_{combo_count:03d}"

        combo = Combination(
            id=combo_id,
            indicator_id=indicator_id,
            indicator_name=indicator_name,
            base_strategy=strategy["id"],
            filter_role=role,
            filter_column=config["column"],
            filter_threshold=variation["threshold"],
            filter_direction=variation["direction"],
            parameters={
                **strategy.get("parameters", {}),
                "indicator_id": indicator_id,
                "threshold": variation["threshold"],
                "direction": variation["direction"]
            }
        )
        combinations.append(combo)

    return combinations


def generate_combinations(
    catalog_entries: List[Dict[str, Any]],
    status_filter: List[str] = None,
    type_filter: str = "indicator"
) -> CombinationMatrix:
    """
    Generate complete combination matrix from catalog entries.

    Args:
        catalog_entries: List of catalog entries
        status_filter: Only include entries with these statuses
        type_filter: Only include entries of this type

    Returns:
        CombinationMatrix with all combinations
    """
    if status_filter is None:
        status_filter = ["VALIDATED", "CONDITIONAL"]

    logger.info(f"Generating combinations for {len(catalog_entries)} catalog entries")

    matrix = CombinationMatrix()

    # Filter entries
    filtered_entries = [
        e for e in catalog_entries
        if e.get("type") == type_filter
        and e.get("status") in status_filter
    ]

    logger.info(f"Found {len(filtered_entries)} {type_filter}s with status in {status_filter}")

    # Generate combinations for each indicator
    for entry in filtered_entries:
        indicator_combos = generate_combinations_for_indicator(entry)
        matrix.combinations.extend(indicator_combos)

        # Update counts
        indicator_id = entry.get("id", "unknown")
        matrix.by_indicator[indicator_id] = len(indicator_combos)

    # Update aggregate counts
    matrix.total_combinations = len(matrix.combinations)

    for combo in matrix.combinations:
        matrix.by_strategy[combo.base_strategy] = matrix.by_strategy.get(combo.base_strategy, 0) + 1
        matrix.by_role[combo.filter_role] = matrix.by_role.get(combo.filter_role, 0) + 1

    logger.info(f"Generated {matrix.total_combinations} total combinations")
    logger.info(f"By strategy: {matrix.by_strategy}")
    logger.info(f"By role: {matrix.by_role}")

    return matrix


def generate_pairwise_combinations(
    indicators: List[Dict[str, Any]],
    max_pair_size: int = 2
) -> List[Dict[str, Any]]:
    """
    Generate combinations of multiple indicators together.

    Args:
        indicators: List of indicators to combine
        max_pair_size: Maximum number of indicators to combine

    Returns:
        List of multi-indicator combination configs
    """
    from itertools import combinations as itertools_combinations

    pairwise = []

    for size in range(2, min(max_pair_size + 1, len(indicators) + 1)):
        for combo in itertools_combinations(indicators, size):
            combo_ids = [i.get("id") for i in combo]
            pairwise.append({
                "indicators": combo_ids,
                "name": " + ".join(combo_ids),
                "logic": "AND"  # All indicators must agree
            })

    logger.info(f"Generated {len(pairwise)} pairwise combinations")
    return pairwise


def save_matrix(matrix: CombinationMatrix, output_path: Path) -> None:
    """Save combination matrix to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(matrix.to_dict(), f, indent=2)

    logger.info(f"Saved combination matrix to {output_path}")


def load_matrix(input_path: Path) -> CombinationMatrix:
    """Load combination matrix from JSON file."""
    with open(input_path, 'r') as f:
        data = json.load(f)

    matrix = CombinationMatrix(
        generated_at=data["generated_at"],
        total_combinations=data["total_combinations"],
        by_indicator=data.get("by_indicator", {}),
        by_strategy=data.get("by_strategy", {}),
        by_role=data.get("by_role", {})
    )

    for c in data.get("combinations", []):
        matrix.combinations.append(Combination(
            id=c["id"],
            indicator_id=c["indicator_id"],
            indicator_name=c["indicator_name"],
            base_strategy=c["base_strategy"],
            filter_role=c["filter_role"],
            filter_column=c["filter_column"],
            filter_threshold=c["filter_threshold"],
            filter_direction=c["filter_direction"],
            parameters=c.get("parameters", {}),
            priority=c.get("priority", 0.0),
            expected_value=c.get("expected_value", 0.0)
        ))

    return matrix


if __name__ == "__main__":
    # Example usage with mock catalog entries
    mock_entries = [
        {
            "id": "IND-001",
            "name": "McClellan Oscillator",
            "type": "indicator",
            "status": "VALIDATED"
        },
        {
            "id": "IND-002",
            "name": "NYSE Advance/Decline Ratio",
            "type": "indicator",
            "status": "VALIDATED"
        },
        {
            "id": "IND-003",
            "name": "New Highs New Lows",
            "type": "indicator",
            "status": "CONDITIONAL"
        }
    ]

    matrix = generate_combinations(mock_entries)

    print(f"\nCombination Matrix")
    print(f"=" * 50)
    print(f"Total combinations: {matrix.total_combinations}")
    print(f"\nBy Indicator:")
    for ind, count in matrix.by_indicator.items():
        print(f"  {ind}: {count}")
    print(f"\nBy Strategy:")
    for strat, count in matrix.by_strategy.items():
        print(f"  {strat}: {count}")
    print(f"\nBy Filter Role:")
    for role, count in matrix.by_role.items():
        print(f"  {role}: {count}")

    print(f"\nSample combinations:")
    for combo in matrix.combinations[:5]:
        print(f"  {combo.id}: {combo.indicator_name} + {combo.base_strategy} ({combo.filter_role})")
