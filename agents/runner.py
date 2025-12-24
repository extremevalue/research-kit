"""
Persona Agent Runner

Invokes persona-based LLM agents with structured input/output.
Manages the multi-persona analysis flow:
1. Parallel: momentum-trader, risk-manager, quant-researcher
2. Sequential: contrarian (sees all others)
3. Final: report-synthesizer (integrates all)

Usage:
    from agents.runner import run_persona_analysis
    result = run_persona_analysis(component_id, validation_results)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from string import Template

from scripts.utils.logging_config import get_logger

logger = get_logger("persona-runner")

# Paths
PERSONAS_DIR = Path(__file__).parent / "personas"
PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass
class PersonaResponse:
    """Response from a persona agent."""
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
class PersonaAnalysisResult:
    """Complete multi-persona analysis result."""
    component_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    responses: Dict[str, PersonaResponse] = field(default_factory=dict)
    synthesis: Optional[Dict[str, Any]] = None
    consensus_points: List[str] = field(default_factory=list)
    disagreements: List[str] = field(default_factory=list)
    final_recommendation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "timestamp": self.timestamp,
            "responses": {k: v.to_dict() for k, v in self.responses.items()},
            "synthesis": self.synthesis,
            "consensus_points": self.consensus_points,
            "disagreements": self.disagreements,
            "final_recommendation": self.final_recommendation
        }


class PersonaRunner:
    """
    Runs persona-based analysis on validation results.

    Manages the multi-persona workflow with proper sequencing.
    """

    PERSONAS = [
        "momentum-trader",
        "risk-manager",
        "quant-researcher",
        "contrarian",
        "report-synthesizer"
    ]

    # Personas that can run in parallel (don't need others' output)
    PARALLEL_PERSONAS = ["momentum-trader", "risk-manager", "quant-researcher"]

    # Personas that need sequential execution
    SEQUENTIAL_PERSONAS = ["contrarian", "report-synthesizer"]

    def __init__(self, llm_client=None):
        """
        Initialize the persona runner.

        Args:
            llm_client: LLM client for generating responses
                        (None = offline mode, returns prompts only)
        """
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
        for prompt_file in PROMPTS_DIR.glob("*.md"):
            prompt_name = prompt_file.stem
            with open(prompt_file, 'r') as f:
                self.prompts[prompt_name] = f.read()

    def _render_prompt(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """Render a prompt template with context."""
        template = self.prompts.get(template_name, "")

        # Use simple string replacement for Jinja-like variables
        # In production, use actual Jinja2
        rendered = template
        for key, value in context.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, indent=2)
            rendered = rendered.replace(f"{{{{ {key} }}}}", str(value))

        return rendered

    def _build_system_prompt(self, persona: str) -> str:
        """Build the system prompt for a persona."""
        persona_def = self.personas.get(persona, "")
        return f"""You are an AI assistant embodying a specific persona for investment analysis.

{persona_def}

