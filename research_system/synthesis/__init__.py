"""LLM-Powered Synthesis Module.

Provides intelligent strategy generation and cross-strategy analysis
using multi-persona LLM synthesis.

Two modes:
- ideate(): 3 personas generate ideas -> quality gate -> 1-3 strategies
- synthesize(): 5 specialists + director -> ranked recommendations

Example usage:
    from research_system.synthesis import SynthesisRunner
    from research_system.llm.client import LLMClient
    from research_system.core.v4 import Workspace

    workspace = Workspace("/path/to/workspace")
    runner = SynthesisRunner(workspace, LLMClient())

    # Generate new strategy ideas
    result = runner.ideate()
    for path in result.strategy_files:
        print(f"Created: {path}")

    # Full cross-strategy synthesis
    result = runner.synthesize()
    print(f"Accepted {result.ideas_accepted} ideas")
"""

from research_system.synthesis.context import (
    Learning,
    StrategyWithMetrics,
    WorkspaceContext,
    WorkspaceContextAggregator,
)
from research_system.synthesis.output import (
    save_idea_as_strategy,
    save_synthesis_report,
)
from research_system.synthesis.prompts import PromptBuilder
from research_system.synthesis.quality_gate import (
    MAX_IDEAS,
    GeneratedIdea,
    QualityGate,
    QualityResult,
    parse_ideas_from_response,
)
from research_system.synthesis.runner import SynthesisRunResult, SynthesisRunner

__all__ = [
    # Runner
    "SynthesisRunner",
    "SynthesisRunResult",
    # Context
    "WorkspaceContextAggregator",
    "WorkspaceContext",
    "StrategyWithMetrics",
    "Learning",
    # Prompts
    "PromptBuilder",
    # Quality Gate
    "QualityGate",
    "QualityResult",
    "GeneratedIdea",
    "parse_ideas_from_response",
    "MAX_IDEAS",
    # Output
    "save_idea_as_strategy",
    "save_synthesis_report",
]
