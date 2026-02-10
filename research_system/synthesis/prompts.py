"""Persona-specific prompt construction with actual backtest metrics.

Builds system and user prompts for LLM synthesis by combining:
- Persona definitions (research_system/agents/personas/*.md)
- Prompt templates (research_system/agents/prompts/*.md)
- Actual workspace context (validated/invalidated strategies with metrics)

Different personas receive different metrics emphasis:

    portfolio-architect  -- Sharpe, drawdown, instrument overlap (correlation proxy)
    regime-strategist    -- Per-window walk-forward performance
    data-integrator      -- Data requirements vs available data sources
    creative-maverick    -- Invalidated strategies with failure reasons
    synthesis-director   -- Everything above, ranked
    edge-hunter          -- Entry types, trade frequency patterns
    macro-strategist     -- Cross-asset patterns, regime data from windows
    quant-archaeologist  -- Failed strategies with reasons, learnings
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from research_system.synthesis.context import StrategyWithMetrics, WorkspaceContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Directory constants (relative to project root)
# ---------------------------------------------------------------------------

PERSONAS_DIR = Path(__file__).parent.parent / "agents" / "personas"
PROMPTS_DIR = Path(__file__).parent.parent / "agents" / "prompts"

# ---------------------------------------------------------------------------
# JSON output schemas embedded in prompts
# ---------------------------------------------------------------------------

_IDEATION_OUTPUT_SCHEMA = """\
```json
{
  "persona": "<persona-name>",
  "ideas": [
    {
      "name": "Descriptive name for the strategy",
      "thesis": "Clear statement of why this edge exists and should persist",
      "hypothesis": "Specific, testable hypothesis",
      "entry_type": "technical|statistical|event|fundamental|compound",
      "data_requirements": ["data_source_1", "data_source_2"],
      "entry_logic": "Specific conditions for entering a position",
      "exit_logic": "Specific conditions for exiting",
      "risk_management": "Position sizing and risk controls",
      "expected_characteristics": {
        "holding_period": "days/weeks/months",
        "trade_frequency": "high/medium/low"
      },
      "confidence": "high|medium|low",
      "rationale": "Why this specific combination should work"
    }
  ]
}
```"""

_SYNTHESIS_OUTPUT_SCHEMA = """\
```json
{
  "persona": "<persona-name>",
  "recommendations": [
    {
      "name": "Descriptive recommendation name",
      "type": "combination|enhancement|new_strategy|portfolio_adjustment",
      "source_strategies": ["STRAT-xxx", "STRAT-yyy"],
      "rationale": "Why this recommendation",
      "expected_benefit": "Specific expected improvement",
      "implementation_notes": "How to implement",
      "priority": "high|medium|low"
    }
  ],
  "key_insights": ["Insight 1", "Insight 2"],
  "risks_and_concerns": ["Risk 1", "Risk 2"]
}
```"""

_DIRECTOR_OUTPUT_SCHEMA = """\
```json
{
  "executive_summary": "2-3 sentences summarizing key findings",
  "consensus_points": ["Points all personas agree on"],
  "areas_of_disagreement": [
    {
      "topic": "The disagreement",
      "positions": {"persona1": "view", "persona2": "view"},
      "resolution": "Recommended resolution"
    }
  ],
  "prioritized_opportunities": [
    {
      "rank": 1,
      "name": "Opportunity name",
      "type": "portfolio_combination|instrument_expansion|data_enhancement|new_strategy",
      "source_strategies": ["STRAT-xxx"],
      "expected_benefit": "High|Medium",
      "implementation_complexity": "Low|Medium|High",
      "next_steps": ["Step 1", "Step 2"],
      "rationale": "Why this is prioritized"
    }
  ],
  "recommended_catalog_entries": [
    {
      "type": "idea|strategy",
      "name": "Entry name",
      "summary": "Brief summary",
      "hypothesis": "Testable hypothesis",
      "parent_entries": ["STRAT-xxx"],
      "tags": ["synthesis-generated"],
      "data_requirements": ["data_source"]
    }
  ],
  "final_determination": {
    "recommendation": "proceed|investigate|pause",
    "confidence": "high|medium|low",
    "rationale": "Why"
  }
}
```"""


# ===========================================================================
# PromptBuilder
# ===========================================================================


class PromptBuilder:
    """Build persona-specific prompts with real workspace metrics.

    Loads persona markdown definitions and prompt templates once, then
    renders them with live context for each LLM call.
    """

    # Ideation personas -- generate new strategy ideas
    IDEATION_PERSONAS = ["edge-hunter", "macro-strategist", "quant-archaeologist"]

    # Synthesis personas -- analyse existing validated strategies
    SYNTHESIS_PERSONAS = [
        "portfolio-architect",
        "instrument-specialist",
        "data-integrator",
        "regime-strategist",
        "creative-maverick",
    ]

    # The director integrates all synthesis persona outputs
    SYNTHESIS_DIRECTOR = "synthesis-director"

    # -----------------------------------------------------------------
    # Init / loading
    # -----------------------------------------------------------------

    def __init__(self) -> None:
        self._personas: dict[str, str] = {}
        self._prompts: dict[str, str] = {}
        self._load_personas()
        self._load_prompts()

    def _load_personas(self) -> None:
        """Load persona markdown files from research_system/agents/personas/."""
        if not PERSONAS_DIR.is_dir():
            logger.warning("Personas directory not found: %s", PERSONAS_DIR)
            return
        for persona_file in PERSONAS_DIR.glob("*.md"):
            name = persona_file.stem
            self._personas[name] = persona_file.read_text()
            logger.debug("Loaded persona: %s", name)

    def _load_prompts(self) -> None:
        """Load prompt templates from research_system/agents/prompts/."""
        if not PROMPTS_DIR.is_dir():
            logger.warning("Prompts directory not found: %s", PROMPTS_DIR)
            return
        for prompt_file in PROMPTS_DIR.glob("*.md"):
            name = prompt_file.stem
            self._prompts[name] = prompt_file.read_text()
            logger.debug("Loaded prompt template: %s", name)

    # -----------------------------------------------------------------
    # System prompt (shared across ideation and synthesis)
    # -----------------------------------------------------------------

    def build_system_prompt(self, persona: str) -> str:
        """Build system prompt with persona definition and critical instructions."""
        persona_def = self._personas.get(persona, "")
        if not persona_def:
            logger.warning("No persona definition found for '%s'", persona)

        return f"""\
