"""
Multi-Persona Ideation System

Generates novel strategy ideas using three distinct personas:
1. Edge Hunter - Finds micro-structure and timing edges
2. Macro Strategist - Cross-asset, regime-aware themes
3. Quant Archaeologist - Rehabilitates failed approaches

Usage:
    from research_system.agents.ideation import run_ideation
    result = run_ideation(workspace, llm_client, count=2)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from scripts.utils.logging_config import get_logger

logger = get_logger("ideation")

# Paths
PERSONAS_DIR = Path(__file__).parent / "personas"
PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass
class GeneratedIdea:
    """A single generated idea."""
    name: str
    thesis: str
    hypothesis: str
    data_requirements: List[str]
    entry_logic: str
    exit_logic: str
    risk_management: str
    related_entries: List[str]
    expected_characteristics: Dict[str, str]
    confidence: str
    rationale: str
    persona: str
    entry_type: str = "idea"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.entry_type,
            "thesis": self.thesis,
            "hypothesis": self.hypothesis,
            "data_requirements": self.data_requirements,
            "entry_logic": self.entry_logic,
            "exit_logic": self.exit_logic,
            "risk_management": self.risk_management,
            "related_entries": self.related_entries,
            "expected_characteristics": self.expected_characteristics,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "persona": self.persona,
        }


@dataclass
class IdeationResult:
    """Result from the ideation process."""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    ideas: List[GeneratedIdea] = field(default_factory=list)
    personas_run: List[str] = field(default_factory=list)
    data_gaps: List[str] = field(default_factory=list)
    research_suggestions: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "ideas": [idea.to_dict() for idea in self.ideas],
            "personas_run": self.personas_run,
            "data_gaps": self.data_gaps,
            "research_suggestions": self.research_suggestions,
            "errors": self.errors,
        }


class IdeationRunner:
    """
    Runs multi-persona ideation to generate novel strategy ideas.

    Each persona brings a different perspective:
    - edge-hunter: Timing and micro-structure edges
    - macro-strategist: Cross-asset regime plays
    - quant-archaeologist: Rehabilitation of failed approaches
    """

    PERSONAS = [
        "edge-hunter",
        "macro-strategist",
        "quant-archaeologist",
    ]

    def __init__(self, workspace, llm_client=None):
        """
        Initialize the ideation runner.

        Args:
            workspace: Workspace instance for accessing catalog and data registry
            llm_client: LLM client for generating ideas (None = offline mode)
        """
        self.workspace = workspace
        self.llm_client = llm_client
        self._load_personas()
        self._load_prompts()

    def _load_personas(self):
        """Load persona definitions."""
        self.personas = {}
        for persona in self.PERSONAS:
            persona_file = PERSONAS_DIR / f"{persona}.md"
            if persona_file.exists():
                with open(persona_file, 'r') as f:
                    self.personas[persona] = f.read()
            else:
                logger.warning(f"Persona file not found: {persona_file}")

    def _load_prompts(self):
        """Load prompt templates."""
        self.prompts = {}
        prompt_file = PROMPTS_DIR / "generate_ideas.md"
        if prompt_file.exists():
            with open(prompt_file, 'r') as f:
                self.prompts["generate_ideas"] = f.read()

    def _build_system_prompt(self, persona: str) -> str:
        """Build the system prompt for a persona."""
        persona_def = self.personas.get(persona, "")
        return f"""You are an AI assistant embodying a specific persona for strategy ideation.

{persona_def}

CRITICAL INSTRUCTIONS:
- DO NOT use any tools or try to read files - all data you need is in the prompt below
- DO NOT ask for more information - generate ideas based on what is provided
- Respond IMMEDIATELY with your ideas in the JSON format specified
- Stay in character as this persona throughout your response
- Generate concrete, actionable ideas with specific logic
- Reference specific data sources and catalog entries where relevant