IMPORTANT:
- Stay in character as this persona throughout your response
- Provide your analysis in the JSON format specified in your persona document
- Be specific and quantitative where possible
- Your analysis should be actionable and clear
"""

    def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> str:
        """Call the LLM with the given prompts."""
        if self.llm_client is None:
            # Offline mode - return the prompt for inspection
            return json.dumps({
                "mode": "offline",
                "system_prompt_length": len(system_prompt),
                "user_prompt_length": len(user_prompt)
            })

        # In production, this would call Claude or another LLM
        try:
            response = self.llm_client.generate(
                system=system_prompt,
                user=user_prompt,
                max_tokens=4000
            )
            return response.content  # Extract string content from LLMResponse
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response."""
        # Try to extract JSON from response
        try:
            # Look for JSON block
            if "```json" in response:
                start = response.index("```json") + 7
                end = response.index("```", start)
                json_str = response[start:end].strip()
            elif "{" in response:
                # Find first { to last }
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]
            else:
                return None

            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse JSON from response: {e}")
            return None

    def run_persona(
        self,
        persona: str,
        context: Dict[str, Any],
        prompt_template: str = "interpret_results"
    ) -> PersonaResponse:
        """
        Run a single persona analysis.

        Args:
            persona: Persona name
            context: Context for the prompt template
            prompt_template: Which prompt template to use

        Returns:
            PersonaResponse with results
        """
        logger.info(f"Running persona: {persona}")

        response = PersonaResponse(persona=persona)

        try:
            # Build prompts
            system_prompt = self._build_system_prompt(persona)
            context["persona_name"] = persona
            user_prompt = self._render_prompt(prompt_template, context)

            # Call LLM
            raw_response = self._call_llm(system_prompt, user_prompt)
            response.raw_response = raw_response

            # Parse structured response
            structured = self._parse_response(raw_response)
            response.structured_response = structured

        except Exception as e:
            response.error = str(e)
            logger.error(f"Persona {persona} failed: {e}")

        return response

    def run_analysis(
        self,
        component_id: str,
        validation_results: Dict[str, Any],
        include_suggestions: bool = False
    ) -> PersonaAnalysisResult:
        """
        Run complete multi-persona analysis.

        Flow:
        1. Parallel: momentum-trader, risk-manager, quant-researcher
        2. Sequential: contrarian (receives all above)
        3. Final: report-synthesizer (receives all above)

        Args:
            component_id: Catalog entry ID
            validation_results: Complete validation results
            include_suggestions: Also run combination suggestions

        Returns:
            PersonaAnalysisResult with all responses and synthesis
        """
        logger.info(f"Starting multi-persona analysis for {component_id}")

        result = PersonaAnalysisResult(component_id=component_id)

        # Build base context
        base_context = {
            "component_id": component_id,
            **validation_results
        }

        # Phase 1: Parallel personas
        logger.info("Phase 1: Running parallel personas")
        for persona in self.PARALLEL_PERSONAS:
            response = self.run_persona(persona, base_context.copy())
            result.responses[persona] = response

        # Phase 2: Contrarian (sees all parallel outputs)
        logger.info("Phase 2: Running contrarian")
        contrarian_context = base_context.copy()
        contrarian_context["other_analyses"] = {
            p: result.responses[p].structured_response
            for p in self.PARALLEL_PERSONAS
            if result.responses.get(p) and result.responses[p].structured_response
        }

        # Build specific context for contrarian
        for persona in self.PARALLEL_PERSONAS:
            r = result.responses.get(persona)
            if r and r.structured_response:
                key = persona.replace("-", "_")
                contrarian_context[f"{key}_assessment"] = r.structured_response.get("overall_assessment", "N/A")
                contrarian_context[f"{key}_claims"] = r.structured_response.get("key_observations", [])
                contrarian_context[f"{key}_recommendation"] = r.structured_response.get("would_trade", "N/A")

        response = self.run_persona("contrarian", contrarian_context, "challenge_consensus")
        result.responses["contrarian"] = response

        # Phase 3: Report synthesizer (sees everything)
        logger.info("Phase 3: Running report synthesizer")
        synthesis_context = base_context.copy()
        synthesis_context["all_analyses"] = {
            p: result.responses[p].structured_response
            for p in result.responses
            if result.responses[p].structured_response
        }

        response = self.run_persona("report-synthesizer", synthesis_context)
        result.responses["report-synthesizer"] = response

        # Extract synthesis
        if response.structured_response:
            result.synthesis = response.structured_response
            result.consensus_points = response.structured_response.get("consensus_points", [])
            result.disagreements = response.structured_response.get("areas_of_disagreement", [])
            result.final_recommendation = response.structured_response.get(
                "final_determination", {}
            ).get("status")

        logger.info(f"Multi-persona analysis complete. Recommendation: {result.final_recommendation}")

        return result


def run_persona_analysis(
    component_id: str,
    validation_results: Dict[str, Any],
    llm_client=None
) -> PersonaAnalysisResult:
    """
    Convenience function to run multi-persona analysis.

    Args:
        component_id: Catalog entry ID
        validation_results: Complete validation results
        llm_client: Optional LLM client (None = offline mode)

    Returns:
        PersonaAnalysisResult
    """
    runner = PersonaRunner(llm_client)
    return runner.run_analysis(component_id, validation_results)


def save_analysis_result(result: PersonaAnalysisResult, output_dir: Path) -> Path:
    """Save persona analysis result to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "persona_analysis.json"

    with open(output_file, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)

    logger.info(f"Saved persona analysis to {output_file}")
    return output_file


if __name__ == "__main__":
    # Example usage (offline mode)
    example_results = {
        "component_name": "McClellan Oscillator Filter",
        "hypothesis": "McClellan Oscillator > 0 improves trend-following",
        "test_type": "is",
        "start_date": "2005-01-01",
        "end_date": "2019-12-31",
        "sharpe_ratio": 0.85,
        "alpha": 2.5,
        "cagr": 12.3,
        "max_drawdown": -18.5,
        "total_trades": 150,
        "win_rate": 58.0,
        "baseline_sharpe": 0.55,
        "sharpe_improvement": 0.30,
        "baseline_max_dd": -25.0,
        "drawdown_improvement": 6.5,
        "p_value": 0.008,
        "bonferroni_p": 0.008,
        "n_tests": 1,
        "is_significant": True,
        "effect_size": 0.30,
        "regime_results": [
            {"name": "Bull", "sharpe": 1.1, "returns": 15.2},
            {"name": "Bear", "sharpe": 0.3, "returns": -5.1},
            {"name": "Sideways", "sharpe": 0.6, "returns": 8.3}
        ],
        "sanity_flags": []
    }

    result = run_persona_analysis("IND-002", example_results)

    print(f"\nPersona Analysis Result")
    print(f"=" * 50)
    print(f"Component: {result.component_id}")
    print(f"Personas run: {list(result.responses.keys())}")
    print(f"Final recommendation: {result.final_recommendation}")

    print(f"\nResponses:")
    for persona, response in result.responses.items():
        status = "OK" if response.structured_response else "Parse Failed" if response.raw_response else "Error"
        print(f"  {persona}: {status}")
        if response.error:
            print(f"    Error: {response.error}")
