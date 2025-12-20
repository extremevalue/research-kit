"""
Combination generation and prioritization module.

Provides functionality for creating and ranking indicator + strategy combinations.

Components:
    - generate_matrix: Create systematic combination matrix
    - prioritize: Rank combinations by expected value

Usage:
    from scripts.combinations import generate_combinations, prioritize_combinations

    matrix = generate_combinations(catalog_entries)
    prioritized = prioritize_combinations(matrix, validation_history)
"""

from .generate_matrix import (
    generate_combinations,
    generate_combinations_for_indicator,
    generate_pairwise_combinations,
    Combination,
    CombinationMatrix,
    BASE_STRATEGIES,
    FILTER_ROLES,
    save_matrix,
    load_matrix,
)

from .prioritize import (
    prioritize_combinations,
    calculate_expected_value,
    get_next_batch,
    update_with_results,
    suggest_novel_combinations,
    PriorityFactors,
)

__all__ = [
    # Matrix generation
    "generate_combinations",
    "generate_combinations_for_indicator",
    "generate_pairwise_combinations",
    "Combination",
    "CombinationMatrix",
    "BASE_STRATEGIES",
    "FILTER_ROLES",
    "save_matrix",
    "load_matrix",

    # Prioritization
    "prioritize_combinations",
    "calculate_expected_value",
    "get_next_batch",
    "update_with_results",
    "suggest_novel_combinations",
    "PriorityFactors",
]