Generate 1-2 high-quality strategy ideas matching your persona's perspective.
"""

    def _get_catalog_context(self) -> Dict[str, str]:
        """Build context about the catalog for ideation."""
        from research_system.core.catalog import Catalog

        catalog = Catalog(self.workspace.catalog_path)

        # Get validated entries
        validated = catalog.query().by_status("VALIDATED").execute()
        validated_entries = []
        for entry in validated[:10]:  # Limit to top 10
            validated_entries.append(
                f"- {entry['id']}: {entry['name']} - {entry.get('summary', 'N/A')[:100]}"
            )

        # Get invalidated entries
        invalidated = catalog.query().by_status("INVALIDATED").execute()
        invalidated_entries = []
        for entry in invalidated[:10]:
            invalidated_entries.append(
                f"- {entry['id']}: {entry['name']} - {entry.get('summary', 'N/A')[:100]}"
            )

        # Get untested ideas
        untested = catalog.query().by_status("UNTESTED").execute()
        untested_entries = []
        for entry in untested[:10]:
            untested_entries.append(
                f"- {entry['id']}: {entry['name']} - {entry.get('summary', 'N/A')[:100]}"
            )

        return {
            "validated_entries": "\n".join(validated_entries) if validated_entries else "None yet",
            "invalidated_entries": "\n".join(invalidated_entries) if invalidated_entries else "None yet",
            "untested_entries": "\n".join(untested_entries) if untested_entries else "None yet",
        }

    def _get_data_context(self) -> Dict[str, str]:
        """Build context about available data sources."""
        from research_system.core.data_registry import DataRegistry

        registry = DataRegistry(self.workspace.data_registry_path)

        # Get custom data sources (Object Store)
        custom_sources = []
        internal_sources = []

        for source in registry.list():
            best = source.best_source()
            if best.available:
                source_line = f"- {source.id}: {source.name}"
                if best.source_tier == "qc_object_store":
                    custom_sources.append(source_line)
                elif best.source_tier in ["internal_purchased", "internal_curated"]:
                    internal_sources.append(source_line)

        return {
            "custom_data_sources": "\n".join(custom_sources) if custom_sources else "None configured",
            "internal_data_sources": "\n".join(internal_sources) if internal_sources else "None configured",
        }

    def _render_prompt(self, persona: str) -> str:
        """Render the ideation prompt for a persona."""
        template = self.prompts.get("generate_ideas", "")

        # Get contexts
        catalog_context = self._get_catalog_context()
        data_context = self._get_data_context()

        # Build full context
        context = {
            "persona_name": persona,
            **catalog_context,
            **data_context,
        }

        # Simple template rendering
        rendered = template
        for key, value in context.items():
            rendered = rendered.replace(f"{{{{ {key} }}}}", str(value))

        return rendered

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call the LLM with the given prompts."""
        if self.llm_client is None:
            return json.dumps({
                "mode": "offline",
                "message": "LLM client not available"
            })

        try:
            response = self.llm_client.generate(
                system=system_prompt,
                user=user_prompt,
                max_tokens=4000
            )
            return response.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_ideas(self, response: str, persona: str) -> List[GeneratedIdea]:
        """Parse generated ideas from LLM response."""
        ideas = []

        try:
            # Extract JSON from response
            if "```json" in response:
                start = response.index("```json") + 7
                end = response.index("```", start)
                json_str = response[start:end].strip()
            elif "{" in response:
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]
            else:
                return ideas

            data = json.loads(json_str)

            # Extract ideas from response
            for idea_data in data.get("ideas", []):
                idea = GeneratedIdea(
                    name=idea_data.get("name", "Untitled"),
                    thesis=idea_data.get("thesis", ""),
                    hypothesis=idea_data.get("hypothesis", ""),
                    data_requirements=idea_data.get("data_requirements", []),
                    entry_logic=idea_data.get("entry_logic", ""),
                    exit_logic=idea_data.get("exit_logic", ""),
                    risk_management=idea_data.get("risk_management", ""),
                    related_entries=idea_data.get("related_entries", []),
                    expected_characteristics=idea_data.get("expected_characteristics", {}),
                    confidence=idea_data.get("confidence", "medium"),
                    rationale=idea_data.get("rationale", ""),
                    persona=persona,
                )
                ideas.append(idea)

            return ideas

        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse ideas from {persona}: {e}")
            return ideas

    def run_persona(self, persona: str, max_retries: int = 3) -> tuple[List[GeneratedIdea], Dict[str, Any]]:
        """
        Run ideation for a single persona with retry on JSON parse failures.

        Args:
            persona: The persona to run
            max_retries: Maximum number of retries on JSON parse failure

        Returns:
            Tuple of (list of ideas, metadata dict)
        """
        logger.info(f"Running ideation for persona: {persona}")

        system_prompt = self._build_system_prompt(persona)
        user_prompt = self._render_prompt(persona)

        last_error = None
        for attempt in range(max_retries):
            try:
                response = self._call_llm(system_prompt, user_prompt)
                ideas = self._parse_ideas(response, persona)

                # If we got ideas, return them
                if ideas:
                    # Extract metadata
                    meta = {}
                    try:
                        if "{" in response:
                            start = response.index("{")
                            end = response.rindex("}") + 1
                            data = json.loads(response[start:end])
                            meta = data.get("meta", {})
                    except:
                        pass

                    return ideas, meta

                # No ideas parsed - likely JSON error, retry
                if attempt < max_retries - 1:
                    logger.warning(f"No ideas parsed for {persona} (attempt {attempt + 1}/{max_retries}), retrying...")
                    continue

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"Ideation attempt {attempt + 1} failed for {persona}: {e}, retrying...")
                    continue
                break

        # All retries exhausted
        error_msg = str(last_error) if last_error else "JSON parsing failed after retries"
        logger.error(f"Ideation failed for {persona} after {max_retries} attempts: {error_msg}")
        return [], {"error": error_msg, "retries": max_retries}

    def run(self, count: int = 2) -> IdeationResult:
        """
        Run full ideation with all personas.

        Args:
            count: Target number of ideas per persona (1-2 recommended)

        Returns:
            IdeationResult with all generated ideas
        """
        logger.info(f"Starting ideation with {len(self.PERSONAS)} personas")

        result = IdeationResult()

        all_data_gaps = set()
        all_research_suggestions = set()

        for persona in self.PERSONAS:
            result.personas_run.append(persona)

            ideas, meta = self.run_persona(persona)

            if ideas:
                result.ideas.extend(ideas)
                logger.info(f"{persona} generated {len(ideas)} ideas")
            else:
                logger.warning(f"{persona} generated no valid ideas")
                if "error" in meta:
                    result.errors.append(f"{persona}: {meta['error']}")

            # Collect metadata
            if meta.get("data_gaps"):
                all_data_gaps.update(meta["data_gaps"])
            if meta.get("research_suggestions"):
                all_research_suggestions.update(meta["research_suggestions"])

        result.data_gaps = list(all_data_gaps)
        result.research_suggestions = list(all_research_suggestions)

        logger.info(f"Ideation complete: {len(result.ideas)} ideas from {len(result.personas_run)} personas")

        return result

    def add_ideas_to_catalog(self, result: IdeationResult) -> List[str]:
        """
        Add generated ideas to the catalog.

        Args:
            result: IdeationResult with ideas to add

        Returns:
            List of created entry IDs
        """
        from research_system.core.catalog import Catalog

        catalog = Catalog(self.workspace.catalog_path)
        created_ids = []

        for idea in result.ideas:
            try:
                # Build summary with thesis and key info
                summary_parts = [idea.thesis[:150] if idea.thesis else ""]
                if idea.entry_logic:
                    summary_parts.append(f"Entry: {idea.entry_logic[:50]}")
                summary = " | ".join(p for p in summary_parts if p)

                # Build hypothesis with full trading logic
                hypothesis_parts = [idea.hypothesis]
                if idea.entry_logic:
                    hypothesis_parts.append(f"Entry logic: {idea.entry_logic}")
                if idea.exit_logic:
                    hypothesis_parts.append(f"Exit logic: {idea.exit_logic}")
                if idea.risk_management:
                    hypothesis_parts.append(f"Risk: {idea.risk_management}")
                if idea.rationale:
                    hypothesis_parts.append(f"Rationale: {idea.rationale}")
                full_hypothesis = "\n\n".join(hypothesis_parts)

                # Build tags with persona and characteristics
                tags = [
                    f"persona:{idea.persona}",
                    f"confidence:{idea.confidence}",
                    "generated",
                ]
                if idea.expected_characteristics:
                    if idea.expected_characteristics.get("holding_period"):
                        tags.append(f"horizon:{idea.expected_characteristics['holding_period']}")
                    if idea.expected_characteristics.get("trade_frequency"):
                        tags.append(f"frequency:{idea.expected_characteristics['trade_frequency']}")

                # Create catalog entry using existing API
                entry = catalog.add(
                    entry_type="idea",
                    name=idea.name,
                    source_files=[],  # Generated, no source files
                    summary=summary[:200],
                    hypothesis=full_hypothesis,
                    tags=tags,
                    data_requirements=idea.data_requirements,
                    related_entries=idea.related_entries,
                    source_origin=f"ideation:{idea.persona}:{result.timestamp}",
                )

                created_ids.append(entry.id)
                logger.info(f"Created catalog entry: {entry.id}")

            except Exception as e:
                logger.error(f"Failed to add idea '{idea.name}' to catalog: {e}")

        return created_ids


def run_ideation(workspace, llm_client=None, count: int = 2) -> IdeationResult:
    """
    Convenience function to run multi-persona ideation.

    Args:
        workspace: Workspace instance
        llm_client: Optional LLM client (None = offline mode)
        count: Target ideas per persona

    Returns:
        IdeationResult with all generated ideas
    """
    runner = IdeationRunner(workspace, llm_client)
    return runner.run(count)


def save_ideation_result(result: IdeationResult, output_dir: Path) -> Path:
    """Save ideation result to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use timestamp in filename to keep history
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"ideation_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)

    logger.info(f"Saved ideation result to {output_file}")
    return output_file
