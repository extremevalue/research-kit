"""Parameter optimization for walk-forward validation.

This package provides parameter optimization capabilities:
- ParameterOptimizer: Search for optimal parameters
- OptimizationResult: Results from optimization run
- WalkForwardRunner: True walk-forward optimization
- Grid search and random search methods
"""

from research_system.optimization.optimizer import (
    OptimizationMethod,
    OptimizationResult,
    ParameterOptimizer,
)
from research_system.optimization.walk_forward import (
    WalkForwardConfig,
    WalkForwardPeriod,
    WalkForwardResult,
    WalkForwardRunner,
)

__all__ = [
    "OptimizationMethod",
    "OptimizationResult",
    "ParameterOptimizer",
    "WalkForwardConfig",
    "WalkForwardPeriod",
    "WalkForwardResult",
    "WalkForwardRunner",
]
