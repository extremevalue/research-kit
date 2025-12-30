"""
Multi-Persona Synthesis System

Analyzes validated strategies across multiple expert perspectives:
1. Portfolio Architect - Correlation, allocation, portfolio construction
2. Instrument Specialist - Options, futures, ETF opportunities
3. Data Integrator - Alternative data enhancement
4. Regime Strategist - Market regime analysis
5. Synthesis Director - Integrates all perspectives

Usage:
    from agents.synthesis import run_synthesis
    result = run_synthesis(workspace, llm_client)
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from scripts.utils.logging_config import get_logger

logger = get_logger("synthesis")

# Paths
PERSONAS_DIR = Path(__file__).parent / "personas"
PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass
class StrategyContext:
    """Context for a single strategy/idea."""
    id: str
    name: str
    type: str
    summary: str
    hypothesis: str
    tags: List[str]
    sharpe: Optional[float] = None
    cagr: Optional[float] = None
    max_drawdown: Optional[float] = None
    calmar: Optional[float] = None
    alpha: Optional[float] = None
    instruments: List[str] = field(default_factory=list)

    def to_summary_line(self) -> str:
        """Format as a concise summary line."""
        metrics = []
        if self.sharpe is not None:
            metrics.append(f"Sharpe={self.sharpe:.2f}")
        if self.cagr is not None:
            metrics.append(f"CAGR={self.cagr*100:.1f}%")
        if self.max_drawdown is not None:
            metrics.append(f"MaxDD={self.max_drawdown*100:.1f}%")
        if self.calmar is not None:
            metrics.append(f"Calmar={self.calmar:.2f}")

        metrics_str = ", ".join(metrics) if metrics else "No metrics"
        return f"- {self.id}: {self.name} [{metrics_str}]\n  {self.summary[:150]}"


@dataclass
class SynthesisContext:
    """Complete context for synthesis."""
    validated_strategies: List[StrategyContext] = field(default_factory=list)
    validated_ideas: List[StrategyContext] = field(default_factory=list)
    indicators: List[StrategyContext] = field(default_factory=list)
    custom_data_sources: List[str] = field(default_factory=list)
    summary_stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PersonaResponse:
    """Response from a synthesis persona."""
    persona: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    raw_response: str = ""
    structured_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "persona": self.persona,
            "timestamp": self.timestamp,
            "raw_response": self.raw_response,
            "structured_response": self.structured_response,
            "error": self.error
        }


@dataclass
class SynthesisResult:
    """Complete synthesis result."""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    context_summary: Dict[str, int] = field(default_factory=dict)
    responses: Dict[str, PersonaResponse] = field(default_factory=dict)
    synthesis: Optional[Dict[str, Any]] = None
    prioritized_opportunities: List[Dict[str, Any]] = field(default_factory=list)
    recommended_entries: List[Dict[str, Any]] = field(default_factory=list)
    consensus_points: List[str] = field(default_factory=list)
    disagreements: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "context_summary": self.context_summary,
            "responses": {k: v.to_dict() for k, v in self.responses.items()},
            "synthesis": self.synthesis,
            "prioritized_opportunities": self.prioritized_opportunities,
            "recommended_entries": self.recommended_entries,
            "consensus_points": self.consensus_points,
            "disagreements": self.disagreements,
            "errors": self.errors
        }


class ContextAggregator:
    """
    Aggregates validated strategy data for synthesis.

    Collects metrics from both Lean output and JSON result formats.
    """

    def __init__(self, workspace):
        """
        Initialize with workspace.

        Args:
            workspace: Workspace instance for accessing catalog and validations
        """
        self.workspace = workspace
        self.catalog_path = workspace.catalog_path
        self.validations_path = workspace.validations_path

    def _parse_lean_output(self, filepath: Path) -> Dict[str, Any]:
        """Parse metrics from last_lean_output.txt."""
        try:
            content = filepath.read_text()
            metrics = {}

            # Sharpe Ratio
            match = re.search(r'Sharpe Ratio\s*│\s*([-\d.]+)\s*│', content)
            if match:
                metrics['sharpe'] = float(match.group(1))

            # CAGR
            match = re.search(r'Compounding Annual Return\s*│\s*([-\d.]+)%', content)
            if match:
                metrics['cagr'] = float(match.group(1)) / 100

            # Max Drawdown
            match = re.search(r'Drawdown\s*│\s*([-\d.]+)%', content)
            if match:
                metrics['max_drawdown'] = float(match.group(1)) / 100

            # Alpha
            match = re.search(r'Alpha\s*│\s*([-\d.]+)', content)
            if match:
                metrics['alpha'] = float(match.group(1))

            # Sortino
            match = re.search(r'Sortino Ratio\s*│\s*([-\d.]+)', content)
            if match:
                metrics['sortino'] = float(match.group(1))

            return metrics
        except Exception as e:
            logger.warning(f"Failed to parse Lean output {filepath}: {e}")
            return {}

    def _parse_json_results(self, val_dir: Path) -> Dict[str, Any]:
        """Parse metrics from JSON result files."""
        metrics = {}

        # Try OOS results first (preferred), then IS
        for filename, prefix in [("oos_results.json", "oos_"), ("is_results.json", "is_")]:
            filepath = val_dir / filename
            if filepath.exists():
                try:
                    data = json.loads(filepath.read_text())
                    if data.get("success", False):
                        # Use OOS as primary if available
                        if prefix == "oos_" or 'sharpe' not in metrics:
                            for key in ['sharpe', 'cagr', 'max_drawdown', 'alpha']:
                                if key in data:
                                    metrics[key] = data[key]
                except Exception as e:
                    logger.warning(f"Failed to parse {filepath}: {e}")

        return metrics

    def _get_entry_metrics(self, entry_id: str) -> Dict[str, Any]:
        """Get metrics for an entry from validation results."""
        val_dir = self.validations_path / entry_id
        if not val_dir.exists():
            return {}

        metrics = {}

        # Try Lean output first
        lean_file = val_dir / "last_lean_output.txt"
        if lean_file.exists():
            metrics.update(self._parse_lean_output(lean_file))

        # Try JSON results (may override)
        json_metrics = self._parse_json_results(val_dir)
        if json_metrics:
            metrics.update(json_metrics)

        # Calculate Calmar if possible
        if metrics.get('cagr') and metrics.get('max_drawdown') and metrics['max_drawdown'] > 0:
            metrics['calmar'] = metrics['cagr'] / metrics['max_drawdown']

        return metrics

    def aggregate(
        self,
        min_sharpe: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        entry_types: Optional[List[str]] = None,
        top_n: Optional[int] = None
    ) -> SynthesisContext:
        """
        Aggregate validated entries with their metrics.

        Args:
            min_sharpe: Minimum Sharpe ratio filter
            max_drawdown: Maximum drawdown filter
            entry_types: Filter by entry types (strategy, idea, indicator)
            top_n: Limit to top N by Sharpe

        Returns:
            SynthesisContext with all aggregated data
        """
        from research_system.core.catalog import Catalog
        from research_system.core.data_registry import DataRegistry

        logger.info("Aggregating synthesis context...")

        context = SynthesisContext()

        # Load catalog
        catalog = Catalog(self.catalog_path)

        # Get validated entries
        validated = catalog.query().by_status("VALIDATED").execute()
        logger.info(f"Found {len(validated)} validated entries")

        all_entries = []

        for entry in validated:
            entry_id = entry['id']
            entry_type = entry.get('type', 'unknown')

            # Type filter
            if entry_types and entry_type not in entry_types:
                continue

            # Skip derived entries
            tags = entry.get('tags', [])
            if 'derived' in tags or 'expert-suggestion' in tags:
                continue

            # Get metrics
            metrics = self._get_entry_metrics(entry_id)

            # Skip if no Sharpe
            if 'sharpe' not in metrics:
                continue

            # Sharpe filter
            if min_sharpe and metrics['sharpe'] < min_sharpe:
                continue

            # Drawdown filter
            if max_drawdown and metrics.get('max_drawdown', 0) > max_drawdown:
                continue

            # Create context object
            strategy_ctx = StrategyContext(
                id=entry_id,
                name=entry.get('name', entry_id),
                type=entry_type,
                summary=entry.get('summary', ''),
                hypothesis=entry.get('hypothesis', ''),
                tags=tags,
                sharpe=metrics.get('sharpe'),
                cagr=metrics.get('cagr'),
                max_drawdown=metrics.get('max_drawdown'),
                calmar=metrics.get('calmar'),
                alpha=metrics.get('alpha'),
                instruments=entry.get('data', {}).get('instruments', [])
            )

            all_entries.append(strategy_ctx)

        # Sort by Sharpe
        all_entries.sort(key=lambda x: x.sharpe or 0, reverse=True)

        # Apply top_n limit
        if top_n:
            all_entries = all_entries[:top_n]

        # Categorize by type
        for entry in all_entries:
            if entry.type == 'strategy':
                context.validated_strategies.append(entry)
            elif entry.type == 'idea':
                context.validated_ideas.append(entry)
            elif entry.type == 'indicator':
                context.indicators.append(entry)

        # Get data sources
        try:
            registry = DataRegistry(self.workspace.data_registry_path)
            for source in registry.list():
                if source.is_available():
                    context.custom_data_sources.append(f"{source.id}: {source.name}")
        except Exception as e:
            logger.warning(f"Could not load data registry: {e}")

        # Summary stats
        context.summary_stats = {
            "total_validated": len(all_entries),
            "strategies": len(context.validated_strategies),
            "ideas": len(context.validated_ideas),
            "indicators": len(context.indicators),
            "avg_sharpe": sum(e.sharpe for e in all_entries if e.sharpe) / len(all_entries) if all_entries else 0,
            "custom_data_sources": len(context.custom_data_sources)
        }

        logger.info(f"Aggregated {context.summary_stats['total_validated']} entries")

        return context


class SynthesisRunner:
    """
    Runs multi-persona synthesis on validated strategies.

    Flow:
    1. Parallel: portfolio-architect, instrument-specialist, data-integrator, regime-strategist, creative-maverick
    2. Final: synthesis-director (receives all above)
    """

    PERSONAS = [
        "portfolio-architect",
        "instrument-specialist",
        "data-integrator",
        "regime-strategist",
        "creative-maverick",
        "synthesis-director"
    ]

    PARALLEL_PERSONAS = [
        "portfolio-architect",
        "instrument-specialist",
        "data-integrator",
        "regime-strategist",
        "creative-maverick"
    ]

    def __init__(self, workspace, llm_client=None):
        """
        Initialize the synthesis runner.

        Args:
            workspace: Workspace instance
            llm_client: LLM client for generating responses (None = offline)
        """
        self.workspace = workspace
        self.llm_client = llm_client
        self.aggregator = ContextAggregator(workspace)
        self._load_personas()
        self._load_prompts()

    def _load_personas(self):
        """Load persona definitions."""
        self.personas = {}
        for persona in self.PERSONAS:
            persona_file = PERSONAS_DIR / f"{persona}.md"
            if persona_file.exists():
                self.personas[persona] = persona_file.read_text()
            else:
                logger.warning(f"Persona file not found: {persona_file}")

    def _load_prompts(self):
        """Load prompt templates."""
        self.prompts = {}
        prompt_file = PROMPTS_DIR / "synthesize_strategies.md"
        if prompt_file.exists():
            self.prompts["synthesize_strategies"] = prompt_file.read_text()

    def _build_system_prompt(self, persona: str) -> str:
        """Build system prompt for a persona."""
        persona_def = self.personas.get(persona, "")
        return f"""You are an AI assistant embodying a specific persona for strategy synthesis.

