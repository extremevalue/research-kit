"""Parameter optimization for walk-forward validation.

This package provides parameter optimization capabilities:
- ParameterOptimizer: Search for optimal parameters
- OptimizationResult: Results from optimization run
- WalkForwardRunner: True walk-forward optimization
- Reporting: Terminal summaries and JSON export
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
from research_system.optimization.reporting import (
    format_terminal_summary,
    format_json_output,
    format_parameter_evolution,
    print_walk_forward_summary,
    print_parameter_evolution,
)

__all__ = [
    "OptimizationMethod",
    "OptimizationResult",
    "ParameterOptimizer",
    "WalkForwardConfig",
    "WalkForwardPeriod",
    "WalkForwardResult",
    "WalkForwardRunner",
    "format_terminal_summary",
    "format_json_output",
    "format_parameter_evolution",
    "print_walk_forward_summary",
    "print_parameter_evolution",
]
