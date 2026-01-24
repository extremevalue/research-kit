"""
Idea Maturity Classification

Classifies ideas by their development maturity:
- RAW: Vague concept, needs full 10-step development
- PARTIAL: Some details specified, needs clarification
- FULL: Ready for validation (all key elements present)
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class MaturityLevel(Enum):
    """Idea maturity levels."""
    RAW = "raw"           # Vague idea, needs full development
    PARTIAL = "partial"   # Some details, needs clarification
    FULL = "full"         # Ready for validation


@dataclass
class IdeaMaturity:
    """Result of maturity classification."""
    level: MaturityLevel
    score: float  # 0.0 to 1.0

    # What's specified
    has_hypothesis: bool = False
    has_universe: bool = False
    has_signals: bool = False
    has_entry_rules: bool = False
    has_exit_rules: bool = False
    has_position_sizing: bool = False
    has_risk_management: bool = False

    # What's missing
    missing: List[str] = field(default_factory=list)

    # Development steps needed
    steps_needed: List[str] = field(default_factory=list)

    # Reasoning
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "score": self.score,
            "has_hypothesis": self.has_hypothesis,
            "has_universe": self.has_universe,
            "has_signals": self.has_signals,
            "has_entry_rules": self.has_entry_rules,
            "has_exit_rules": self.has_exit_rules,
            "has_position_sizing": self.has_position_sizing,
            "has_risk_management": self.has_risk_management,
            "missing": self.missing,
            "steps_needed": self.steps_needed,
            "reasoning": self.reasoning,
        }


# The 10 development steps
DEVELOPMENT_STEPS = [
    "hypothesis",           # 1. What are we trying to prove?
    "success_criteria",     # 2. How do we know it works?
    "universe",             # 3. What assets?
    "diversification",      # 4. Do they actually diversify?
    "structure",            # 5. Core+satellite, regime, or rotation?
    "signals",              # 6. Selection + timing signals
    "risk_management",      # 7. Position sizing, risk-off, limits
    "testing_protocol",     # 8. Walk-forward methodology
    "implementation",       # 9. Data sources, schedule
    "monitoring",           # 10. Decay detection, stop criteria
]


# Classification prompt for LLM
CLASSIFICATION_PROMPT = """Analyze this trading idea and assess its maturity for backtesting.

IDEA:
---
{idea_text}
---

Evaluate what's specified vs missing. A fully specified strategy needs:
1. HYPOTHESIS: Clear, testable statement of what should work and why
2. UNIVERSE: Specific assets or asset selection criteria (not just "stocks")
3. SIGNALS: Concrete entry/exit signals with parameters (not just "buy low sell high")
4. POSITION SIZING: How much to allocate per position
5. RISK MANAGEMENT: Stop losses, max drawdown limits, position limits

Rate each element:
- SPECIFIED: Clearly defined with actionable details
- PARTIAL: Mentioned but vague or incomplete
- MISSING: Not addressed at all

Respond in JSON:
{{
    "hypothesis": {{"status": "specified|partial|missing", "detail": "what's there or what's needed"}},
    "universe": {{"status": "specified|partial|missing", "detail": "..."}},
    "signals": {{"status": "specified|partial|missing", "detail": "..."}},
    "entry_rules": {{"status": "specified|partial|missing", "detail": "..."}},
    "exit_rules": {{"status": "specified|partial|missing", "detail": "..."}},
    "position_sizing": {{"status": "specified|partial|missing", "detail": "..."}},
    "risk_management": {{"status": "specified|partial|missing", "detail": "..."}},
    "maturity_level": "raw|partial|full",
    "reasoning": "Brief explanation of classification"
}}

