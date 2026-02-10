"""Synthesis Runner - Main orchestrator for LLM-powered synthesis.

Provides two modes:
- ideate(): 3 ideation personas -> quality gate -> 1-3 strategies
- synthesize(): 5 specialist personas -> synthesis-director -> recommendations
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from research_system.synthesis.context import (
    WorkspaceContext,
    WorkspaceContextAggregator,
)
from research_system.synthesis.output import save_idea_as_strategy, save_synthesis_report
from research_system.synthesis.prompts import PromptBuilder
from research_system.synthesis.quality_gate import (
    GeneratedIdea,
    QualityGate,
    QualityResult,
    parse_ideas_from_response,
)

if TYPE_CHECKING:
    from research_system.core.v4.workspace import Workspace
    from research_system.llm.client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class SynthesisRunResult:
    """Result from a synthesis or ideation run."""

    mode: str  # "ideate" or "synthesize"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    ideas_generated: int = 0
    ideas_accepted: int = 0
    ideas_rejected: int = 0
    accepted_ideas: list[GeneratedIdea] = field(default_factory=list)
    rejected_reasons: list[str] = field(default_factory=list)
    strategy_files: list[Path] = field(default_factory=list)
    report_file: Path | None = None
    persona_responses: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    offline: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "timestamp": self.timestamp,
            "ideas_generated": self.ideas_generated,
            "ideas_accepted": self.ideas_accepted,
            "ideas_rejected": self.ideas_rejected,
            "accepted_ideas": [i.to_dict() for i in self.accepted_ideas],
            "rejected_reasons": self.rejected_reasons,
            "strategy_files": [str(p) for p in self.strategy_files],
            "report_file": str(self.report_file) if self.report_file else None,
            "errors": self.errors,
            "offline": self.offline,
        }


class SynthesisRunner:
    """Orchestrates LLM-powered multi-persona synthesis.

    Usage:
        from research_system.synthesis import SynthesisRunner
        from research_system.llm.client import LLMClient

        runner = SynthesisRunner(workspace, LLMClient())
        result = runner.ideate()       # Generate 1-3 new strategies
        result = runner.synthesize()   # Full cross-strategy analysis
    """

    def __init__(self, workspace: Workspace, llm_client: LLMClient | None = None):
        self.workspace = workspace
        self.llm_client = llm_client
        self.prompt_builder = PromptBuilder()
        self.aggregator = WorkspaceContextAggregator(workspace)

    def ideate(self, max_ideas: int = 3) -> SynthesisRunResult:
        """Run LLM-powered ideation with quality gate.

        Uses 3 ideation personas (edge-hunter, macro-strategist, quant-archaeologist)
        to generate strategy ideas, then filters through a quality gate.

        Args:
            max_ideas: Maximum ideas to accept (hard cap at 3).

        Returns:
            SynthesisRunResult with accepted ideas saved as pending strategies.
        """
        result = SynthesisRunResult(mode="ideate")

        # Check LLM availability
        if self.llm_client is None or self.llm_client.is_offline:
            result.offline = True
            result.errors.append("No LLM backend available. Set ANTHROPIC_API_KEY or install Claude CLI.")
            logger.warning("Ideation skipped: no LLM backend available")
            return result

        # Aggregate workspace context
        logger.info("Aggregating workspace context...")
        context = self.aggregator.aggregate()

        # Build quality gate with available data
        gate = QualityGate(available_data=context.available_data)

        # Run each ideation persona
        all_ideas: list[GeneratedIdea] = []
        for persona in PromptBuilder.IDEATION_PERSONAS:
            logger.info(f"Running ideation persona: {persona}")
            ideas, response_text = self._run_ideation_persona(persona, context)
            result.persona_responses[persona] = response_text
            all_ideas.extend(ideas)
            logger.info(f"  {persona} generated {len(ideas)} ideas")

        # Apply quality gate
        logger.info(f"Filtering {len(all_ideas)} ideas through quality gate...")
        quality_result = gate.filter(all_ideas)

        result.ideas_generated = quality_result.total_generated
        result.ideas_accepted = len(quality_result.accepted)
        result.ideas_rejected = len(quality_result.rejected)
        result.accepted_ideas = quality_result.accepted
        result.rejected_reasons = [reason for _, reason in quality_result.rejected]

        # Save accepted ideas as pending strategies
        for idea in quality_result.accepted:
            try:
                filepath = save_idea_as_strategy(idea, self.workspace)
                result.strategy_files.append(filepath)
                logger.info(f"  Saved: {filepath.name}")
            except Exception as e:
                logger.error(f"  Failed to save idea '{idea.name}': {e}")
                result.errors.append(f"Failed to save '{idea.name}': {e}")

        # Save synthesis report
        try:
            report = save_synthesis_report(
                quality_result.accepted, result.persona_responses, self.workspace
            )
            result.report_file = report
        except Exception as e:
            logger.warning(f"Failed to save synthesis report: {e}")

        return result

    def synthesize(self) -> SynthesisRunResult:
        """Run full cross-strategy synthesis with specialist personas.

        Uses 5 specialist personas followed by a synthesis-director to analyze
        all validated strategies and produce ranked recommendations.

        Returns:
            SynthesisRunResult with synthesis analysis and any generated ideas.
        """
        result = SynthesisRunResult(mode="synthesize")

        # Check LLM availability
        if self.llm_client is None or self.llm_client.is_offline:
            result.offline = True
            result.errors.append("No LLM backend available. Set ANTHROPIC_API_KEY or install Claude CLI.")
            return result

        # Aggregate workspace context
        logger.info("Aggregating workspace context...")
        context = self.aggregator.aggregate()

        if not context.validated:
            result.errors.append("No validated strategies found. Run validation first.")
            return result

        # Phase 1: Run specialist personas in sequence
        for persona in PromptBuilder.SYNTHESIS_PERSONAS:
            logger.info(f"Running synthesis persona: {persona}")
            response = self._run_synthesis_persona(persona, context)
            result.persona_responses[persona] = response
            logger.info(f"  {persona} complete")

        # Phase 2: Run synthesis-director with all responses
        logger.info("Running synthesis-director...")
        director_response = self._run_director(context, result.persona_responses)
        result.persona_responses[PromptBuilder.SYNTHESIS_DIRECTOR] = director_response

        # Parse any ideas from director response
        ideas = parse_ideas_from_response(director_response, PromptBuilder.SYNTHESIS_DIRECTOR)
        if ideas:
            gate = QualityGate(available_data=context.available_data)
            quality_result = gate.filter(ideas)
            result.ideas_generated = quality_result.total_generated
            result.ideas_accepted = len(quality_result.accepted)
            result.accepted_ideas = quality_result.accepted

            for idea in quality_result.accepted:
                try:
                    filepath = save_idea_as_strategy(idea, self.workspace)
                    result.strategy_files.append(filepath)
                except Exception as e:
                    result.errors.append(f"Failed to save '{idea.name}': {e}")

        # Save report
        try:
            report = save_synthesis_report(
                result.accepted_ideas, result.persona_responses, self.workspace
            )
            result.report_file = report
        except Exception as e:
            logger.warning(f"Failed to save synthesis report: {e}")

        return result

    def _run_ideation_persona(
        self, persona: str, context: WorkspaceContext
    ) -> tuple[list[GeneratedIdea], str]:
        """Run a single ideation persona and parse its output."""
        system_prompt = self.prompt_builder.build_system_prompt(persona)
        user_prompt = self.prompt_builder.build_ideation_prompt(persona, context)

        try:
            response = self.llm_client.generate(
                system=system_prompt,
                user=user_prompt,
                max_tokens=4000,
            )
            ideas = parse_ideas_from_response(response.content, persona)
            return ideas, response.content
        except Exception as e:
            logger.error(f"Ideation persona {persona} failed: {e}")
            return [], f"Error: {e}"

    def _run_synthesis_persona(self, persona: str, context: WorkspaceContext) -> str:
        """Run a single synthesis persona and return raw response."""
        system_prompt = self.prompt_builder.build_system_prompt(persona)
        user_prompt = self.prompt_builder.build_synthesis_prompt(persona, context)

        try:
            response = self.llm_client.generate(
                system=system_prompt,
                user=user_prompt,
                max_tokens=4000,
            )
            return response.content
        except Exception as e:
            logger.error(f"Synthesis persona {persona} failed: {e}")
            return f"Error: {e}"

    def _run_director(
        self, context: WorkspaceContext, persona_responses: dict[str, str]
    ) -> str:
        """Run the synthesis-director with all persona responses."""
        system_prompt = self.prompt_builder.build_system_prompt(
            PromptBuilder.SYNTHESIS_DIRECTOR
        )
        user_prompt = self.prompt_builder.build_director_prompt(context, persona_responses)

        try:
            response = self.llm_client.generate(
                system=system_prompt,
                user=user_prompt,
                max_tokens=8000,
            )
            return response.content
        except Exception as e:
            logger.error(f"Synthesis director failed: {e}")
            return f"Error: {e}"