You are an AI assistant embodying a specific persona for strategy analysis.

{persona_def}

CRITICAL INSTRUCTIONS:
- DO NOT use any tools or try to read files - all data is in the user prompt
- DO NOT ask for more information - analyze based on what is provided
- Respond IMMEDIATELY with your analysis in the JSON format specified
- Stay in character as this persona throughout
- Be specific - reference strategy IDs, specific metrics, concrete actions"""

    # -----------------------------------------------------------------
    # Ideation prompts
    # -----------------------------------------------------------------

    def build_ideation_prompt(self, persona: str, context: WorkspaceContext) -> str:
        """Build user prompt for ideation with results-aware context.

        Fills the ``generate_ideas`` template with live strategy data and
        customises the emphasis for the given ideation persona.
        """
        template = self._prompts.get("generate_ideas", "")

        # -- Populate shared template variables --------------------------
        replacements: dict[str, str] = {
            "persona_name": persona,
            "custom_data_sources": self._format_available_data(context.available_data),
            "internal_data_sources": "None configured",
            "validated_entries": self._format_strategies(context.validated),
            "invalidated_entries": self._format_strategies(context.invalidated),
            "untested_entries": self._format_strategies(context.pending),
        }

        rendered = self._render_template(template, replacements)

        # -- Append persona-specific emphasis ----------------------------
        emphasis = self._ideation_emphasis(persona, context)
        if emphasis:
            rendered += "\n\n## Persona-Specific Context\n\n" + emphasis

        # -- Append output format if not already in template -------------
        if '"ideas"' not in rendered:
            rendered += (
                "\n\n## Required Output Format\n\n"
                "Return a JSON object with this exact structure:\n\n"
                + _IDEATION_OUTPUT_SCHEMA
            )

        return rendered

    def _ideation_emphasis(self, persona: str, context: WorkspaceContext) -> str:
        """Return persona-specific emphasis text for ideation prompts."""
        sections: list[str] = []

        if persona == "edge-hunter":
            sections.append("### Entry Type Distribution\n")
            entry_dist = context.summary_stats.get("entry_type_distribution", {})
            if entry_dist:
                for entry_type, count in sorted(entry_dist.items()):
                    sections.append(f"- {entry_type}: {count} strategies")
            else:
                sections.append("No entry type data available.")

            # Trade frequency info from validated strategies
            freq_lines = self._format_trade_frequency(context.validated)
            if freq_lines:
                sections.append("\n### Trade Frequency Patterns\n" + freq_lines)

        elif persona == "macro-strategist":
            sections.append("### Cross-Asset Coverage\n")
            all_instruments: set[str] = set()
            for s in context.validated + context.invalidated:
                all_instruments.update(s.instruments)
            if all_instruments:
                for inst in sorted(all_instruments):
                    sections.append(f"- {inst}")
            else:
                sections.append("No instrument data available.")

            # Regime data from walk-forward windows
            wf = self._format_per_window(context.validated)
            if wf and "No per-window" not in wf:
                sections.append("\n### Walk-Forward Regime Data\n" + wf)

        elif persona == "quant-archaeologist":
            sections.append("### Invalidated Strategies (Dig Into These)\n")
            for s in context.invalidated:
                reason = s.determination_reason or "Unknown"
                sections.append(f"- {s.id}: {s.name}")
                sections.append(f"  Reason: {reason}")
                sections.append(f"  Hypothesis: {s.hypothesis[:120]}")

            # Learnings
            if context.learnings:
                sections.append("\n### Learnings from Failures\n")
                for learning in context.learnings:
                    sections.append(
                        f"- [{learning.category}] {learning.strategy_id}: "
                        f"{learning.description[:120]}"
                    )

        return "\n".join(sections)

    # -----------------------------------------------------------------
    # Synthesis prompts
    # -----------------------------------------------------------------

    def build_synthesis_prompt(self, persona: str, context: WorkspaceContext) -> str:
        """Build user prompt for synthesis with persona-specific metrics.

        Uses ``synthesize_strategies`` template as base, then appends
        per-persona data sections so each persona gets the metrics most
        relevant to its role.
        """
        template = self._prompts.get("synthesize_strategies", "")

        # -- Shared template variables -----------------------------------
        replacements: dict[str, str] = {
            "persona_name": persona,
            "validated_strategies": self._format_strategies(context.validated),
            "validated_ideas": self._format_strategies(context.pending),
            "custom_data_sources": self._format_available_data(context.available_data),
        }

        rendered = self._render_template(template, replacements)

        # -- Persona-specific data sections ------------------------------
        extra = self._synthesis_emphasis(persona, context)
        if extra:
            rendered += "\n\n## Persona-Specific Data\n\n" + extra

        # -- Output schema -----------------------------------------------
        rendered += (
            "\n\n## Required Output Format\n\n"
            "Return a JSON object with this exact structure:\n\n"
            + _SYNTHESIS_OUTPUT_SCHEMA
        )

        return rendered

    def _synthesis_emphasis(self, persona: str, context: WorkspaceContext) -> str:
        """Return persona-specific data for synthesis prompts."""
        sections: list[str] = []

        if persona == "portfolio-architect":
            # Sharpe, drawdown, instrument overlap
            sections.append("### Strategy Metrics Summary\n")
            for s in context.validated:
                metrics_parts: list[str] = []
                if s.sharpe is not None:
                    metrics_parts.append(f"Sharpe={s.sharpe:.2f}")
                if s.max_drawdown is not None:
                    metrics_parts.append(f"MaxDD={s.max_drawdown * 100:.1f}%")
                if s.calmar is not None:
                    metrics_parts.append(f"Calmar={s.calmar:.2f}")
                instruments_str = ", ".join(s.instruments[:5]) or "N/A"
                metrics_str = ", ".join(metrics_parts) or "No metrics"
                sections.append(
                    f"- {s.id}: {s.name} [{metrics_str}]"
                    f"\n  Instruments: {instruments_str}"
                )

            # Instrument overlap matrix (proxy for correlation)
            sections.append("\n### Instrument Overlap (Correlation Proxy)\n")
            overlap_lines = self._format_instrument_overlap(context.validated)
            sections.append(overlap_lines)

        elif persona == "regime-strategist":
            # Per-window performance
            sections.append("### Per-Window Walk-Forward Performance\n")
            sections.append(self._format_per_window(context.validated))

        elif persona == "data-integrator":
            # Data usage vs availability
            sections.append("### Data Usage vs Availability\n")
            sections.append(
                self._format_data_usage(context.validated, context.available_data)
            )

        elif persona == "creative-maverick":
            # Invalidated strategies with failure reasons
            sections.append("### Invalidated Strategies (What Failed & Why)\n")
            if context.invalidated:
                for s in context.invalidated:
                    reason = s.determination_reason or "No specific reason recorded"
                    sections.append(f"- {s.id}: {s.name}")
                    sections.append(f"  Status: INVALIDATED")
                    sections.append(f"  Hypothesis: {s.hypothesis[:150]}")
                    sections.append(f"  Reason: {reason}")
                    if s.sharpe is not None:
                        sections.append(f"  Sharpe: {s.sharpe:.2f}")
                    sections.append("")
            else:
                sections.append("No invalidated strategies to analyze.")

            # Learnings
            if context.learnings:
                sections.append("\n### Learnings Archive\n")
                for learning in context.learnings:
                    sections.append(
                        f"- [{learning.category}] {learning.strategy_id}: "
                        f"{learning.description[:150]}"
                    )
                    if learning.action:
                        sections.append(f"  Action: {learning.action[:120]}")

        elif persona == "instrument-specialist":
            # Instrument details per strategy
            sections.append("### Current Instrument Usage\n")
            for s in context.validated:
                instruments_str = ", ".join(s.instruments) if s.instruments else "Not specified"
                sections.append(f"- {s.id}: {s.name}")
                sections.append(f"  Instruments: {instruments_str}")
                sections.append(f"  Entry type: {s.entry_type}")

        return "\n".join(sections)

    # -----------------------------------------------------------------
    # Director prompt
    # -----------------------------------------------------------------

    def build_director_prompt(
        self,
        context: WorkspaceContext,
        persona_responses: dict[str, str],
    ) -> str:
        """Build prompt for synthesis-director to integrate all persona outputs.

        The director sees all other persona responses and must synthesize,
        rank, and select 1-3 best recommendations.
        """
        sections: list[str] = [
            "# Synthesis Director: Integration Task\n",
            "You are the Synthesis Director. Below you have:",
            "1. The workspace context (strategies, metrics)",
            "2. Analysis from each specialist persona",
            "",
            "Your task: integrate all perspectives into prioritized, "
            "actionable recommendations. Select the 1-3 best opportunities.",
            "",
        ]

        # Workspace summary
        sections.append("## Workspace Summary\n")
        stats = context.summary_stats
        sections.append(f"- Validated strategies: {stats.get('validated_count', 0)}")
        sections.append(f"- Invalidated strategies: {stats.get('invalidated_count', 0)}")
        sections.append(f"- Pending strategies: {stats.get('pending_count', 0)}")
        if "avg_sharpe" in stats:
            sections.append(f"- Average Sharpe (validated): {stats['avg_sharpe']:.2f}")
        if "best_sharpe" in stats:
            sections.append(f"- Best Sharpe: {stats['best_sharpe']:.2f}")
        if "worst_drawdown" in stats:
            sections.append(f"- Worst drawdown: {stats['worst_drawdown'] * 100:.1f}%")
        sections.append("")

        # All validated strategies (brief)
        sections.append("## Validated Strategies\n")
        sections.append(self._format_strategies(context.validated))
        sections.append("")

        # Invalidated strategies (brief)
        sections.append("## Invalidated Strategies\n")
        sections.append(self._format_strategies(context.invalidated))
        sections.append("")

        # Each persona's response
        sections.append("## Specialist Analyses\n")
        for persona_name, response_text in persona_responses.items():
            sections.append(f"### {persona_name}\n")
            sections.append(response_text[:3000])  # Truncate very long responses
            sections.append("")

        # Director instructions
        sections.append("## Your Task\n")
        sections.append(
            "Integrate the above analyses. Focus on:\n"
            "1. What do the specialists agree on?\n"
            "2. Where do they disagree and how should we resolve it?\n"
            "3. What are the top 1-3 prioritized opportunities?\n"
            "4. What new catalog entries should we create?\n"
        )

        # Output format
        sections.append("## Required Output Format\n")
        sections.append(
            "Return a JSON object with this exact structure:\n\n"
            + _DIRECTOR_OUTPUT_SCHEMA
        )

        return "\n".join(sections)

    # ==================================================================
    # Formatting helpers
    # ==================================================================

    def _format_strategies(self, strategies: list[StrategyWithMetrics]) -> str:
        """Format strategies as text for prompts."""
        return "\n".join(s.to_summary_line() for s in strategies) or "None"

    def _format_per_window(self, strategies: list[StrategyWithMetrics]) -> str:
        """Format per-window data for regime-strategist."""
        lines: list[str] = []
        for s in strategies:
            if s.per_window:
                lines.append(f"\n### {s.id}: {s.name}")
                for i, w in enumerate(s.per_window):
                    period = w.get("period", f"Window {i + 1}")
                    sharpe = w.get("sharpe_ratio") or w.get("sharpe", "N/A")
                    dd = w.get("max_drawdown", "N/A")
                    if isinstance(sharpe, float):
                        sharpe = f"{sharpe:.2f}"
                    if isinstance(dd, float):
                        dd = f"{dd * 100:.1f}%"
                    lines.append(f"  {period}: Sharpe={sharpe}, MaxDD={dd}")
        return "\n".join(lines) or "No per-window data available"

    def _format_data_usage(
        self,
        strategies: list[StrategyWithMetrics],
        available: list[str],
    ) -> str:
        """Format data usage vs availability for data-integrator."""
        lines: list[str] = ["### Used by Strategies\n"]
        used: set[str] = set()
        for s in strategies:
            for inst in s.instruments:
                used.add(inst)
                lines.append(f"  - {s.id} uses {inst}")

        if not used:
            lines.append("  No instrument usage data recorded.")

        unused = [d for d in available if d not in used]
        if unused:
            lines.append("\n### Available but Unused\n")
            for d in unused[:20]:
                lines.append(f"  - {d}")
            if len(unused) > 20:
                lines.append(f"  ... and {len(unused) - 20} more")

        return "\n".join(lines)

    def _format_instrument_overlap(
        self,
        strategies: list[StrategyWithMetrics],
    ) -> str:
        """Build a simple instrument overlap matrix as text.

        When two strategies share instruments they are more likely to be
        correlated, so this acts as a rough correlation proxy.
        """
        if len(strategies) < 2:
            return "Insufficient strategies for overlap analysis."

        lines: list[str] = []
        for i, s1 in enumerate(strategies):
            set1 = set(s1.instruments)
            if not set1:
                continue
            for s2 in strategies[i + 1 :]:
                set2 = set(s2.instruments)
                if not set2:
                    continue
                overlap = set1 & set2
                if overlap:
                    pct = len(overlap) / min(len(set1), len(set2)) * 100
                    lines.append(
                        f"- {s1.id} <-> {s2.id}: {len(overlap)} shared "
                        f"instruments ({pct:.0f}% overlap) - {', '.join(sorted(overlap))}"
                    )
        return "\n".join(lines) or "No instrument overlap detected between strategies."

    def _format_trade_frequency(
        self,
        strategies: list[StrategyWithMetrics],
    ) -> str:
        """Format trade frequency information for edge-hunter."""
        lines: list[str] = []
        for s in strategies:
            if s.total_trades is not None:
                lines.append(
                    f"- {s.id}: {s.name} - {s.total_trades} total trades "
                    f"(entry type: {s.entry_type})"
                )
        return "\n".join(lines) or "No trade frequency data available."

    def _format_available_data(self, available: list[str]) -> str:
        """Format available data sources as a bullet list."""
        if not available:
            return "None configured"
        return "\n".join(f"- {d}" for d in available)

    # ------------------------------------------------------------------
    # Template rendering
    # ------------------------------------------------------------------

    @staticmethod
    def _render_template(template: str, replacements: dict[str, str]) -> str:
        """Render a prompt template with simple ``{{ key }}`` replacement.

        Uses the same pattern as existing ``research_system/agents/runner.py`` and
        ``research_system/agents/synthesis.py`` -- plain string replacement with
        Jinja-style double-brace placeholders.
        """
        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(f"{{{{ {key} }}}}", str(value))
        return rendered
