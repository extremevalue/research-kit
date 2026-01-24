"""
Development Workflow Engine

Manages the 10-step development process for turning vague ideas
into fully specified, testable strategies.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DevelopmentStep(Enum):
    """The 10 development steps."""
    HYPOTHESIS = "hypothesis"
    SUCCESS_CRITERIA = "success_criteria"
    UNIVERSE = "universe"
    DIVERSIFICATION = "diversification"
    STRUCTURE = "structure"
    SIGNALS = "signals"
    RISK_MANAGEMENT = "risk_management"
    TESTING_PROTOCOL = "testing_protocol"
    IMPLEMENTATION = "implementation"
    MONITORING = "monitoring"


# Step order for enforcement
STEP_ORDER = [
    DevelopmentStep.HYPOTHESIS,
    DevelopmentStep.SUCCESS_CRITERIA,
    DevelopmentStep.UNIVERSE,
    DevelopmentStep.DIVERSIFICATION,
    DevelopmentStep.STRUCTURE,
    DevelopmentStep.SIGNALS,
    DevelopmentStep.RISK_MANAGEMENT,
    DevelopmentStep.TESTING_PROTOCOL,
    DevelopmentStep.IMPLEMENTATION,
    DevelopmentStep.MONITORING,
]


# Step definitions with prompts and required outputs
STEP_DEFINITIONS = {
    DevelopmentStep.HYPOTHESIS: {
        "name": "Hypothesis",
        "question": "What are we trying to prove?",
        "description": "State your hypothesis in one clear, testable sentence.",
        "required_outputs": ["hypothesis_statement"],
        "guidance": """A good hypothesis:
- Is specific and measurable
- Explains WHY it should work (mechanism)
- Can be proven false
Example: "Golden cross (50-day SMA > 200-day SMA) captures momentum trends
because institutional investors use these signals, creating self-fulfilling price moves." """,
    },
    DevelopmentStep.SUCCESS_CRITERIA: {
        "name": "Success Criteria",
        "question": "How do we know it works?",
        "description": "Define your benchmark, objectives, and constraints.",
        "required_outputs": ["benchmark", "primary_objective", "constraints"],
        "guidance": """Define:
- Benchmark: What are you trying to beat? (SPY, 60/40, cash)
- Primary objective: Return? Risk-adjusted return? Lower drawdowns?
- Constraints: Max turnover, tax sensitivity, trading frequency""",
    },
    DevelopmentStep.UNIVERSE: {
        "name": "Universe",
        "question": "What assets will you trade?",
        "description": "Select 3-5 assets with economic rationale (not just tickers).",
        "required_outputs": ["assets", "economic_rationale"],
        "guidance": """Pick assets based on economic DRIVERS, not just tickers:
- Growth driver: SPY, QQQ
- Defensive driver: TLT, GLD
- Diversifier: International, alternatives

Explain WHY each asset is included and what role it plays.""",
    },
    DevelopmentStep.DIVERSIFICATION: {
        "name": "Diversification Check",
        "question": "Do these assets actually diversify?",
        "description": "Validate diversification with data, not assumptions.",
        "required_outputs": ["correlation_analysis", "stress_behavior"],
        "guidance": """Check:
- Rolling correlations (do they stay low?)
- Behavior in equity drawdowns (2008, 2020, 2022)
- Tail correlations (do they spike in crises?)

If "diversifiers" correlate in stress, reconsider the universe.""",
    },
    DevelopmentStep.STRUCTURE: {
        "name": "Structure",
        "question": "What's the portfolio skeleton?",
        "description": "Choose ONE structure: core+satellite, regime switch, or rotation.",
        "required_outputs": ["structure_type", "structure_description"],
        "guidance": """Pick ONE:
1. Core+Satellite: Fixed core allocation + tactical satellites
2. Regime Switch: Different allocations based on market regime
3. Rotation: Fully rotate between assets based on signals

Don't mix structures - pick one and commit.""",
    },
    DevelopmentStep.SIGNALS: {
        "name": "Signals",
        "question": "What triggers trades?",
        "description": "Define selection signal (which asset) and timing signal (when).",
        "required_outputs": ["selection_signal", "timing_signal", "signal_rationale"],
        "guidance": """Define:
- Selection signal: Which asset to favor (momentum, value, etc.)
- Timing signal: When to enter/exit (crossover, breakout, etc.)

For each signal:
- Specific parameters (e.g., 50-day, not "short-term")
- Economic rationale (WHY should this work?)
- Keep it simple (fewer signals = more robust)""",
    },
    DevelopmentStep.RISK_MANAGEMENT: {
        "name": "Risk Management",
        "question": "What can kill us and how do we prevent it?",
        "description": "Define position sizing, risk-off conditions, and limits.",
        "required_outputs": ["position_sizing", "risk_off_rules", "limits"],
        "guidance": """Define:
- Position sizing: Equal weight? Risk parity? Kelly?
- Risk-off conditions: When do we go to cash/defensive?
- Limits: Max position, max drawdown, max correlation

Describe expected behavior in 2008/2020 scenarios.""",
    },
    DevelopmentStep.TESTING_PROTOCOL: {
        "name": "Testing Protocol",
        "question": "How do we avoid fooling ourselves?",
        "description": "Define walk-forward methodology and sensitivity tests.",
        "required_outputs": ["validation_method", "sensitivity_tests", "benchmarks"],
        "guidance": """Standard protocol (already in research-kit):
- Walk-forward: 12 windows (5yr train / 1yr test)
- Gates: Median return >0%, consistency ≥60%, Sharpe >0.3, MaxDD <30%

Also consider:
- Parameter sensitivity: Does it break with small changes?
- Regime sensitivity: Does it work in bull AND bear markets?""",
    },
    DevelopmentStep.IMPLEMENTATION: {
        "name": "Implementation",
        "question": "How do we actually run this?",
        "description": "Specify data sources, rebalancing schedule, execution details.",
        "required_outputs": ["data_sources", "rebalance_schedule", "execution_notes"],
        "guidance": """Specify:
- Data sources: What data do we need? Is it available?
- Rebalancing: Daily? Weekly? Monthly? On signal?
- Execution: Market orders? Limits? Time of day?

Handle edge cases: missing data, ETF inception dates, splits.""",
    },
    DevelopmentStep.MONITORING: {
        "name": "Monitoring",
        "question": "How do we know when it stops working?",
        "description": "Define metrics to track and stop criteria.",
        "required_outputs": ["monitoring_metrics", "decay_detection", "stop_criteria"],
        "guidance": """Define:
- What metrics to track continuously
- How to detect regime change or strategy decay
- When to stop trading it (hard rules, not judgment calls)

Example stop criteria:
- Rolling Sharpe drops below 0 for 6 months
- Drawdown exceeds 1.5x historical max""",
    },
}