Be strict: if parameters are vague (e.g., "use moving averages" without periods), mark as PARTIAL.
Respond with ONLY the JSON object."""


def classify_idea(
    idea_text: str,
    llm_client=None,
    existing_metadata: Optional[Dict[str, Any]] = None
) -> IdeaMaturity:
    """
    Classify an idea's maturity level.

    Args:
        idea_text: The raw idea text to classify
        llm_client: Optional LLM client for enhanced classification
        existing_metadata: Optional existing extraction metadata

    Returns:
        IdeaMaturity with classification results
    """
    # If we have an LLM client, use it for enhanced classification
    if llm_client and not llm_client.is_offline:
        return _classify_with_llm(idea_text, llm_client)

    # Fall back to rule-based classification
    return _classify_rule_based(idea_text, existing_metadata)


def _classify_with_llm(idea_text: str, llm_client) -> IdeaMaturity:
    """Use LLM for classification."""
    try:
        prompt = CLASSIFICATION_PROMPT.format(idea_text=idea_text)
        response = llm_client.generate(prompt, max_tokens=1000)

        # Parse JSON response - extract content from LLMResponse
        content = response.content if hasattr(response, 'content') else str(response)
        result = json.loads(content)

        # Map to IdeaMaturity
        level_map = {
            "raw": MaturityLevel.RAW,
            "partial": MaturityLevel.PARTIAL,
            "full": MaturityLevel.FULL,
        }
        level = level_map.get(result.get("maturity_level", "raw"), MaturityLevel.RAW)

        # Calculate score and gather missing items
        specified_count = 0
        missing = []
        elements = ["hypothesis", "universe", "signals", "entry_rules",
                   "exit_rules", "position_sizing", "risk_management"]

        for elem in elements:
            elem_data = result.get(elem, {})
            status = elem_data.get("status", "missing")
            if status == "specified":
                specified_count += 1
            elif status == "missing":
                missing.append(f"{elem}: {elem_data.get('detail', 'not specified')}")
            else:  # partial
                specified_count += 0.5
                missing.append(f"{elem}: {elem_data.get('detail', 'needs more detail')}")

        score = specified_count / len(elements)

        # Determine steps needed
        steps_needed = _determine_steps_needed(result)

        return IdeaMaturity(
            level=level,
            score=score,
            has_hypothesis=result.get("hypothesis", {}).get("status") == "specified",
            has_universe=result.get("universe", {}).get("status") == "specified",
            has_signals=result.get("signals", {}).get("status") == "specified",
            has_entry_rules=result.get("entry_rules", {}).get("status") == "specified",
            has_exit_rules=result.get("exit_rules", {}).get("status") == "specified",
            has_position_sizing=result.get("position_sizing", {}).get("status") == "specified",
            has_risk_management=result.get("risk_management", {}).get("status") == "specified",
            missing=missing,
            steps_needed=steps_needed,
            reasoning=result.get("reasoning", ""),
        )

    except Exception as e:
        logger.warning(f"LLM classification failed: {e}, falling back to rule-based")
        return _classify_rule_based(idea_text, None)


def _classify_rule_based(
    idea_text: str,
    existing_metadata: Optional[Dict[str, Any]]
) -> IdeaMaturity:
    """Simple rule-based classification."""
    text_lower = idea_text.lower()

    # Check for key elements
    has_hypothesis = any(kw in text_lower for kw in [
        "when", "if", "hypothesis", "believe", "expect", "should"
    ])

    has_universe = any(kw in text_lower for kw in [
        "spy", "qqq", "stock", "etf", "bond", "asset", "ticker",
        "equity", "futures", "crypto", "btc"
    ])

    has_signals = any(kw in text_lower for kw in [
        "sma", "ema", "rsi", "macd", "crossover", "momentum",
        "breakout", "mean reversion", "moving average"
    ])

    # Check for specific numbers (parameter specificity)
    import re
    has_numbers = bool(re.search(r'\d+-day|\d+ day|\d+%|period\s*=?\s*\d+', text_lower))

    has_entry_rules = any(kw in text_lower for kw in [
        "buy when", "enter when", "go long", "buy signal",
        "crosses above", "breaks out"
    ])

    has_exit_rules = any(kw in text_lower for kw in [
        "sell when", "exit when", "close position", "sell signal",
        "crosses below", "stop loss"
    ])

    has_position_sizing = any(kw in text_lower for kw in [
        "position size", "allocate", "% of portfolio", "weight",
        "equal weight", "risk parity"
    ])

    has_risk_management = any(kw in text_lower for kw in [
        "stop loss", "max drawdown", "risk limit", "position limit",
        "de-risk", "risk-off", "hedge"
    ])

    # Calculate score
    elements = [
        has_hypothesis, has_universe, has_signals and has_numbers,
        has_entry_rules, has_exit_rules, has_position_sizing, has_risk_management
    ]
    score = sum(elements) / len(elements)

    # Determine level
    if score >= 0.7:
        level = MaturityLevel.FULL
    elif score >= 0.3:
        level = MaturityLevel.PARTIAL
    else:
        level = MaturityLevel.RAW

    # Gather missing items
    missing = []
    if not has_hypothesis:
        missing.append("hypothesis: No clear testable statement")
    if not has_universe:
        missing.append("universe: No specific assets mentioned")
    if not has_signals or not has_numbers:
        missing.append("signals: No concrete signals with parameters")
    if not has_entry_rules:
        missing.append("entry_rules: No specific entry conditions")
    if not has_exit_rules:
        missing.append("exit_rules: No specific exit conditions")
    if not has_position_sizing:
        missing.append("position_sizing: No position sizing rules")
    if not has_risk_management:
        missing.append("risk_management: No risk management rules")

    # Determine steps needed
    steps_needed = []
    if not has_hypothesis:
        steps_needed.append("hypothesis")
    if not has_universe:
        steps_needed.extend(["universe", "diversification"])
    if not (has_signals and has_numbers and has_entry_rules and has_exit_rules):
        steps_needed.append("signals")
    if not has_risk_management or not has_position_sizing:
        steps_needed.append("risk_management")
    steps_needed.extend(["testing_protocol", "implementation", "monitoring"])

    return IdeaMaturity(
        level=level,
        score=score,
        has_hypothesis=has_hypothesis,
        has_universe=has_universe,
        has_signals=has_signals and has_numbers,
        has_entry_rules=has_entry_rules,
        has_exit_rules=has_exit_rules,
        has_position_sizing=has_position_sizing,
        has_risk_management=has_risk_management,
        missing=missing,
        steps_needed=list(dict.fromkeys(steps_needed)),  # dedupe preserving order
        reasoning=f"Rule-based classification: score={score:.2f}",
    )


def _determine_steps_needed(llm_result: Dict[str, Any]) -> List[str]:
    """Determine which development steps are needed based on LLM classification."""
    steps = []

    # Map classification results to development steps
    if llm_result.get("hypothesis", {}).get("status") != "specified":
        steps.append("hypothesis")
        steps.append("success_criteria")

    if llm_result.get("universe", {}).get("status") != "specified":
        steps.append("universe")
        steps.append("diversification")

    # Structure is always needed if universe is vague
    if llm_result.get("universe", {}).get("status") != "specified":
        steps.append("structure")

    if llm_result.get("signals", {}).get("status") != "specified":
        steps.append("signals")

    if (llm_result.get("position_sizing", {}).get("status") != "specified" or
        llm_result.get("risk_management", {}).get("status") != "specified"):
        steps.append("risk_management")

    # These are always needed for proper validation
    steps.extend(["testing_protocol", "implementation", "monitoring"])

    # Dedupe while preserving order
    return list(dict.fromkeys(steps))
