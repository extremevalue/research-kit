"""Comprehensive tests for the LLM synthesis module.

Tests cover:
- WorkspaceContextAggregator: reading V4 workspace directories
- QualityGate / GeneratedIdea / parse_ideas_from_response: filtering ideas
- PromptBuilder: building persona-specific prompts
- save_idea_as_strategy / save_synthesis_report: YAML output
- SynthesisRunner / SynthesisRunResult: main orchestrator
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from research_system.core.v4.workspace import Workspace
from research_system.llm.client import Backend, LLMResponse
from research_system.synthesis.context import (
    Learning,
    StrategyWithMetrics,
    WorkspaceContext,
    WorkspaceContextAggregator,
)
from research_system.synthesis.output import save_idea_as_strategy, save_synthesis_report
from research_system.synthesis.prompts import PromptBuilder
from research_system.synthesis.quality_gate import (
    MAX_IDEAS,
    GeneratedIdea,
    QualityGate,
    QualityResult,
    parse_ideas_from_response,
)
from research_system.synthesis.runner import SynthesisRunResult, SynthesisRunner


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def workspace(tmp_path):
    """Create and initialize a V4 workspace in a temporary directory."""
    ws = Workspace(tmp_path)
    ws.init()
    return ws


def _make_valid_idea(**overrides) -> GeneratedIdea:
    """Create a GeneratedIdea with valid defaults; caller can override fields."""
    defaults = dict(
        name="VIX Mean Reversion",
        thesis="VIX tends to mean-revert after spikes",
        hypothesis="When VIX > 30 and drops 10% from peak, buy SPY for 5 day hold period",
        entry_type="technical",
        data_requirements=["equities"],
        entry_logic="Buy SPY when VIX crosses below 30 after being above 35 for at least 2 days",
        exit_logic="Sell after 5 trading days or if VIX spikes back above 35",
        risk_management="2% of portfolio per trade, stop at VIX > 40",
        expected_characteristics={"holding_period": "5 days"},
        confidence="high",
        rationale="VIX mean reversion is well-documented behavioral pattern",
        persona="edge-hunter",
    )
    defaults.update(overrides)
    return GeneratedIdea(**defaults)


class MockLLMClient:
    """Minimal mock for LLMClient that returns canned responses."""

    def __init__(self, response_content: str = "", offline: bool = False):
        self.response_content = response_content
        self._offline = offline
        self.calls: list[dict] = []

    @property
    def is_offline(self) -> bool:
        return self._offline

    @property
    def backend(self) -> Backend:
        return Backend.OFFLINE if self._offline else Backend.API

    def generate(self, **kwargs) -> LLMResponse:
        self.calls.append(kwargs)
        return LLMResponse(content=self.response_content, model="mock")


# =============================================================================
# CONTEXT AGGREGATOR
# =============================================================================


class TestWorkspaceContextAggregator:
    """Test context aggregation from V4 workspace."""

    def test_aggregate_empty_workspace(self, workspace):
        """Aggregation of a fresh (empty) workspace succeeds with empty lists."""
        ctx = WorkspaceContextAggregator(workspace).aggregate()

        assert isinstance(ctx, WorkspaceContext)
        assert ctx.validated == []
        assert ctx.invalidated == []
        assert ctx.pending == []
        assert ctx.learnings == []
        assert ctx.summary_stats["total_strategies"] == 0

    def test_aggregate_with_strategies(self, workspace):
        """Strategy YAML files appear in the correct status bucket."""
        strat_data = {
            "id": "STRAT-001",
            "name": "Test Strategy",
            "hypothesis": {"thesis": "VIX mean-reverts after spikes"},
            "entry": {"type": "technical"},
            "universe": {"instruments": [{"symbol": "SPY"}]},
        }
        validated_dir = workspace.strategies_path / "validated"
        validated_dir.mkdir(parents=True, exist_ok=True)
        with open(validated_dir / "STRAT-001.yaml", "w") as f:
            yaml.dump(strat_data, f)

        ctx = WorkspaceContextAggregator(workspace).aggregate()

        assert len(ctx.validated) == 1
        s = ctx.validated[0]
        assert s.id == "STRAT-001"
        assert s.name == "Test Strategy"
        assert s.status == "validated"
        assert s.hypothesis == "VIX mean-reverts after spikes"
        assert s.entry_type == "technical"
        assert "SPY" in s.instruments

    def test_aggregate_with_validation_results(self, workspace):
        """Backtest metrics are loaded and attached to the strategy."""
        # Create strategy
        strat_data = {
            "id": "STRAT-001",
            "name": "Strat One",
            "hypothesis": {"thesis": "test hypothesis text here"},
            "entry": {"type": "statistical"},
            "universe": {"instruments": [{"symbol": "QQQ"}]},
        }
        validated_dir = workspace.strategies_path / "validated"
        validated_dir.mkdir(parents=True, exist_ok=True)
        with open(validated_dir / "STRAT-001.yaml", "w") as f:
            yaml.dump(strat_data, f)

        # Create backtest results
        val_dir = workspace.validations_path / "STRAT-001"
        val_dir.mkdir(parents=True, exist_ok=True)
        backtest = {
            "sharpe_ratio": 1.5,
            "cagr": 0.15,
            "max_drawdown": 0.12,
            "total_trades": 200,
        }
        with open(val_dir / "backtest_results.yaml", "w") as f:
            yaml.dump(backtest, f)

        ctx = WorkspaceContextAggregator(workspace).aggregate()

        s = ctx.validated[0]
        assert s.sharpe == pytest.approx(1.5)
        assert s.cagr == pytest.approx(0.15)
        assert s.max_drawdown == pytest.approx(0.12)
        assert s.total_trades == 200

    def test_aggregate_with_walk_forward_results(self, workspace):
        """Walk-forward per-window data is loaded and consistency computed."""
        strat_data = {
            "id": "STRAT-002",
            "name": "WF Strat",
            "hypothesis": {"thesis": "walk forward test hypothesis"},
            "entry": {"type": "technical"},
            "universe": {"instruments": []},
        }
        validated_dir = workspace.strategies_path / "validated"
        validated_dir.mkdir(parents=True, exist_ok=True)
        with open(validated_dir / "STRAT-002.yaml", "w") as f:
            yaml.dump(strat_data, f)

        val_dir = workspace.validations_path / "STRAT-002"
        val_dir.mkdir(parents=True, exist_ok=True)
        wf_data = {
            "windows": [
                {"period": "2018-2019", "sharpe_ratio": 1.2},
                {"period": "2019-2020", "sharpe_ratio": -0.3},
                {"period": "2020-2021", "sharpe_ratio": 0.8},
            ]
        }
        with open(val_dir / "walk_forward_results.yaml", "w") as f:
            yaml.dump(wf_data, f)

        ctx = WorkspaceContextAggregator(workspace).aggregate()
        s = ctx.validated[0]
        assert s.per_window is not None
        assert len(s.per_window) == 3
        # 2 of 3 windows have sharpe > 0 => consistency = 2/3
        assert s.consistency == pytest.approx(2.0 / 3.0)

    def test_aggregate_with_learnings(self, workspace):
        """Learning YAML files are loaded correctly."""
        learning_data = {
            "strategy_id": "STRAT-001",
            "learnings": [
                {
                    "category": "parameter",
                    "insight": "Lookback period of 5 is too short",
                    "recommendation": "Use 20-day lookback",
                },
                {
                    "category": "regime",
                    "insight": "Strategy fails in low-vol regimes",
                    "recommendation": "Add VIX filter",
                },
            ],
        }
        learnings_dir = workspace.learnings_path
        learnings_dir.mkdir(parents=True, exist_ok=True)
        with open(learnings_dir / "learning-001.yaml", "w") as f:
            yaml.dump(learning_data, f)

        ctx = WorkspaceContextAggregator(workspace).aggregate()

        assert len(ctx.learnings) == 2
        assert ctx.learnings[0].strategy_id == "STRAT-001"
        assert ctx.learnings[0].category == "parameter"
        assert "lookback" in ctx.learnings[0].description.lower()

    def test_malformed_yaml_skipped(self, workspace):
        """Malformed YAML files are skipped gracefully, no crash."""
        validated_dir = workspace.strategies_path / "validated"
        validated_dir.mkdir(parents=True, exist_ok=True)
        with open(validated_dir / "bad.yaml", "w") as f:
            f.write("not: [valid: yaml: {{{}}")

        # Should not raise
        ctx = WorkspaceContextAggregator(workspace).aggregate()
        assert ctx.validated == []

    def test_aggregate_summary_stats(self, workspace):
        """Summary stats include counts and metric averages."""
        # Create two validated strategies with metrics
        validated_dir = workspace.strategies_path / "validated"
        validated_dir.mkdir(parents=True, exist_ok=True)
        for idx, sharpe in enumerate([1.0, 2.0], start=1):
            sid = f"STRAT-{idx:03d}"
            strat = {
                "id": sid,
                "name": f"Strat {idx}",
                "hypothesis": {"thesis": "some test hypothesis here"},
                "entry": {"type": "technical"},
                "universe": {"instruments": []},
            }
            with open(validated_dir / f"{sid}.yaml", "w") as f:
                yaml.dump(strat, f)
            val_dir = workspace.validations_path / sid
            val_dir.mkdir(parents=True, exist_ok=True)
            with open(val_dir / "backtest_results.yaml", "w") as f:
                yaml.dump({"sharpe_ratio": sharpe, "cagr": 0.1 * idx}, f)

        # Create one pending strategy (no metrics)
        pending_dir = workspace.strategies_path / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        with open(pending_dir / "STRAT-003.yaml", "w") as f:
            yaml.dump(
                {
                    "id": "STRAT-003",
                    "name": "Pending",
                    "hypothesis": {"thesis": "pending hypothesis text here"},
                    "entry": {"type": "event"},
                    "universe": {"instruments": []},
                },
                f,
            )

        ctx = WorkspaceContextAggregator(workspace).aggregate()

        assert ctx.summary_stats["validated_count"] == 2
        assert ctx.summary_stats["pending_count"] == 1
        assert ctx.summary_stats["total_strategies"] == 3
        assert ctx.summary_stats["avg_sharpe"] == pytest.approx(1.5)
        assert ctx.summary_stats["best_sharpe"] == pytest.approx(2.0)

    def test_determination_reason_loaded(self, workspace):
        """Determination reason from determination.json is loaded."""
        validated_dir = workspace.strategies_path / "validated"
        validated_dir.mkdir(parents=True, exist_ok=True)
        strat = {
            "id": "STRAT-001",
            "name": "Determined",
            "hypothesis": {"thesis": "has determination reason"},
            "entry": {"type": "technical"},
            "universe": {"instruments": []},
        }
        with open(validated_dir / "STRAT-001.yaml", "w") as f:
            yaml.dump(strat, f)

        val_dir = workspace.validations_path / "STRAT-001"
        val_dir.mkdir(parents=True, exist_ok=True)
        with open(val_dir / "determination.json", "w") as f:
            json.dump({"reason": "Consistent Sharpe > 1.0 across all windows"}, f)

        ctx = WorkspaceContextAggregator(workspace).aggregate()
        assert ctx.validated[0].determination_reason == "Consistent Sharpe > 1.0 across all windows"


# =============================================================================
# QUALITY GATE
# =============================================================================


class TestQualityGate:
    """Test programmatic filtering and ranking of generated ideas."""

    def test_accepts_valid_idea(self):
        """A fully valid idea passes the quality gate."""
        idea = _make_valid_idea()
        gate = QualityGate()
        result = gate.filter([idea])

        assert len(result.accepted) == 1
        assert result.accepted[0].name == "VIX Mean Reversion"
        assert result.total_generated == 1

    def test_rejects_missing_entry_logic(self):
        """Ideas with empty or too-short entry_logic are rejected."""
        idea = _make_valid_idea(entry_logic="buy")
        gate = QualityGate()
        result = gate.filter([idea])

        assert len(result.accepted) == 0
        assert len(result.rejected) == 1
        assert "entry logic" in result.rejected[0][1].lower()

    def test_rejects_missing_exit_logic(self):
        """Ideas with empty or too-short exit_logic are rejected."""
        idea = _make_valid_idea(exit_logic="sell")
        gate = QualityGate()
        result = gate.filter([idea])

        assert len(result.accepted) == 0
        assert "exit logic" in result.rejected[0][1].lower()

    def test_rejects_missing_hypothesis(self):
        """Ideas with short hypothesis are rejected."""
        idea = _make_valid_idea(hypothesis="short")
        gate = QualityGate()
        result = gate.filter([idea])

        assert len(result.accepted) == 0
        assert "hypothesis" in result.rejected[0][1].lower()

    def test_rejects_low_confidence(self):
        """Ideas with confidence='low' are rejected."""
        idea = _make_valid_idea(confidence="low")
        gate = QualityGate()
        result = gate.filter([idea])

        assert len(result.accepted) == 0
        assert "low confidence" in result.rejected[0][1].lower()

    def test_max_ideas_cap(self):
        """At most MAX_IDEAS (3) ideas are accepted even if more pass filters."""
        ideas = [_make_valid_idea(name=f"Idea {i}") for i in range(5)]
        gate = QualityGate()
        result = gate.filter(ideas)

        assert len(result.accepted) == MAX_IDEAS
        assert result.total_generated == 5
        # Remaining are rejected with cap reason
        excess_rejected = [
            r for r in result.rejected if "max ideas" in r[1].lower()
        ]
        assert len(excess_rejected) == 2

    def test_rejects_unavailable_data(self):
        """Ideas referencing unknown data sources are rejected when registry is provided."""
        idea = _make_valid_idea(data_requirements=["secret_sauce_data"])
        gate = QualityGate(available_data=["equities", "futures"])
        result = gate.filter([idea])

        assert len(result.accepted) == 0
        assert "unavailable data" in result.rejected[0][1].lower()

    def test_standard_data_always_available(self):
        """Standard data (equities, futures, etc.) passes even with a restricted registry."""
        idea = _make_valid_idea(data_requirements=["equities"])
        gate = QualityGate(available_data=["some_custom_source"])
        result = gate.filter([idea])

        assert len(result.accepted) == 1

    def test_ranking_prefers_high_confidence(self):
        """High confidence ideas are ranked above medium confidence."""
        high = _make_valid_idea(name="High", confidence="high")
        med = _make_valid_idea(name="Medium", confidence="medium")
        gate = QualityGate()
        result = gate.filter([med, high])

        # Both accepted, but high confidence should be first
        assert result.accepted[0].name == "High"
        assert result.accepted[1].name == "Medium"


class TestParseIdeasFromResponse:
    """Test parsing of LLM JSON responses into GeneratedIdea objects."""

    def test_parse_json_block(self):
        """Ideas are parsed from a fenced ```json block."""
        response = '```json\n{"ideas": [{"name": "Test", "thesis": "test thesis", "hypothesis": "when X then Y within Z timeframe for profit", "entry_type": "technical", "data_requirements": ["equities"], "entry_logic": "buy when RSI below 30 for 2 consecutive days", "exit_logic": "sell after 5 days or RSI above 70", "risk_management": "2% per trade", "expected_characteristics": {}, "confidence": "high", "rationale": "mean reversion"}]}\n```'
        ideas = parse_ideas_from_response(response, "test-persona")

        assert len(ideas) == 1
        assert ideas[0].name == "Test"
        assert ideas[0].persona == "test-persona"

    def test_parse_raw_json_array(self):
        """Ideas are parsed from a bare JSON array."""
        response = json.dumps(
            [
                {
                    "name": "Raw Idea",
                    "thesis": "raw thesis",
                    "hypothesis": "raw hypothesis text for testing",
                    "entry_type": "statistical",
                    "data_requirements": [],
                    "entry_logic": "some entry logic with enough length",
                    "exit_logic": "some exit logic with enough length",
                    "risk_management": "",
                    "expected_characteristics": {},
                    "confidence": "medium",
                    "rationale": "raw rationale",
                }
            ]
        )
        ideas = parse_ideas_from_response(response, "raw")
        assert len(ideas) == 1
        assert ideas[0].name == "Raw Idea"

    def test_parse_malformed_json(self):
        """Malformed JSON returns empty list, no crash."""
        ideas = parse_ideas_from_response("not json at all", "test")
        assert len(ideas) == 0

    def test_parse_empty_response(self):
        """Empty response returns empty list."""
        ideas = parse_ideas_from_response("", "test")
        assert len(ideas) == 0

    def test_parse_json_object_wrapper(self):
        """A JSON object with 'ideas' key is unwrapped correctly."""
        payload = {
            "persona": "edge-hunter",
            "ideas": [
                {
                    "name": "Wrapped Idea",
                    "thesis": "t",
                    "hypothesis": "h",
                    "entry_type": "technical",
                    "data_requirements": [],
                    "entry_logic": "e",
                    "exit_logic": "x",
                    "risk_management": "r",
                    "expected_characteristics": {},
                    "confidence": "high",
                    "rationale": "r",
                }
            ],
        }
        ideas = parse_ideas_from_response(json.dumps(payload), "edge-hunter")
        assert len(ideas) == 1
        assert ideas[0].name == "Wrapped Idea"


# =============================================================================
# OUTPUT
# =============================================================================


class TestOutputConverter:
    """Test saving ideas as strategy YAML and synthesis reports."""

    def test_save_idea_as_strategy(self, workspace):
        """A GeneratedIdea is correctly saved as a V4 Strategy YAML file."""
        idea = _make_valid_idea(persona="edge-hunter", confidence="high")
        filepath = save_idea_as_strategy(idea, workspace)

        assert filepath.exists()
        assert filepath.suffix == ".yaml"
        assert filepath.parent == workspace.strategies_path / "pending"

        with open(filepath) as f:
            data = yaml.safe_load(f)

        assert data["id"].startswith("STRAT-")
        assert data["name"] == "VIX Mean Reversion"
        assert data["status"] == "pending"
        assert data["source"]["type"] == "synthesis"
        assert "synthesis-generated" in data["tags"]["custom"]
        assert "persona:edge-hunter" in data["tags"]["custom"]
        assert "confidence:high" in data["tags"]["custom"]
        assert data["hypothesis"]["thesis"] == idea.hypothesis
        assert data["entry"]["type"] == "technical"
        assert data["exit"]["description"] == idea.exit_logic

    def test_save_idea_increments_id(self, workspace):
        """Successive saves produce distinct, incrementing strategy IDs."""
        idea1 = _make_valid_idea(name="Idea One")
        idea2 = _make_valid_idea(name="Idea Two")

        p1 = save_idea_as_strategy(idea1, workspace)
        p2 = save_idea_as_strategy(idea2, workspace)

        assert p1.name != p2.name  # Different filenames (STRAT-001 vs STRAT-002)
        with open(p1) as f:
            d1 = yaml.safe_load(f)
        with open(p2) as f:
            d2 = yaml.safe_load(f)
        assert d1["id"] != d2["id"]

    def test_save_idea_with_lineage(self, workspace):
        """Related strategies appear in the lineage section."""
        idea = _make_valid_idea(related_strategies=["STRAT-001", "STRAT-002"])
        filepath = save_idea_as_strategy(idea, workspace)

        with open(filepath) as f:
            data = yaml.safe_load(f)

        assert "lineage" in data
        parent_ids = [p["id"] for p in data["lineage"]["parents"]]
        assert "STRAT-001" in parent_ids
        assert "STRAT-002" in parent_ids

    def test_save_synthesis_report(self, workspace):
        """Synthesis report is saved with expected structure."""
        ideas = [_make_valid_idea(name="Idea A"), _make_valid_idea(name="Idea B")]
        persona_responses = {
            "edge-hunter": "edge-hunter produced analysis text here",
            "macro-strategist": "macro analysis text",
        }
        report_path = save_synthesis_report(ideas, persona_responses, workspace)

        assert report_path.exists()
        assert report_path.parent == workspace.ideas_path

        with open(report_path) as f:
            data = yaml.safe_load(f)

        assert data["total_ideas"] == 2
        assert len(data["ideas"]) == 2
        assert "edge-hunter" in data["persona_summaries"]


# =============================================================================
# PROMPT BUILDER
# =============================================================================


class TestPromptBuilder:
    """Test prompt construction with persona definitions and workspace context."""

    def test_build_system_prompt_contains_critical_instructions(self):
        """System prompt always contains CRITICAL INSTRUCTIONS block."""
        builder = PromptBuilder()
        prompt = builder.build_system_prompt("edge-hunter")

        assert "CRITICAL INSTRUCTIONS" in prompt
        assert "DO NOT use any tools" in prompt

    def test_build_system_prompt_includes_persona(self):
        """System prompt for a known persona includes its definition text."""
        builder = PromptBuilder()
        prompt = builder.build_system_prompt("edge-hunter")
        # The prompt should contain something beyond just the boilerplate,
        # indicating the persona file was loaded (if it exists on disk).
        assert len(prompt) > 200

    def test_build_ideation_prompt_includes_context(self):
        """Ideation prompt includes workspace context data."""
        builder = PromptBuilder()
        ctx = WorkspaceContext(
            validated=[
                StrategyWithMetrics(
                    id="STRAT-001",
                    name="Test Strat",
                    status="validated",
                    hypothesis="A testable hypothesis",
                    entry_type="technical",
                    instruments=["SPY"],
                    sharpe=1.5,
                )
            ],
            invalidated=[],
            pending=[],
            learnings=[],
            available_data=["equities"],
            summary_stats={
                "total_strategies": 1,
                "validated_count": 1,
                "invalidated_count": 0,
                "pending_count": 0,
                "entry_type_distribution": {"technical": 1},
            },
        )
        prompt = builder.build_ideation_prompt("edge-hunter", ctx)

        assert "STRAT-001" in prompt
        assert "Test Strat" in prompt

    def test_build_synthesis_prompt_portfolio_architect(self):
        """Portfolio-architect synthesis prompt includes correlation data."""
        builder = PromptBuilder()
        ctx = WorkspaceContext(
            validated=[
                StrategyWithMetrics(
                    id="STRAT-001",
                    name="Strat A",
                    status="validated",
                    hypothesis="Hypo A",
                    entry_type="technical",
                    instruments=["SPY", "QQQ"],
                    sharpe=1.2,
                    max_drawdown=0.1,
                ),
                StrategyWithMetrics(
                    id="STRAT-002",
                    name="Strat B",
                    status="validated",
                    hypothesis="Hypo B",
                    entry_type="statistical",
                    instruments=["SPY", "IWM"],
                    sharpe=0.9,
                    max_drawdown=0.15,
                ),
            ],
            invalidated=[],
            pending=[],
            learnings=[],
            available_data=[],
            summary_stats={
                "total_strategies": 2,
                "validated_count": 2,
                "invalidated_count": 0,
                "pending_count": 0,
                "entry_type_distribution": {"technical": 1, "statistical": 1},
            },
        )
        prompt = builder.build_synthesis_prompt("portfolio-architect", ctx)

        # Should contain strategy metrics and overlap section
        assert "STRAT-001" in prompt
        assert "STRAT-002" in prompt
        assert "Overlap" in prompt or "overlap" in prompt

    def test_build_synthesis_prompt_regime_strategist(self):
        """Regime-strategist synthesis prompt includes per-window data."""
        builder = PromptBuilder()
        ctx = WorkspaceContext(
            validated=[
                StrategyWithMetrics(
                    id="STRAT-001",
                    name="Regime Strat",
                    status="validated",
                    hypothesis="Regime dependent",
                    entry_type="technical",
                    instruments=["SPY"],
                    per_window=[
                        {"period": "2018-2019", "sharpe_ratio": 1.1},
                        {"period": "2019-2020", "sharpe_ratio": -0.2},
                    ],
                )
            ],
            invalidated=[],
            pending=[],
            learnings=[],
            available_data=[],
            summary_stats={
                "total_strategies": 1,
                "validated_count": 1,
                "invalidated_count": 0,
                "pending_count": 0,
                "entry_type_distribution": {"technical": 1},
            },
        )
        prompt = builder.build_synthesis_prompt("regime-strategist", ctx)

        assert "Per-Window" in prompt or "per-window" in prompt.lower()
        assert "2018-2019" in prompt

    def test_build_director_prompt(self):
        """Director prompt includes workspace summary and persona responses."""
        builder = PromptBuilder()
        ctx = WorkspaceContext(
            validated=[],
            invalidated=[],
            pending=[],
            learnings=[],
            available_data=[],
            summary_stats={
                "total_strategies": 0,
                "validated_count": 0,
                "invalidated_count": 0,
                "pending_count": 0,
                "entry_type_distribution": {},
            },
        )
        persona_responses = {
            "portfolio-architect": "architect analysis here",
            "regime-strategist": "regime analysis here",
        }
        prompt = builder.build_director_prompt(ctx, persona_responses)

        assert "Synthesis Director" in prompt
        assert "architect analysis here" in prompt
        assert "regime analysis here" in prompt


# =============================================================================
# RUNNER
# =============================================================================


class TestSynthesisRunner:
    """Test the main SynthesisRunner orchestrator."""

    def test_ideate_offline(self, workspace):
        """Ideation with no LLM returns offline result."""
        runner = SynthesisRunner(workspace, llm_client=None)
        result = runner.ideate()

        assert isinstance(result, SynthesisRunResult)
        assert result.offline is True
        assert result.mode == "ideate"
        assert len(result.errors) > 0

    def test_ideate_offline_with_offline_client(self, workspace):
        """Ideation with an offline client returns offline result."""
        client = MockLLMClient(offline=True)
        runner = SynthesisRunner(workspace, llm_client=client)
        result = runner.ideate()

        assert result.offline is True

    def test_ideate_with_mock_llm(self, workspace):
        """Full ideation pipeline with mock LLM parses ideas and saves strategies."""
        # Build a response the mock LLM will return
        idea_payload = json.dumps(
            {
                "ideas": [
                    {
                        "name": "Mock Mean Reversion",
                        "thesis": "Mean reversion in equity markets",
                        "hypothesis": "When SPY drops 3% in a day, it mean-reverts within 5 days at least 60% of the time",
                        "entry_type": "statistical",
                        "data_requirements": ["equities"],
                        "entry_logic": "Buy SPY at close when daily return is below -3% and RSI(14) is below 30",
                        "exit_logic": "Sell after 5 trading days or at 2% profit target whichever comes first",
                        "risk_management": "2% per trade, max 3 concurrent positions, 10% portfolio VaR limit",
                        "expected_characteristics": {"holding_period": "5 days"},
                        "confidence": "high",
                        "rationale": "Well-documented short-term mean reversion in large-cap equities",
                    }
                ]
            }
        )
        llm_response = f"```json\n{idea_payload}\n```"

        client = MockLLMClient(response_content=llm_response)
        runner = SynthesisRunner(workspace, llm_client=client)
        result = runner.ideate()

        assert result.offline is False
        assert result.mode == "ideate"
        # Each of the 3 ideation personas is called
        assert len(client.calls) == 3
        # Quality gate should accept the ideas (up to MAX_IDEAS)
        assert result.ideas_accepted >= 1
        # Strategy files saved
        assert len(result.strategy_files) >= 1
        for path in result.strategy_files:
            assert path.exists()
        # Report saved
        assert result.report_file is not None
        assert result.report_file.exists()

    def test_synthesize_no_validated(self, workspace):
        """Synthesis with no validated strategies reports an error."""
        client = MockLLMClient(response_content="{}")
        runner = SynthesisRunner(workspace, llm_client=client)
        result = runner.synthesize()

        assert result.mode == "synthesize"
        assert any("no validated" in e.lower() for e in result.errors)

    def test_synthesize_offline(self, workspace):
        """Synthesis with no LLM returns offline result."""
        runner = SynthesisRunner(workspace, llm_client=None)
        result = runner.synthesize()

        assert result.offline is True
        assert result.mode == "synthesize"

    def test_synthesis_run_result_to_dict(self):
        """SynthesisRunResult serializes to a dict correctly."""
        result = SynthesisRunResult(mode="ideate")
        result.ideas_generated = 5
        result.ideas_accepted = 2
        result.offline = False

        d = result.to_dict()
        assert d["mode"] == "ideate"
        assert d["ideas_generated"] == 5
        assert d["ideas_accepted"] == 2
        assert d["offline"] is False
        assert isinstance(d["accepted_ideas"], list)
        assert isinstance(d["strategy_files"], list)

    def test_synthesize_with_validated_strategies(self, workspace):
        """Full synthesis pipeline runs all specialist personas + director."""
        # Create a validated strategy in the workspace
        strat_data = {
            "id": "STRAT-001",
            "name": "Validated Strategy",
            "hypothesis": {"thesis": "A testable hypothesis for validation"},
            "entry": {"type": "technical"},
            "universe": {"instruments": [{"symbol": "SPY"}]},
        }
        validated_dir = workspace.strategies_path / "validated"
        validated_dir.mkdir(parents=True, exist_ok=True)
        with open(validated_dir / "STRAT-001.yaml", "w") as f:
            yaml.dump(strat_data, f)

        # Mock LLM returns a simple JSON response (no ideas from director)
        client = MockLLMClient(response_content='{"recommendations": [], "key_insights": [], "risks_and_concerns": []}')
        runner = SynthesisRunner(workspace, llm_client=client)
        result = runner.synthesize()

        assert result.mode == "synthesize"
        assert result.offline is False
        # 5 synthesis personas + 1 director = 6 calls
        assert len(client.calls) == 6
        # All persona responses recorded
        assert len(result.persona_responses) == 6


# =============================================================================
# STRATEGY WITH METRICS
# =============================================================================


class TestStrategyWithMetrics:
    """Test StrategyWithMetrics data class behaviour."""

    def test_to_summary_line_with_metrics(self):
        """Summary line includes Sharpe, CAGR, MaxDD when present."""
        s = StrategyWithMetrics(
            id="STRAT-001",
            name="Test",
            status="validated",
            hypothesis="Test hypothesis",
            entry_type="technical",
            instruments=["SPY"],
            sharpe=1.5,
            cagr=0.12,
            max_drawdown=0.08,
            consistency=0.75,
        )
        line = s.to_summary_line()
        assert "STRAT-001" in line
        assert "Sharpe=1.50" in line
        assert "CAGR=12.0%" in line
        assert "MaxDD=8.0%" in line
        assert "Consistency=75%" in line

    def test_to_summary_line_no_metrics(self):
        """Summary line says 'No metrics' when nothing is set."""
        s = StrategyWithMetrics(
            id="STRAT-002",
            name="Bare",
            status="pending",
            hypothesis="Bare hypothesis",
            entry_type="event",
            instruments=[],
        )
        line = s.to_summary_line()
        assert "No metrics" in line