{persona_def}

CRITICAL INSTRUCTIONS:
- DO NOT use any tools or try to read files - all data you need is in the prompt below
- DO NOT ask for more information - analyze what is provided
- Respond IMMEDIATELY with your analysis in the JSON format specified
- Stay in character as this persona throughout your response
- Be specific and reference strategy IDs directly
- Focus on practical, implementable opportunities
"""

    def _render_context_for_prompt(self, context: SynthesisContext) -> Dict[str, str]:
        """Render context into prompt-friendly format."""
        strategies_text = "\n".join(
            s.to_summary_line() for s in context.validated_strategies
        ) if context.validated_strategies else "None"

        ideas_text = "\n".join(
            i.to_summary_line() for i in context.validated_ideas
        ) if context.validated_ideas else "None"

        data_text = "\n".join(
            f"- {d}" for d in context.custom_data_sources
        ) if context.custom_data_sources else "None configured"

        return {
            "validated_strategies": strategies_text,
            "validated_ideas": ideas_text,
            "custom_data_sources": data_text
        }

    def _render_prompt(self, persona: str, context: SynthesisContext, extra_context: Dict[str, Any] = None) -> str:
        """Render the synthesis prompt."""
        template = self.prompts.get("synthesize_strategies", "")

        prompt_context = self._render_context_for_prompt(context)
        prompt_context["persona_name"] = persona

        if extra_context:
            prompt_context.update(extra_context)

        rendered = template
        for key, value in prompt_context.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, indent=2)
            rendered = rendered.replace(f"{{{{ {key} }}}}", str(value))

        return rendered

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call the LLM."""
        if self.llm_client is None:
            return json.dumps({
                "mode": "offline",
                "message": "LLM client not available",
                "system_prompt_length": len(system_prompt),
                "user_prompt_length": len(user_prompt)
            })

        try:
            response = self.llm_client.generate(
                system=system_prompt,
                user=user_prompt,
                max_tokens=8000
            )
            return response.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response."""
        try:
            if "```json" in response:
                start = response.index("```json") + 7
                end = response.index("```", start)
                json_str = response[start:end].strip()
            elif "{" in response:
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]
            else:
                return None

            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return None

    def run_persona(
        self,
        persona: str,
        context: SynthesisContext,
        extra_context: Dict[str, Any] = None
    ) -> PersonaResponse:
        """Run a single persona."""
        logger.info(f"Running synthesis persona: {persona}")

        response = PersonaResponse(persona=persona)

        try:
            system_prompt = self._build_system_prompt(persona)
            user_prompt = self._render_prompt(persona, context, extra_context)

            raw_response = self._call_llm(system_prompt, user_prompt)
            response.raw_response = raw_response
            response.structured_response = self._parse_response(raw_response)

        except Exception as e:
            response.error = str(e)
            logger.error(f"Persona {persona} failed: {e}")

        return response

    def run(
        self,
        min_sharpe: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        top_n: Optional[int] = 50
    ) -> SynthesisResult:
        """
        Run complete synthesis.

        Args:
            min_sharpe: Minimum Sharpe filter
            max_drawdown: Maximum drawdown filter
            top_n: Limit to top N entries by Sharpe

        Returns:
            SynthesisResult with all analysis
        """
        logger.info("Starting multi-persona synthesis")

        # Aggregate context
        context = self.aggregator.aggregate(
            min_sharpe=min_sharpe,
            max_drawdown=max_drawdown,
            top_n=top_n
        )

        result = SynthesisResult()
        result.context_summary = context.summary_stats

        if context.summary_stats['total_validated'] == 0:
            result.errors.append("No validated entries to synthesize")
            return result

        # Phase 1: Run parallel personas
        logger.info("Phase 1: Running parallel personas")
        for persona in self.PARALLEL_PERSONAS:
            response = self.run_persona(persona, context)
            result.responses[persona] = response
            if response.error:
                result.errors.append(f"{persona}: {response.error}")

        # Phase 2: Run synthesis director with all outputs
        logger.info("Phase 2: Running synthesis director")

        # Build extra context with all parallel outputs
        parallel_outputs = {}
        for persona in self.PARALLEL_PERSONAS:
            r = result.responses.get(persona)
            if r and r.structured_response:
                parallel_outputs[persona.replace("-", "_")] = r.structured_response

        extra_context = {
            "parallel_analyses": json.dumps(parallel_outputs, indent=2)
        }

        # Create enhanced prompt for director
        director_prompt = f"""
