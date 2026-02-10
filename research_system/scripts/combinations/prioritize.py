"""
Prioritize combinations for testing based on expected value.

Ranks combinations using:
- Prior indicator performance
- Strategy-indicator compatibility
- Theoretical backing
- Resource requirements

Usage:
    from research_system.scripts.combinations.prioritize import prioritize_combinations
    prioritized = prioritize_combinations(matrix, validation_history)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging_config import get_logger
from combinations.generate_matrix import Combination, CombinationMatrix, load_matrix, save_matrix

logger = get_logger("combination-prioritize")


@dataclass
class PriorityFactors:
    """Factors used to calculate combination priority."""
    indicator_sharpe: float = 0.0          # Prior Sharpe ratio of indicator
    indicator_alpha: float = 0.0           # Prior alpha of indicator
    strategy_fit: float = 0.5              # How well indicator fits strategy (0-1)
    theoretical_backing: float = 0.5       # Theoretical justification (0-1)
    data_quality: float = 1.0              # Quality of data source (0-1)
    regime_robustness: float = 0.5         # Performance across regimes (0-1)
    uniqueness: float = 0.5                # How different from tested combos (0-1)
    test_cost: float = 1.0                 # Relative cost to test (lower = better)


# Strategy-indicator compatibility scores
STRATEGY_FIT_SCORES = {
    # (strategy, indicator_characteristic) -> fit score
    ("SMA_CROSSOVER", "trend_following"): 0.9,
    ("SMA_CROSSOVER", "mean_reversion"): 0.3,
    ("SMA_CROSSOVER", "breadth"): 0.7,
    ("SMA_CROSSOVER", "volatility"): 0.5,

    ("RSI_MEAN_REVERSION", "trend_following"): 0.3,
    ("RSI_MEAN_REVERSION", "mean_reversion"): 0.9,
    ("RSI_MEAN_REVERSION", "breadth"): 0.6,
    ("RSI_MEAN_REVERSION", "volatility"): 0.7,

    ("MOMENTUM", "trend_following"): 0.9,
    ("MOMENTUM", "mean_reversion"): 0.2,
    ("MOMENTUM", "breadth"): 0.8,
    ("MOMENTUM", "volatility"): 0.4,

    ("BUY_AND_HOLD", "trend_following"): 0.5,
    ("BUY_AND_HOLD", "mean_reversion"): 0.5,
    ("BUY_AND_HOLD", "breadth"): 0.6,
    ("BUY_AND_HOLD", "volatility"): 0.7,
}

# Indicator characteristics (would come from catalog in production)
INDICATOR_CHARACTERISTICS = {
    "mcclellan": "breadth",
    "advance_decline": "breadth",
    "new_high_low": "breadth",
    "vix": "volatility",
    "put_call": "volatility",
    "rsi": "mean_reversion",
    "macd": "trend_following",
    "momentum": "trend_following",
}


def get_indicator_characteristic(indicator_id: str) -> str:
    """Get the primary characteristic of an indicator."""
    indicator_lower = indicator_id.lower()

    for pattern, characteristic in INDICATOR_CHARACTERISTICS.items():
        if pattern in indicator_lower:
            return characteristic

    return "unknown"


def calculate_strategy_fit(
    indicator_id: str,
    strategy_id: str
) -> float:
    """
    Calculate how well an indicator fits with a strategy.

    Args:
        indicator_id: Indicator ID
        strategy_id: Strategy ID

    Returns:
        Fit score (0-1)
    """
    characteristic = get_indicator_characteristic(indicator_id)
    key = (strategy_id, characteristic)

    return STRATEGY_FIT_SCORES.get(key, 0.5)


def calculate_expected_value(
    combo: Combination,
    validation_history: Dict[str, Any],
    prior_weights: Dict[str, float] = None
) -> float:
    """
    Calculate expected value for a combination.

    Uses a weighted combination of factors:
    - Prior performance (40%)
    - Strategy fit (25%)
    - Theoretical backing (15%)
    - Uniqueness (10%)
    - Data quality (10%)

    Args:
        combo: Combination to evaluate
        validation_history: History of validation results
        prior_weights: Custom weights for factors

    Returns:
        Expected value score (higher = more promising)
    """
    if prior_weights is None:
        prior_weights = {
            "prior_performance": 0.40,
            "strategy_fit": 0.25,
            "theoretical_backing": 0.15,
            "uniqueness": 0.10,
            "data_quality": 0.10
        }

    # Get prior performance
    indicator_results = validation_history.get(combo.indicator_id, {})
    prior_sharpe = indicator_results.get("sharpe", 0)
    prior_alpha = indicator_results.get("alpha", 0)

    # Normalize prior performance (assume Sharpe of 1.0 is excellent)
    prior_score = min(1.0, max(0.0, (prior_sharpe + 0.5) / 1.5))

    # Get strategy fit
    fit_score = calculate_strategy_fit(combo.indicator_id, combo.base_strategy)

    # Theoretical backing (would come from catalog metadata in production)
    theoretical_score = 0.6  # Default moderate backing

    # Uniqueness (penalize if similar combinations already tested)
    tested_combos = validation_history.get("tested_combinations", [])
    similar_count = sum(
        1 for tc in tested_combos
        if tc.get("indicator_id") == combo.indicator_id
        and tc.get("base_strategy") == combo.base_strategy
    )
    uniqueness_score = 1.0 / (1 + similar_count * 0.3)

    # Data quality (would come from data registry in production)
    data_quality_score = 0.8  # Default good quality

    # Calculate weighted expected value
    expected_value = (
        prior_weights["prior_performance"] * prior_score +
        prior_weights["strategy_fit"] * fit_score +
        prior_weights["theoretical_backing"] * theoretical_score +
        prior_weights["uniqueness"] * uniqueness_score +
        prior_weights["data_quality"] * data_quality_score
    )

    return expected_value


def prioritize_combinations(
    matrix: CombinationMatrix,
    validation_history: Dict[str, Any] = None,
    top_n: Optional[int] = None
) -> CombinationMatrix:
    """
    Prioritize combinations based on expected value.

    Args:
        matrix: Combination matrix to prioritize
        validation_history: History of validation results
        top_n: Only return top N combinations

    Returns:
        Prioritized CombinationMatrix
    """
    if validation_history is None:
        validation_history = {}

    logger.info(f"Prioritizing {len(matrix.combinations)} combinations")

    # Calculate expected value for each combination
    for combo in matrix.combinations:
        combo.expected_value = calculate_expected_value(combo, validation_history)
        combo.priority = combo.expected_value

    # Sort by priority (descending)
    matrix.combinations.sort(key=lambda c: c.priority, reverse=True)

    # Optionally limit to top N
    if top_n is not None and top_n > 0:
        matrix.combinations = matrix.combinations[:top_n]
        matrix.total_combinations = len(matrix.combinations)

    logger.info(f"Top 5 combinations:")
    for combo in matrix.combinations[:5]:
        logger.info(f"  {combo.id}: priority={combo.priority:.3f}")

    return matrix


def get_next_batch(
    matrix: CombinationMatrix,
    batch_size: int = 5,
    exclude_tested: List[str] = None
) -> List[Combination]:
    """
    Get the next batch of combinations to test.

    Args:
        matrix: Prioritized combination matrix
        batch_size: Number of combinations to return
        exclude_tested: List of combination IDs already tested

    Returns:
        List of combinations to test next
    """
    if exclude_tested is None:
        exclude_tested = []

    available = [
        c for c in matrix.combinations
        if c.id not in exclude_tested
    ]

    return available[:batch_size]


def update_with_results(
    matrix: CombinationMatrix,
    results: Dict[str, Any]
) -> CombinationMatrix:
    """
    Update priorities based on new test results.

    Uses results to adjust expected values of related combinations.

    Args:
        matrix: Current combination matrix
        results: New test results {combo_id: {sharpe, alpha, success, ...}}

    Returns:
        Updated matrix with revised priorities
    """
    for combo_id, result in results.items():
        # Find the combination
        combo = next((c for c in matrix.combinations if c.id == combo_id), None)
        if not combo:
            continue

        # Update based on result
        if result.get("success"):
            # Boost priority of similar combinations
            for other in matrix.combinations:
                if other.id == combo_id:
                    continue

                similarity = 0.0
                if other.indicator_id == combo.indicator_id:
                    similarity += 0.5
                if other.base_strategy == combo.base_strategy:
                    similarity += 0.3
                if other.filter_role == combo.filter_role:
                    similarity += 0.2

                if similarity > 0:
                    boost = similarity * result.get("sharpe", 0) * 0.1
                    other.priority = min(1.0, other.priority + boost)
        else:
            # Reduce priority of similar combinations
            for other in matrix.combinations:
                if other.id == combo_id:
                    continue

                if (other.indicator_id == combo.indicator_id and
                    other.base_strategy == combo.base_strategy):
                    other.priority *= 0.8

    # Re-sort
    matrix.combinations.sort(key=lambda c: c.priority, reverse=True)

    return matrix


def suggest_novel_combinations(
    matrix: CombinationMatrix,
    validation_history: Dict[str, Any],
    n_suggestions: int = 5
) -> List[Dict[str, Any]]:
    """
    Suggest novel combinations based on patterns in validation history.

    Looks for:
    - Indicators that work well together
    - Strategies that benefit from specific indicator types
    - Unexplored combinations with high potential

    Args:
        matrix: Current combination matrix
        validation_history: History of validation results
        n_suggestions: Number of suggestions to return

    Returns:
        List of suggested combination configurations
    """
    suggestions = []

    # Find successful indicators
    successful = []
    for ind_id, results in validation_history.items():
        if isinstance(results, dict) and results.get("sharpe", 0) > 0.5:
            successful.append(ind_id)

    # Suggest combining successful indicators
    if len(successful) >= 2:
        for i, ind1 in enumerate(successful):
            for ind2 in successful[i+1:]:
                suggestions.append({
                    "type": "multi_indicator",
                    "indicators": [ind1, ind2],
                    "logic": "AND",
                    "reason": "Both indicators showed positive results independently"
                })

    # Suggest unexplored strategy + indicator combinations
    tested_pairs = set()
    for combo in matrix.combinations:
        if combo.expected_value < 0.3:  # Considered tested/low value
            tested_pairs.add((combo.indicator_id, combo.base_strategy))

    all_indicators = set(c.indicator_id for c in matrix.combinations)
    all_strategies = ["SMA_CROSSOVER", "RSI_MEAN_REVERSION", "MOMENTUM", "BUY_AND_HOLD"]

    for ind in all_indicators:
        for strat in all_strategies:
            if (ind, strat) not in tested_pairs:
                fit = calculate_strategy_fit(ind, strat)
                if fit > 0.6:
                    suggestions.append({
                        "type": "unexplored",
                        "indicator": ind,
                        "strategy": strat,
                        "fit_score": fit,
                        "reason": f"High strategy fit ({fit:.2f}) but not yet tested"
                    })

    return suggestions[:n_suggestions]


if __name__ == "__main__":
    from combinations.generate_matrix import generate_combinations

    # Example usage
    mock_entries = [
        {
            "id": "IND-001",
            "name": "McClellan Oscillator",
            "type": "indicator",
            "status": "VALIDATED"
        },
        {
            "id": "IND-002",
            "name": "VIX Filter",
            "type": "indicator",
            "status": "VALIDATED"
        },
    ]

    # Generate matrix
    matrix = generate_combinations(mock_entries)

    # Mock validation history
    history = {
        "IND-001": {"sharpe": 0.65, "alpha": 0.02},
        "IND-002": {"sharpe": 0.45, "alpha": 0.01},
        "tested_combinations": []
    }

    # Prioritize
    prioritized = prioritize_combinations(matrix, history)

    print(f"\nPrioritized Combinations")
    print(f"=" * 60)
    for i, combo in enumerate(prioritized.combinations[:10], 1):
        print(f"{i:2d}. {combo.id}")
        print(f"    Priority: {combo.priority:.3f}")
        print(f"    Strategy: {combo.base_strategy}, Role: {combo.filter_role}")

    # Get next batch
    print(f"\nNext batch to test:")
    batch = get_next_batch(prioritized, batch_size=3)
    for combo in batch:
        print(f"  - {combo.id}")

    # Suggest novel combinations
    print(f"\nNovel suggestions:")
    suggestions = suggest_novel_combinations(prioritized, history)
    for s in suggestions:
        print(f"  - {s['type']}: {s.get('indicator', s.get('indicators'))}")
        print(f"    Reason: {s['reason']}")