@dataclass
class StepOutput:
    """Output from completing a development step."""
    step: DevelopmentStep
    completed_at: str
    outputs: Dict[str, Any]
    notes: str = ""


@dataclass
class DevelopmentState:
    """Persistent state of idea development."""
    entry_id: str
    original_idea: str
    created_at: str
    updated_at: str

    # Progress tracking
    current_step: DevelopmentStep = DevelopmentStep.HYPOTHESIS
    completed_steps: List[str] = field(default_factory=list)

    # Step outputs
    step_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Final output
    is_complete: bool = False
    generated_strategy_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "original_idea": self.original_idea,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_step": self.current_step.value,
            "completed_steps": self.completed_steps,
            "step_outputs": self.step_outputs,
            "is_complete": self.is_complete,
            "generated_strategy_id": self.generated_strategy_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DevelopmentState":
        return cls(
            entry_id=data["entry_id"],
            original_idea=data["original_idea"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            current_step=DevelopmentStep(data["current_step"]),
            completed_steps=data.get("completed_steps", []),
            step_outputs=data.get("step_outputs", {}),
            is_complete=data.get("is_complete", False),
            generated_strategy_id=data.get("generated_strategy_id"),
        )


class DevelopmentWorkflow:
    """
    Manages the development workflow for an idea.

    Enforces step ordering, persists state, and guides through the 10-step process.
    """

    def __init__(self, workspace_path: Path, llm_client=None):
        """
        Initialize workflow manager.

        Args:
            workspace_path: Path to workspace root
            llm_client: Optional LLM client for generating suggestions
        """
        self.workspace_path = workspace_path
        self.llm_client = llm_client
        self.develop_path = workspace_path / "develop"
        self.develop_path.mkdir(exist_ok=True)

    def start(self, entry_id: str, original_idea: str) -> DevelopmentState:
        """
        Start development for a new idea.

        Args:
            entry_id: The catalog entry ID (e.g., IDEA-001)
            original_idea: The original idea text

        Returns:
            New DevelopmentState
        """
        now = datetime.utcnow().isoformat() + "Z"
        state = DevelopmentState(
            entry_id=entry_id,
            original_idea=original_idea,
            created_at=now,
            updated_at=now,
        )
        self._save_state(state)
        logger.info(f"Started development for {entry_id}")
        return state

    def load(self, entry_id: str) -> Optional[DevelopmentState]:
        """Load existing development state."""
        state_file = self.develop_path / f"{entry_id}_development.json"
        if not state_file.exists():
            return None

        with open(state_file) as f:
            data = json.load(f)
        return DevelopmentState.from_dict(data)

    def get_current_step(self, state: DevelopmentState) -> DevelopmentStep:
        """Get the current step to work on."""
        return state.current_step

    def get_step_info(self, step: DevelopmentStep) -> Dict[str, Any]:
        """Get information about a step."""
        return STEP_DEFINITIONS[step].copy()

    def can_advance(self, state: DevelopmentState, to_step: DevelopmentStep) -> bool:
        """
        Check if we can advance to a given step.

        Enforces that earlier steps must be completed first.
        """
        target_idx = STEP_ORDER.index(to_step)

        # All prior steps must be completed
        for i in range(target_idx):
            if STEP_ORDER[i].value not in state.completed_steps:
                return False

        return True

    def complete_step(
        self,
        state: DevelopmentState,
        step: DevelopmentStep,
        outputs: Dict[str, Any],
        notes: str = ""
    ) -> DevelopmentState:
        """
        Complete a development step.

        Args:
            state: Current development state
            step: The step being completed
            outputs: The outputs from this step
            notes: Optional notes

        Returns:
            Updated DevelopmentState
        """
        # Verify this is the current step
        if step != state.current_step:
            raise ValueError(f"Cannot complete {step.value}, current step is {state.current_step.value}")

        # Verify required outputs
        required = STEP_DEFINITIONS[step]["required_outputs"]
        missing = [r for r in required if r not in outputs]
        if missing:
            raise ValueError(f"Missing required outputs: {missing}")

        # Update state
        state.completed_steps.append(step.value)
        state.step_outputs[step.value] = {
            "completed_at": datetime.utcnow().isoformat() + "Z",
            "outputs": outputs,
            "notes": notes,
        }

        # Advance to next step
        current_idx = STEP_ORDER.index(step)
        if current_idx < len(STEP_ORDER) - 1:
            state.current_step = STEP_ORDER[current_idx + 1]
        else:
            state.is_complete = True

        state.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save_state(state)

        logger.info(f"Completed step {step.value} for {state.entry_id}")
        return state

    def go_back(self, state: DevelopmentState, to_step: DevelopmentStep) -> DevelopmentState:
        """
        Go back to a previous step to revise.

        This keeps earlier outputs but marks subsequent steps as incomplete.
        """
        target_idx = STEP_ORDER.index(to_step)
        current_idx = STEP_ORDER.index(state.current_step)

        if target_idx >= current_idx:
            raise ValueError(f"Can only go back to earlier steps")

        # Mark subsequent steps as incomplete
        for i in range(target_idx, len(STEP_ORDER)):
            step_name = STEP_ORDER[i].value
            if step_name in state.completed_steps:
                state.completed_steps.remove(step_name)

        state.current_step = to_step
        state.is_complete = False
        state.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save_state(state)

        logger.info(f"Went back to step {to_step.value} for {state.entry_id}")
        return state

    def generate_strategy_spec(self, state: DevelopmentState) -> Dict[str, Any]:
        """
        Generate a strategy specification from completed development.

        This is the output that feeds into the R1 validation pipeline.
        """
        if not state.is_complete:
            raise ValueError("Development must be complete to generate strategy spec")

        # Compile all outputs into a strategy specification
        outputs = state.step_outputs

        spec = {
            "name": self._generate_strategy_name(state),
            "type": "strategy",
            "original_idea": state.original_idea,
            "development_ref": f"develop/{state.entry_id}_development.json",

            # From Step 1: Hypothesis
            "hypothesis": outputs.get("hypothesis", {}).get("outputs", {}).get("hypothesis_statement", ""),

            # From Step 2: Success Criteria
            "benchmark": outputs.get("success_criteria", {}).get("outputs", {}).get("benchmark", ""),
            "primary_objective": outputs.get("success_criteria", {}).get("outputs", {}).get("primary_objective", ""),

            # From Step 3: Universe
            "universe": outputs.get("universe", {}).get("outputs", {}).get("assets", []),

            # From Step 5: Structure
            "structure": outputs.get("structure", {}).get("outputs", {}).get("structure_type", ""),

            # From Step 6: Signals
            "entry_signal": outputs.get("signals", {}).get("outputs", {}).get("selection_signal", ""),
            "exit_signal": outputs.get("signals", {}).get("outputs", {}).get("timing_signal", ""),

            # From Step 7: Risk Management
            "position_sizing": outputs.get("risk_management", {}).get("outputs", {}).get("position_sizing", ""),
            "risk_off_rules": outputs.get("risk_management", {}).get("outputs", {}).get("risk_off_rules", ""),

            # Tags derived from content
            "tags": self._derive_tags(state),
        }

        return spec

    def _save_state(self, state: DevelopmentState):
        """Save state to disk."""
        state_file = self.develop_path / f"{state.entry_id}_development.json"
        with open(state_file, "w") as f:
            json.dump(state.to_dict(), f, indent=2)

    def _generate_strategy_name(self, state: DevelopmentState) -> str:
        """Generate a name for the developed strategy."""
        structure = state.step_outputs.get("structure", {}).get("outputs", {}).get("structure_type", "Strategy")
        universe = state.step_outputs.get("universe", {}).get("outputs", {}).get("assets", [])

        if universe:
            assets_str = "/".join(universe[:3])
            return f"{structure.title()} {assets_str}"

        return f"Developed {structure.title()} Strategy"

    def _derive_tags(self, state: DevelopmentState) -> List[str]:
        """Derive tags from development outputs."""
        tags = []

        # From structure
        structure = state.step_outputs.get("structure", {}).get("outputs", {}).get("structure_type", "")
        if structure:
            tags.append(structure.lower().replace(" ", "_"))

        # From signals
        signals = state.step_outputs.get("signals", {}).get("outputs", {})
        signal_text = json.dumps(signals).lower()
        if "momentum" in signal_text:
            tags.append("momentum")
        if "mean reversion" in signal_text or "rsi" in signal_text:
            tags.append("mean_reversion")
        if "trend" in signal_text or "sma" in signal_text:
            tags.append("trend_following")

        return list(set(tags))

    def create_strategy_entry(self, state: DevelopmentState, catalog) -> str:
        """
        Create a new strategy catalog entry from completed development.

        Args:
            state: Completed development state
            catalog: Catalog instance

        Returns:
            New strategy entry ID
        """
        if not state.is_complete:
            raise ValueError("Development must be complete to create strategy entry")

        spec = self.generate_strategy_spec(state)

        # Build comprehensive hypothesis from development
        hypothesis_parts = []

        # From step 1
        hyp = state.step_outputs.get("hypothesis", {}).get("outputs", {}).get("hypothesis_statement", "")
        if hyp:
            hypothesis_parts.append(hyp)

        # From step 6 - signals
        signals = state.step_outputs.get("signals", {}).get("outputs", {})
        if signals.get("selection_signal"):
            hypothesis_parts.append(f"Selection: {signals['selection_signal']}")
        if signals.get("timing_signal"):
            hypothesis_parts.append(f"Timing: {signals['timing_signal']}")

        # From step 7 - risk management
        risk = state.step_outputs.get("risk_management", {}).get("outputs", {})
        if risk.get("position_sizing"):
            hypothesis_parts.append(f"Position sizing: {risk['position_sizing']}")
        if risk.get("risk_off_rules"):
            hypothesis_parts.append(f"Risk-off: {risk['risk_off_rules']}")

        full_hypothesis = " | ".join(hypothesis_parts)

        # Create entry
        entry = catalog.add(
            entry_type="strategy",
            name=spec["name"],
            source_files=[spec["development_ref"]],
            summary=spec.get("primary_objective", state.original_idea[:200]),
            hypothesis=full_hypothesis,
            tags=spec.get("tags", []) + ["developed", f"from_{state.entry_id}"]
        )

        # Link back to development state
        state.generated_strategy_id = entry.id
        self._save_state(state)

        logger.info(f"Created strategy {entry.id} from development {state.entry_id}")
        return entry.id