## Previous Analyses

The following specialist analyses have been completed:

{json.dumps(parallel_outputs, indent=2)}

## Your Task

As synthesis-director, integrate these perspectives into actionable recommendations.
Focus on:
1. What do the experts agree on?
2. Where do they disagree and how do we resolve it?
3. What are the top 3-5 prioritized opportunities?
4. What new catalog entries should we create?

Respond with your synthesis in the JSON format specified.
"""

        response = self.run_persona("synthesis-director", context, {"parallel_analyses": json.dumps(parallel_outputs, indent=2)})
        result.responses["synthesis-director"] = response

        # Extract synthesis outputs
        if response.structured_response:
            result.synthesis = response.structured_response
            result.consensus_points = response.structured_response.get("consensus_points", [])
            result.disagreements = response.structured_response.get("areas_of_disagreement", [])
            result.prioritized_opportunities = response.structured_response.get("prioritized_opportunities", [])
            result.recommended_entries = response.structured_response.get("recommended_catalog_entries", [])

        logger.info(f"Synthesis complete. Found {len(result.prioritized_opportunities)} opportunities")

        return result

    def create_catalog_entries(self, result: SynthesisResult) -> List[str]:
        """
        Create catalog entries from synthesis recommendations.

        Args:
            result: SynthesisResult with recommended entries

        Returns:
            List of created entry IDs
        """
        from research_system.core.catalog import Catalog

        if not result.recommended_entries:
            logger.info("No catalog entries to create")
            return []

        catalog = Catalog(self.workspace.catalog_path)
        created_ids = []

        for entry_data in result.recommended_entries:
            try:
                # Build tags
                tags = entry_data.get("tags", [])
                if "synthesis-generated" not in tags:
                    tags.append("synthesis-generated")

                # Add parent references
                parent_refs = entry_data.get("parent_entries", [])
                if parent_refs:
                    tags.append("derived")

                # Create entry
                entry = catalog.add(
                    entry_type=entry_data.get("type", "idea"),
                    name=entry_data.get("name", "Synthesis Idea"),
                    source_files=[],
                    summary=entry_data.get("summary", "")[:200],
                    hypothesis=entry_data.get("hypothesis", ""),
                    tags=tags,
                    data_requirements=entry_data.get("data_requirements", []),
                    related_entries=parent_refs,
                    source_origin=f"synthesis:{result.timestamp}"
                )

                created_ids.append(entry.id)
                logger.info(f"Created catalog entry: {entry.id}")

            except Exception as e:
                logger.error(f"Failed to create entry '{entry_data.get('name')}': {e}")

        return created_ids


def run_synthesis(
    workspace,
    llm_client=None,
    min_sharpe: float = None,
    max_drawdown: float = None,
    top_n: int = 50
) -> SynthesisResult:
    """
    Convenience function to run synthesis.

    Args:
        workspace: Workspace instance
        llm_client: Optional LLM client
        min_sharpe: Minimum Sharpe filter
        max_drawdown: Maximum drawdown filter
        top_n: Limit to top N entries

    Returns:
        SynthesisResult
    """
    runner = SynthesisRunner(workspace, llm_client)
    return runner.run(min_sharpe=min_sharpe, max_drawdown=max_drawdown, top_n=top_n)


def save_synthesis_result(result: SynthesisResult, output_dir: Path) -> Path:
    """Save synthesis result to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"synthesis_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)

    logger.info(f"Saved synthesis result to {output_file}")
    return output_file


