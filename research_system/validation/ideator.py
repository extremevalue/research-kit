"""V4 Strategy Ideator - Generate new strategy ideas.

This module generates new strategy ideas based on:
- Existing validated strategies
- Learnings from failed validations
- Common strategy patterns and variations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class StrategyIdea:
    """A strategy idea generated from analysis."""
    id: str
    name: str
    description: str
    based_on: str | None  # Parent strategy ID if derived
    variation_type: str | None  # e.g., "timeframe", "instrument", "parameter"
    hypothesis: str
    suggested_changes: list[str] = field(default_factory=list)
    priority: str = "medium"  # low, medium, high
    created: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "based_on": self.based_on,
            "variation_type": self.variation_type,
            "hypothesis": self.hypothesis,
            "suggested_changes": self.suggested_changes,
            "priority": self.priority,
            "created": self.created.isoformat(),
            "status": "pending",
        }


class Ideator:
    """Ideator for generating new strategy ideas."""

    # Common variation types
    VARIATION_TEMPLATES = [
        {
            "type": "timeframe",
            "name": "{name} - Extended Timeframe",
            "description": "Test with longer holding period",
            "changes": [
                "Extend holding period by 2x",
                "Adjust stop loss proportionally",
                "Consider weekly instead of daily signals",
            ],
        },
        {
            "type": "instrument",
            "name": "{name} - Alternative Universe",
            "description": "Apply same logic to different instruments",
            "changes": [
                "Test on sector ETFs instead of broad market",
                "Consider international markets",
                "Try with futures instead of ETFs",
            ],
        },
        {
            "type": "filter",
            "name": "{name} - With Regime Filter",
            "description": "Add market regime filter",
            "changes": [
                "Only trade in trending markets (ADX > 25)",
                "Avoid trading during high correlation periods",
                "Add volatility regime filter",
            ],
        },
        {
            "type": "sizing",
            "name": "{name} - Volatility Sizing",
            "description": "Use volatility-adjusted position sizing",
            "changes": [
                "Scale position size inversely with volatility",
                "Use ATR-based position sizing",
                "Implement risk parity allocation",
            ],
        },
        {
            "type": "combination",
            "name": "{name} - Multi-Signal",
            "description": "Combine with additional confirmation signals",
            "changes": [
                "Add momentum confirmation",
                "Require volume confirmation",
                "Add mean reversion filter for entries",
            ],
        },
    ]

    def __init__(self, workspace):
        """Initialize ideator.

        Args:
            workspace: V4Workspace instance
        """
        self.workspace = workspace

    def generate_ideas(
        self,
        strategies: list[dict] | None = None,
        learnings: list[dict] | None = None,
        max_ideas: int = 5,
    ) -> list[StrategyIdea]:
        """Generate strategy ideas.

        Args:
            strategies: List of existing strategies to derive from
            learnings: List of learnings documents
            max_ideas: Maximum number of ideas to generate

        Returns:
            List of StrategyIdea objects
        """
        ideas = []

        # If we have strategies, generate variations
        if strategies:
            for strategy in strategies[:3]:  # Limit to top 3 strategies
                strategy_ideas = self._generate_variations(strategy)
                ideas.extend(strategy_ideas)

        # If we have learnings, generate ideas from failures
        if learnings:
            failure_ideas = self._generate_from_learnings(learnings)
            ideas.extend(failure_ideas)

        # If no strategies, generate generic ideas
        if not strategies and not learnings:
            ideas.extend(self._generate_generic_ideas())

        # Assign IDs and limit
        next_id = self._get_next_idea_id()
        for i, idea in enumerate(ideas[:max_ideas]):
            idea.id = f"IDEA-{next_id + i:03d}"

        return ideas[:max_ideas]

    def _generate_variations(self, strategy: dict) -> list[StrategyIdea]:
        """Generate variation ideas from a strategy."""
        ideas = []
        strategy_name = strategy.get("name", "Unknown Strategy")
        strategy_id = strategy.get("id", "unknown")

        for template in self.VARIATION_TEMPLATES[:3]:  # Limit variations per strategy
            idea = StrategyIdea(
                id="PENDING",
                name=template["name"].format(name=strategy_name),
                description=template["description"],
                based_on=strategy_id,
                variation_type=template["type"],
                hypothesis=f"Variation of {strategy_name}: {template['description']}",
                suggested_changes=template["changes"],
            )
            ideas.append(idea)

        return ideas

    def _generate_from_learnings(self, learnings: list[dict]) -> list[StrategyIdea]:
        """Generate ideas from learnings (especially failures)."""
        ideas = []

        for learning_doc in learnings:
            # Look for failure insights
            for learning in learning_doc.get("learnings", []):
                if learning.get("type") == "failure":
                    recommendation = learning.get("recommendation")
                    if recommendation:
                        idea = StrategyIdea(
                            id="PENDING",
                            name=f"Fix: {learning.get('insight', 'Unknown')[:50]}",
                            description=f"Address issue from {learning_doc.get('strategy_id', 'unknown')}",
                            based_on=learning_doc.get("strategy_id"),
                            variation_type="fix",
                            hypothesis=f"Fixing identified issue: {recommendation}",
                            suggested_changes=[recommendation],
                            priority="high",
                        )
                        ideas.append(idea)

        return ideas

    def _generate_generic_ideas(self) -> list[StrategyIdea]:
        """Generate generic strategy ideas when no existing strategies."""
        generic_ideas = [
            StrategyIdea(
                id="PENDING",
                name="Volatility Mean Reversion",
                description="Trade mean reversion in volatility",
                based_on=None,
                variation_type=None,
                hypothesis="VIX tends to mean-revert after spikes",
                suggested_changes=[
                    "Buy SPY when VIX spikes above 25 then drops below 20",
                    "Use 5% trailing stop",
                    "Exit if VIX exceeds 30",
                ],
            ),
            StrategyIdea(
                id="PENDING",
                name="Momentum + Quality",
                description="Combine momentum with quality factors",
                based_on=None,
                variation_type=None,
                hypothesis="High-quality momentum stocks outperform",
                suggested_changes=[
                    "Screen for top momentum stocks",
                    "Filter by quality metrics (ROE, debt ratio)",
                    "Rebalance monthly",
                ],
            ),
            StrategyIdea(
                id="PENDING",
                name="Trend Following ETFs",
                description="Simple trend following on major ETFs",
                based_on=None,
                variation_type=None,
                hypothesis="Trends persist in major asset classes",
                suggested_changes=[
                    "Use 200-day moving average as trend filter",
                    "Trade SPY, TLT, GLD, UUP",
                    "Risk parity position sizing",
                ],
            ),
        ]
        return generic_ideas

    def _get_next_idea_id(self) -> int:
        """Get the next available idea ID number."""
        ideas_path = self.workspace.path / "ideas"
        if not ideas_path.exists():
            return 1

        existing_ids = []
        for filepath in ideas_path.glob("IDEA-*.yaml"):
            try:
                num = int(filepath.stem.split("-")[1])
                existing_ids.append(num)
            except (IndexError, ValueError):
                pass

        return max(existing_ids, default=0) + 1

    def save_ideas(
        self,
        ideas: list[StrategyIdea],
        dry_run: bool = False,
    ) -> list[Path]:
        """Save ideas to the ideas directory.

        Args:
            ideas: List of StrategyIdea objects to save
            dry_run: If True, don't actually save

        Returns:
            List of paths to saved files
        """
        if dry_run:
            return []

        ideas_path = self.workspace.path / "ideas"
        ideas_path.mkdir(parents=True, exist_ok=True)

        saved_paths = []
        for idea in ideas:
            filepath = ideas_path / f"{idea.id}.yaml"
            with open(filepath, "w") as f:
                yaml.dump(idea.to_dict(), f, default_flow_style=False, sort_keys=False)
            saved_paths.append(filepath)

        return saved_paths

    def list_ideas(self) -> list[dict]:
        """List existing ideas.

        Returns:
            List of idea dictionaries
        """
        ideas_path = self.workspace.path / "ideas"
        if not ideas_path.exists():
            return []

        ideas = []
        for filepath in sorted(ideas_path.glob("IDEA-*.yaml")):
            with open(filepath) as f:
                idea = yaml.safe_load(f)
                if idea:
                    idea["_file"] = str(filepath)
                    ideas.append(idea)

        return ideas


# Backward-compat alias
V4Ideator = Ideator
