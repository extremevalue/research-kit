"""Workspace context aggregation for LLM synthesis prompts.

Reads a V4 workspace and aggregates strategy data + validation metrics
into structured context objects suitable for feeding into LLM synthesis
prompts.

Workspace structure consumed:
    strategies/{validated,invalidated,pending}/*.yaml
    validations/{STRAT-NNN}/backtest_results.{yaml,json}
    validations/{STRAT-NNN}/determination.json
    validations/{STRAT-NNN}/walk_forward_results.yaml
    learnings/*.yaml
    ideas/*.yaml
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from research_system.core.v4.workspace import Workspace

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class StrategyWithMetrics:
    """A strategy document enriched with its validation metrics."""

    id: str                                    # e.g., "STRAT-001"
    name: str
    status: str                                # "validated", "invalidated", "pending"
    hypothesis: str                            # From strategy.hypothesis.thesis
    entry_type: str                            # From strategy.entry.type
    instruments: list[str]                     # From strategy.universe
    sharpe: float | None = None
    cagr: float | None = None
    max_drawdown: float | None = None
    calmar: float | None = None
    consistency: float | None = None           # % of walk-forward windows profitable
    total_trades: int | None = None
    per_window: list[dict] | None = None       # Per walk-forward window metrics
    determination_reason: str | None = None    # Why it was validated/invalidated
    tags: list[str] = field(default_factory=list)

    def to_summary_line(self) -> str:
        """Format as a concise single-line summary suitable for LLM prompts."""
        metrics: list[str] = []
        if self.sharpe is not None:
            metrics.append(f"Sharpe={self.sharpe:.2f}")
        if self.cagr is not None:
            metrics.append(f"CAGR={self.cagr * 100:.1f}%")
        if self.max_drawdown is not None:
            metrics.append(f"MaxDD={self.max_drawdown * 100:.1f}%")
        if self.consistency is not None:
            metrics.append(f"Consistency={self.consistency * 100:.0f}%")
        metrics_str = ", ".join(metrics) if metrics else "No metrics"
        return (
            f"- {self.id} [{self.status}]: {self.name} [{metrics_str}]\n"
            f"  Hypothesis: {self.hypothesis[:150]}"
        )


@dataclass
class Learning:
    """A single learning extracted from a validation cycle."""

    strategy_id: str
    category: str           # e.g., "parameter", "regime", "data"
    description: str
    action: str             # What was done differently


@dataclass
class WorkspaceContext:
    """Full aggregated context from a V4 workspace."""

    validated: list[StrategyWithMetrics]
    invalidated: list[StrategyWithMetrics]
    pending: list[StrategyWithMetrics]
    learnings: list[Learning]
    available_data: list[str]             # From DataRegistry if available
    summary_stats: dict[str, Any]         # Counts, avg metrics, etc.


# =============================================================================
# AGGREGATOR
# =============================================================================


class WorkspaceContextAggregator:
    """Read all workspace data and build a WorkspaceContext for LLM prompts.

    Usage::

        from research_system.core.v4.workspace import Workspace

        ws = Workspace("/path/to/workspace")
        ctx = WorkspaceContextAggregator(ws).aggregate()
    """

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def aggregate(self) -> WorkspaceContext:
        """Read all workspace data and build context."""
        validated = self._load_strategies("validated")
        invalidated = self._load_strategies("invalidated")
        pending = self._load_strategies("pending")
        learnings = self._load_learnings()
        available_data = self._load_available_data()
        summary_stats = self._build_summary_stats(validated, invalidated, pending)

        return WorkspaceContext(
            validated=validated,
            invalidated=invalidated,
            pending=pending,
            learnings=learnings,
            available_data=available_data,
            summary_stats=summary_stats,
        )

    # ------------------------------------------------------------------
    # Strategy loading
    # ------------------------------------------------------------------

    def _load_strategies(self, status: str) -> list[StrategyWithMetrics]:
        """Load all strategies for a given status directory."""
        status_dir = self.workspace.strategies_path / status
        if not status_dir.exists():
            return []

        strategies: list[StrategyWithMetrics] = []
        for yaml_file in sorted(status_dir.glob("*.yaml")):
            try:
                strat = self._parse_strategy_file(yaml_file, status)
                if strat is not None:
                    self._enrich_with_validation(strat)
                    strategies.append(strat)
            except Exception:
                logger.warning("Skipping malformed strategy file: %s", yaml_file, exc_info=True)
        return strategies

    def _parse_strategy_file(self, path: Path, status: str) -> StrategyWithMetrics | None:
        """Parse a single strategy YAML file into a StrategyWithMetrics."""
        with open(path) as fh:
            data = yaml.safe_load(fh)

        if not isinstance(data, dict):
            logger.warning("Strategy file is not a YAML mapping: %s", path)
            return None

        strategy_id = data.get("id", path.stem)
        name = data.get("name", "Unknown")

        # Hypothesis - support both V4 (summary/detail) and legacy (thesis) formats
        hypothesis_data = data.get("hypothesis", {})
        if isinstance(hypothesis_data, dict):
            hypothesis = (
                hypothesis_data.get("thesis")
                or hypothesis_data.get("summary")
                or hypothesis_data.get("detail")
                or ""
            )
        elif isinstance(hypothesis_data, str):
            hypothesis = hypothesis_data
        else:
            hypothesis = ""

        # Entry type
        entry_data = data.get("entry", {})
        if isinstance(entry_data, dict):
            entry_type = entry_data.get("type", "unknown")
        else:
            entry_type = "unknown"

        # Instruments from universe
        instruments = self._extract_instruments(data.get("universe", {}))

        # Tags - support dict with 'custom' key or plain list
        raw_tags = data.get("tags", {})
        if isinstance(raw_tags, dict):
            tag_list: list[str] = raw_tags.get("custom", [])
            # Also pull hypothesis_type/asset_class as tags
            for key in ("hypothesis_type", "asset_class"):
                extra = raw_tags.get(key, [])
                if isinstance(extra, list):
                    tag_list.extend(str(t) for t in extra)
                elif isinstance(extra, str):
                    tag_list.append(extra)
        elif isinstance(raw_tags, list):
            tag_list = [str(t) for t in raw_tags]
        else:
            tag_list = []

        return StrategyWithMetrics(
            id=strategy_id,
            name=name,
            status=status,
            hypothesis=hypothesis,
            entry_type=entry_type,
            instruments=instruments,
            tags=tag_list,
        )

    @staticmethod
    def _extract_instruments(universe: Any) -> list[str]:
        """Extract instrument symbols from a universe definition."""
        if not isinstance(universe, dict):
            return []

        instruments_raw = universe.get("instruments", [])
        symbols: list[str] = []
        for item in instruments_raw:
            if isinstance(item, dict):
                sym = item.get("symbol")
                if sym:
                    symbols.append(str(sym))
            elif isinstance(item, str):
                symbols.append(item)
        return symbols

    # ------------------------------------------------------------------
    # Validation enrichment
    # ------------------------------------------------------------------

    def _enrich_with_validation(self, strat: StrategyWithMetrics) -> None:
        """Enrich a strategy with data from its validations/ directory."""
        val_dir = self.workspace.validations_path / strat.id
        if not val_dir.is_dir():
            return

        # Backtest results (YAML or JSON)
        self._load_backtest_results(strat, val_dir)

        # Walk-forward results
        self._load_walk_forward_results(strat, val_dir)

        # Determination
        self._load_determination(strat, val_dir)

    def _load_backtest_results(self, strat: StrategyWithMetrics, val_dir: Path) -> None:
        """Load backtest metrics from backtest_results.yaml or .json."""
        data: dict[str, Any] | None = None

        yaml_path = val_dir / "backtest_results.yaml"
        json_path = val_dir / "backtest_results.json"

        try:
            if yaml_path.exists():
                with open(yaml_path) as fh:
                    data = yaml.safe_load(fh)
            elif json_path.exists():
                with open(json_path) as fh:
                    data = json.load(fh)
        except Exception:
            logger.warning(
                "Failed to read backtest results for %s", strat.id, exc_info=True
            )
            return

        if not isinstance(data, dict):
            return

        strat.sharpe = _safe_float(data.get("sharpe_ratio") or data.get("sharpe"))
        strat.cagr = _safe_float(data.get("cagr"))
        strat.max_drawdown = _safe_float(data.get("max_drawdown"))
        strat.calmar = _safe_float(data.get("calmar") or data.get("calmar_ratio"))
        strat.consistency = _safe_float(data.get("consistency"))
        strat.total_trades = _safe_int(data.get("total_trades"))

    def _load_walk_forward_results(self, strat: StrategyWithMetrics, val_dir: Path) -> None:
        """Load per-window walk-forward results."""
        wf_path = val_dir / "walk_forward_results.yaml"
        if not wf_path.exists():
            return

        try:
            with open(wf_path) as fh:
                data = yaml.safe_load(fh)
        except Exception:
            logger.warning(
                "Failed to read walk-forward results for %s", strat.id, exc_info=True
            )
            return

        if not isinstance(data, dict):
            return

        windows = data.get("windows", [])
        if not isinstance(windows, list):
            return

        strat.per_window = windows

        # Compute consistency from windows if not already set from backtest_results
        if strat.consistency is None and windows:
            profitable = sum(
                1
                for w in windows
                if isinstance(w, dict) and _safe_float(w.get("sharpe_ratio") or w.get("sharpe"), 0.0) > 0
            )
            strat.consistency = profitable / len(windows) if windows else None

    def _load_determination(self, strat: StrategyWithMetrics, val_dir: Path) -> None:
        """Load determination.json for the validation verdict."""
        det_path = val_dir / "determination.json"
        if not det_path.exists():
            return

        try:
            with open(det_path) as fh:
                data = json.load(fh)
        except Exception:
            logger.warning(
                "Failed to read determination for %s", strat.id, exc_info=True
            )
            return

        if not isinstance(data, dict):
            return

        strat.determination_reason = data.get("reason")

    # ------------------------------------------------------------------
    # Learnings
    # ------------------------------------------------------------------

    def _load_learnings(self) -> list[Learning]:
        """Load all learning files from the learnings/ directory."""
        learnings_dir = self.workspace.learnings_path
        if not learnings_dir.exists():
            return []

        learnings: list[Learning] = []
        for yaml_file in sorted(learnings_dir.glob("*.yaml")):
            try:
                with open(yaml_file) as fh:
                    data = yaml.safe_load(fh)

                if not isinstance(data, dict):
                    continue

                # Support both flat learning docs and docs with a learnings list
                raw_learnings = data.get("learnings", [])
                strategy_id = data.get("strategy_id", yaml_file.stem)

                if isinstance(raw_learnings, list):
                    for item in raw_learnings:
                        if not isinstance(item, dict):
                            continue
                        learnings.append(Learning(
                            strategy_id=str(strategy_id),
                            category=item.get("category", "unknown"),
                            description=item.get("insight") or item.get("description", ""),
                            action=item.get("recommendation") or item.get("action", ""),
                        ))
                else:
                    # Single-learning file
                    learnings.append(Learning(
                        strategy_id=str(strategy_id),
                        category=data.get("category", "unknown"),
                        description=data.get("insight") or data.get("description", ""),
                        action=data.get("recommendation") or data.get("action", ""),
                    ))

            except Exception:
                logger.warning("Skipping malformed learnings file: %s", yaml_file, exc_info=True)
        return learnings

    # ------------------------------------------------------------------
    # Data registry
    # ------------------------------------------------------------------

    def _load_available_data(self) -> list[str]:
        """Try loading the DataRegistry and listing available data sources."""
        try:
            from research_system.core.data_registry import DataRegistry

            # The workspace stores the data registry under a known path
            registry_path = self.workspace.path / "data-registry"
            if not registry_path.exists():
                return []

            registry = DataRegistry(registry_path)
            sources = registry.list(available_only=True)
            return [s.name for s in sources]
        except Exception:
            logger.debug("DataRegistry not available, skipping.", exc_info=True)
            return []

    # ------------------------------------------------------------------
    # Summary stats
    # ------------------------------------------------------------------

    @staticmethod
    def _build_summary_stats(
        validated: list[StrategyWithMetrics],
        invalidated: list[StrategyWithMetrics],
        pending: list[StrategyWithMetrics],
    ) -> dict[str, Any]:
        """Build aggregate summary statistics for the workspace."""
        all_strategies = validated + invalidated + pending

        stats: dict[str, Any] = {
            "total_strategies": len(all_strategies),
            "validated_count": len(validated),
            "invalidated_count": len(invalidated),
            "pending_count": len(pending),
        }

        # Average metrics across validated strategies
        if validated:
            sharpes = [s.sharpe for s in validated if s.sharpe is not None]
            cagrs = [s.cagr for s in validated if s.cagr is not None]
            drawdowns = [s.max_drawdown for s in validated if s.max_drawdown is not None]
            consistencies = [s.consistency for s in validated if s.consistency is not None]

            if sharpes:
                stats["avg_sharpe"] = sum(sharpes) / len(sharpes)
                stats["best_sharpe"] = max(sharpes)
            if cagrs:
                stats["avg_cagr"] = sum(cagrs) / len(cagrs)
            if drawdowns:
                stats["avg_max_drawdown"] = sum(drawdowns) / len(drawdowns)
                stats["worst_drawdown"] = min(drawdowns)
            if consistencies:
                stats["avg_consistency"] = sum(consistencies) / len(consistencies)

        # Entry type distribution
        entry_types: dict[str, int] = {}
        for s in all_strategies:
            entry_types[s.entry_type] = entry_types.get(s.entry_type, 0) + 1
        stats["entry_type_distribution"] = entry_types

        # Invalidation reasons (if available)
        invalidation_reasons = [
            s.determination_reason
            for s in invalidated
            if s.determination_reason
        ]
        if invalidation_reasons:
            stats["invalidation_reasons"] = invalidation_reasons

        return stats


# =============================================================================
# HELPERS
# =============================================================================


def _safe_float(value: Any, default: float | None = None) -> float | None:
    """Safely convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    """Safely convert a value to int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
