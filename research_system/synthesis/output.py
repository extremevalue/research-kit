"""Output module for converting GeneratedIdea objects to V4 Strategy YAML.

Handles serialization of synthesis results into the workspace file structure:
- strategies/pending/{STRAT-NNN}.yaml  -- individual strategy files
- ideas/synthesis_{timestamp}.yaml     -- synthesis run reports
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

import yaml

from research_system.synthesis.quality_gate import GeneratedIdea

if TYPE_CHECKING:
    from research_system.core.v4.workspace import Workspace

logger = logging.getLogger(__name__)


# =============================================================================
# STRATEGY OUTPUT
# =============================================================================


def save_idea_as_strategy(
    idea: GeneratedIdea,
    workspace: Workspace,
    parent_strategies: list[str] | None = None,
) -> Path:
    """Convert a GeneratedIdea to V4 Strategy YAML and save to workspace.

    Generates next strategy ID from workspace, creates YAML dict matching
    the V4Strategy schema, saves to strategies/pending/{STRAT-NNN}.yaml.

    Args:
        idea: The generated idea to convert.
        workspace: V4 workspace instance.
        parent_strategies: Optional list of parent strategy IDs for lineage.

    Returns:
        Path to created file.
    """
    strategy_id = workspace.next_strategy_id()  # Returns "STRAT-NNN"

    strategy: dict[str, Any] = {
        "id": strategy_id,
        "name": idea.name,
        "version": "1.0",
        "status": "pending",
        "mode": "simple",
        "created": datetime.now().isoformat(),
        "source": {
            "type": "synthesis",
            "reference": (
                f"synthesis:{idea.persona}:{datetime.now().strftime('%Y%m%d')}"
            ),
            "author": f"synthesis-{idea.persona}",
        },
        "hypothesis": {
            "thesis": idea.hypothesis,
            "type": (
                "behavioral"
                if idea.entry_type in ("event", "fundamental")
                else "structural"
            ),
        },
        "entry": {
            "type": idea.entry_type or "technical",
            "description": idea.entry_logic,
        },
        "exit": {
            "description": idea.exit_logic,
        },
        "position": {
            "description": idea.risk_management,
        },
        "tags": {
            "custom": [
                "synthesis-generated",
                f"persona:{idea.persona}",
                f"confidence:{idea.confidence}",
            ],
        },
    }

    # Add lineage if built on existing strategies
    if parent_strategies or idea.related_strategies:
        parents = parent_strategies or idea.related_strategies
        strategy["lineage"] = {
            "parents": [
                {"id": p, "relationship": "informed"} for p in parents
            ],
        }

    # Add data requirements
    if idea.data_requirements:
        strategy["data_requirements"] = {
            "price": [{"type": "ohlcv", "symbols": idea.data_requirements}],
        }

    # Save to workspace (atomic write: temp file + rename)
    filepath = workspace.strategies_path / "pending" / f"{strategy_id}.yaml"
    filepath.parent.mkdir(parents=True, exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=filepath.parent,
        suffix=".yaml.tmp",
        prefix=f".{strategy_id}_",
    )
    try:
        with os.fdopen(tmp_fd, "w") as f:
            yaml.dump(strategy, f, default_flow_style=False, sort_keys=False)
        os.replace(tmp_path, filepath)  # Atomic on POSIX
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    logger.info("Saved strategy %s to %s", strategy_id, filepath)
    return filepath


# =============================================================================
# SYNTHESIS REPORT
# =============================================================================


def save_synthesis_report(
    ideas: list[GeneratedIdea],
    persona_responses: dict[str, str],
    workspace: Workspace,
) -> Path:
    """Save synthesis report as YAML in workspace ideas/ directory.

    Creates a timestamped YAML file summarising the synthesis run, including
    all accepted ideas and truncated persona response summaries.

    Args:
        ideas: List of accepted GeneratedIdea objects.
        persona_responses: Mapping of persona name to raw LLM response text.
        workspace: V4 workspace instance.

    Returns:
        Path to created report file.
    """
    report: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "total_ideas": len(ideas),
        "ideas": [idea.to_dict() for idea in ideas],
        "persona_summaries": {k: v[:500] for k, v in persona_responses.items()},
    }

    report_path = (
        workspace.ideas_path
        / f"synthesis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=report_path.parent,
        suffix=".yaml.tmp",
        prefix=".synthesis_",
    )
    try:
        with os.fdopen(tmp_fd, "w") as f:
            yaml.dump(report, f, default_flow_style=False, sort_keys=False)
        os.replace(tmp_path, report_path)  # Atomic on POSIX
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    logger.info("Saved synthesis report to %s", report_path)
    return report_path
