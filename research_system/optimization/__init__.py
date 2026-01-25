"""Parameter optimization for walk-forward validation.

This package provides parameter optimization capabilities:
- ParameterOptimizer: Search for optimal parameters
- OptimizationResult: Results from optimization run
- Grid search and random search methods
"""

from research_system.optimization.optimizer import (
    OptimizationMethod,
    OptimizationResult,
    ParameterOptimizer,
)

__all__ = [
    "OptimizationMethod",
    "OptimizationResult",
    "ParameterOptimizer",
]