def generate_synthesis_report(result: SynthesisResult, output_dir: Path) -> Path:
    """Generate a markdown report from synthesis results."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"synthesis_report_{timestamp}.md"

    lines = [
        "# Meta-Review Synthesis Report",
        f"Generated: {result.timestamp}",
        f"Entries Analyzed: {result.context_summary.get('total_validated', 0)}",
        "",
    ]

    # Executive Summary
    if result.synthesis and result.synthesis.get("executive_summary"):
        lines.extend([
            "## Executive Summary",
            result.synthesis["executive_summary"],
            ""
        ])

    # Consensus Points
    if result.consensus_points:
        lines.extend([
            "## Consensus Points",
            *[f"- {p}" for p in result.consensus_points],
            ""
        ])

    # Prioritized Opportunities
    if result.prioritized_opportunities:
        lines.extend([
            "## Prioritized Opportunities",
            ""
        ])
        for i, opp in enumerate(result.prioritized_opportunities, 1):
            lines.extend([
                f"### {i}. {opp.get('name', 'Opportunity')}",
                f"- **Type**: {opp.get('type', 'N/A')}",
                f"- **Expected Benefit**: {opp.get('expected_benefit', 'N/A')}",
                f"- **Complexity**: {opp.get('implementation_complexity', 'N/A')}",
                f"- **Source Strategies**: {', '.join(opp.get('source_strategies', []))}",
                "",
                opp.get('rationale', ''),
                ""
            ])

    # Recommended Entries
    if result.recommended_entries:
        lines.extend([
            "## Recommended New Catalog Entries",
            ""
        ])
        for entry in result.recommended_entries:
            lines.extend([
                f"### {entry.get('name', 'New Entry')}",
                f"- **Type**: {entry.get('type', 'idea')}",
                f"- **Summary**: {entry.get('summary', 'N/A')}",
                f"- **Parent Entries**: {', '.join(entry.get('parent_entries', []))}",
                ""
            ])

    # Disagreements
    if result.disagreements:
        lines.extend([
            "## Areas of Disagreement",
            ""
        ])
        for d in result.disagreements:
            if isinstance(d, dict):
                lines.extend([
                    f"### {d.get('topic', 'Topic')}",
                    f"**Resolution**: {d.get('resolution', 'N/A')}",
                    ""
                ])
            else:
                lines.append(f"- {d}")
        lines.append("")

    # Persona Insights
    lines.extend([
        "## Persona Insights",
        ""
    ])
    for persona, response in result.responses.items():
        status = "OK" if response.structured_response else "Parse Error" if response.raw_response else "Error"
        lines.append(f"### {persona}: {status}")
        if response.structured_response and response.structured_response.get("key_insights"):
            for insight in response.structured_response["key_insights"][:3]:
                lines.append(f"- {insight}")
        lines.append("")

    # Context Summary
    lines.extend([
        "## Appendix: Context Summary",
        "",
        f"- Strategies analyzed: {result.context_summary.get('strategies', 0)}",
        f"- Ideas analyzed: {result.context_summary.get('ideas', 0)}",
        f"- Indicators analyzed: {result.context_summary.get('indicators', 0)}",
        f"- Average Sharpe: {result.context_summary.get('avg_sharpe', 0):.2f}",
        f"- Custom data sources: {result.context_summary.get('custom_data_sources', 0)}",
        ""
    ])

    output_file.write_text("\n".join(lines))
    logger.info(f"Saved synthesis report to {output_file}")
    return output_file
