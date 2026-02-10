"""Tests for V4 ingest processor.

This module tests the V4 ingestion functionality:
1. IngestProcessor initialization
2. Processing single files
3. Processing entire inbox
4. Quality scoring (specificity, trust)
5. Red flag detection
6. Strategy creation and saving
7. Dry-run mode
8. Error handling
"""

import glob as glob_mod
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from research_system.core.v4 import Workspace, Config, get_default_config
from research_system.ingest.strategy_processor import (
    IngestProcessor,
    IngestResult,
    IngestSummary,
)
from research_system.schemas.v4 import (
    IngestionDecision,
    IngestionQuality,
    SpecificityScore,
    TrustScore,
    Strategy,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def workspace(tmp_path):
    """Create an initialized V4 workspace."""
    ws = Workspace(tmp_path)
    ws.init()
    return ws


@pytest.fixture
def config():
    """Get default V4 config."""
    return get_default_config()


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    client.is_offline = False
    return client


@pytest.fixture
def processor(workspace, config, mock_llm_client):
    """Create a IngestProcessor."""
    return IngestProcessor(workspace, config, mock_llm_client)


@pytest.fixture
def sample_strategy_text():
    """Sample strategy document text."""
    return """
# Moving Average Crossover Strategy

## Overview
This strategy uses a simple moving average crossover system to generate buy and sell signals.

## Entry Rules
- Buy when the 50-day SMA crosses above the 200-day SMA (Golden Cross)
- Only enter when RSI > 30 to avoid oversold conditions

## Exit Rules
- Sell when the 50-day SMA crosses below the 200-day SMA (Death Cross)
- Stop loss at 5% below entry price
- Take profit at 15% above entry price

## Universe
Trade SPY, QQQ, and IWM ETFs.

## Position Sizing
Equal weight across all positions. Maximum 3 positions at once.
Risk no more than 2% of portfolio per trade.

## Rationale
Moving average crossovers capture momentum shifts. The edge exists because
retail traders are slow to react to trend changes, creating predictable
price patterns. Institutional flow tends to follow these signals.

## Historical Performance
Backtested from 2010-2023 with a Sharpe ratio of 1.2 and max drawdown of 18%.
"""


# =============================================================================
# TEST PROCESSOR INITIALIZATION
# =============================================================================


class TestProcessorInit:
    """Test IngestProcessor initialization."""

    def test_processor_initializes(self, workspace, config, mock_llm_client):
        """Test processor initializes with required components."""
        processor = IngestProcessor(workspace, config, mock_llm_client)

        assert processor.workspace is workspace
        assert processor.config is config
        assert processor.llm_client is mock_llm_client

    def test_processor_without_llm_client(self, workspace, config):
        """Test processor works without LLM client (offline mode)."""
        processor = IngestProcessor(workspace, config, None)

        assert processor.llm_client is None


# =============================================================================
# TEST FILE PROCESSING
# =============================================================================


class TestFileProcessing:
    """Test single file processing."""

    def test_process_nonexistent_file(self, processor, workspace):
        """Test processing a file that doesn't exist."""
        fake_path = workspace.inbox_path / "nonexistent.txt"

        result = processor.process_file(fake_path)

        assert not result.success
        assert result.error is not None
        assert "read" in result.error.lower() or "exist" in result.error.lower()

    def test_process_text_file(self, processor, workspace, sample_strategy_text):
        """Test processing a text file."""
        # Create a test file
        test_file = workspace.inbox_path / "strategy.txt"
        test_file.write_text(sample_strategy_text)

        # Mock LLM response
        processor.llm_client.generate_sonnet.return_value = MagicMock(
            content=json.dumps({
                "name": "Moving Average Crossover Strategy",
                "hypothesis": {
                    "summary": "SMA crossover for momentum capture",
                    "detail": "Uses 50/200 SMA crossover",
                    "edge_mechanism": "Momentum capture",
                    "edge_category": "behavioral",
                    "why_exists": "Retail traders slow to react",
                    "counterparty": "Late retail traders",
                    "why_persists": "Human nature",
                    "decay_conditions": "HFT competition"
                },
                "source": {
                    "type": "personal",
                    "author_track_record": "unknown",
                    "author_skin_in_game": False
                },
                "universe": {
                    "type": "static",
                    "instruments": ["SPY", "QQQ", "IWM"]
                },
                "entry": {
                    "type": "technical",
                    "rules": ["50-day SMA crosses above 200-day SMA"],
                    "indicators": ["SMA(50)", "SMA(200)", "RSI"]
                },
                "exit": {
                    "rules": ["50-day SMA crosses below 200-day SMA"],
                    "stop_loss": "5% below entry",
                    "take_profit": "15% above entry"
                },
                "position_sizing": {
                    "method": "equal_weight",
                    "description": "Equal weight, max 3 positions"
                },
                "data_requirements": ["price_data"],
                "tags": {
                    "hypothesis_types": ["momentum", "trend_following"],
                    "asset_classes": ["etf"],
                    "complexity": "simple"
                }
            }),
            offline=False
        )
        processor.llm_client.extract_json.return_value = json.loads(
            processor.llm_client.generate_sonnet.return_value.content
        )

        result = processor.process_file(test_file, dry_run=True)

        assert result.strategy_name == "Moving Average Crossover Strategy"
        assert result.quality is not None
        assert result.decision is not None

    def test_process_file_dry_run(self, processor, workspace, sample_strategy_text):
        """Test dry-run doesn't save files."""
        test_file = workspace.inbox_path / "strategy.txt"
        test_file.write_text(sample_strategy_text)

        # Use offline mode to avoid LLM
        processor.llm_client = None

        # Mock high quality scores to ensure acceptance
        with patch.object(processor, '_score_quality') as mock_score:
            mock_score.return_value = IngestionQuality(
                specificity=SpecificityScore(
                    has_entry_rules=True,
                    has_exit_rules=True,
                    has_position_sizing=True,
                    has_universe_definition=True,
                ),
                trust_score=TrustScore(
                    economic_rationale=20,
                    implementation_realism=15,
                    source_credibility=10,
                    novelty=5,
                ),
            )

            result = processor.process_file(test_file, dry_run=True)

        assert result.dry_run is True
        assert "DRY-RUN" in str(result.strategy_id)
        # File should still exist in inbox
        assert test_file.exists()

    def test_process_file_creates_strategy(self, processor, workspace, sample_strategy_text):
        """Test processing creates a strategy file."""
        test_file = workspace.inbox_path / "strategy.txt"
        test_file.write_text(sample_strategy_text)

        # Use offline mode - creates minimal strategy
        processor.llm_client = None

        # Force acceptance by mocking quality scores
        with patch.object(processor, '_score_quality') as mock_score:
            mock_score.return_value = IngestionQuality(
                specificity=SpecificityScore(
                    has_entry_rules=True,
                    has_exit_rules=True,
                    has_position_sizing=True,
                    has_universe_definition=True,
                ),
                trust_score=TrustScore(
                    economic_rationale=20,
                    implementation_realism=15,
                    source_credibility=10,
                    novelty=5,
                ),
            )

            result = processor.process_file(test_file, dry_run=False)

        assert result.success
        assert result.strategy_id is not None
        assert result.strategy_id.startswith("STRAT-")
        assert result.saved_path is not None

        # Strategy file should exist
        saved_path = Path(result.saved_path)
        assert saved_path.exists()

        # Verify YAML content
        with open(saved_path) as f:
            strategy_data = yaml.safe_load(f)
        assert strategy_data["id"] == result.strategy_id


# =============================================================================
# TEST INBOX PROCESSING
# =============================================================================


class TestInboxProcessing:
    """Test inbox batch processing."""

    def test_process_empty_inbox(self, processor, workspace):
        """Test processing an empty inbox."""
        summary = processor.process_inbox(dry_run=True)

        assert summary.total_files == 0
        assert len(summary.results) == 0

    def test_process_inbox_with_files(self, processor, workspace):
        """Test processing inbox with multiple files."""
        # Create test files
        (workspace.inbox_path / "strat1.txt").write_text("Strategy 1 content")
        (workspace.inbox_path / "strat2.txt").write_text("Strategy 2 content")
        (workspace.inbox_path / "strat3.md").write_text("# Strategy 3")

        # Use offline mode
        processor.llm_client = None

        summary = processor.process_inbox(dry_run=True)

        assert summary.total_files == 3
        assert len(summary.results) == 3

    def test_process_inbox_ignores_hidden_files(self, processor, workspace):
        """Test that hidden files are ignored."""
        (workspace.inbox_path / ".hidden").write_text("hidden")
        (workspace.inbox_path / ".DS_Store").write_text("ds store")
        (workspace.inbox_path / "visible.txt").write_text("visible")

        processor.llm_client = None
        summary = processor.process_inbox(dry_run=True)

        assert summary.total_files == 1

    def test_process_inbox_recursive(self, processor, workspace):
        """Test processing finds files in subdirectories."""
        subdir = workspace.inbox_path / "podcasts"
        subdir.mkdir()
        (subdir / "episode1.txt").write_text("Episode 1")
        (subdir / "episode2.txt").write_text("Episode 2")
        (workspace.inbox_path / "main.txt").write_text("Main")

        processor.llm_client = None
        summary = processor.process_inbox(dry_run=True)

        assert summary.total_files == 3


# =============================================================================
# TEST QUALITY SCORING
# =============================================================================


class TestQualityScoring:
    """Test ingestion quality scoring."""

    def test_specificity_score_calculation(self, processor, workspace):
        """Test specificity score calculation."""
        from research_system.schemas.v4 import (
            Strategy, StrategyStatus, StrategyMode, StrategySource,
            Hypothesis, Universe, UniverseType, Entry, EntryType,
            Position, PositionType, PositionLeg, Direction, LegInstrument,
            InstrumentSource, InstrumentAssetType, PositionSizing, SizingMethod,
            Exit, ExitPath, ExitType, ExitPriority, TechnicalConfig,
        )
        from datetime import datetime

        # Create a complete strategy
        strategy = Strategy(
            id="STRAT-001",
            name="Test Strategy",
            created=datetime.now(),
            status=StrategyStatus.PENDING,
            source=StrategySource(
                reference="test.txt",
                excerpt="Test",
                hash="abc123",
                extracted_date=datetime.now(),
            ),
            hypothesis=Hypothesis(
                summary="Test hypothesis",
                detail="Detailed description",
            ),
            strategy_mode=StrategyMode.SIMPLE,
            universe=Universe(type=UniverseType.STATIC),
            entry=Entry(
                type=EntryType.TECHNICAL,
                technical=TechnicalConfig(
                    indicator="SMA",
                    params={},
                    condition="SMA cross"
                )
            ),
            position=Position(
                type=PositionType.SINGLE_LEG,
                legs=[PositionLeg(
                    name="main",
                    direction=Direction.LONG,
                    instrument=LegInstrument(source=InstrumentSource.FROM_UNIVERSE),
                    asset_type=InstrumentAssetType.EQUITY,
                )],
                sizing=PositionSizing(method=SizingMethod.EQUAL_WEIGHT),
            ),
            exit=Exit(
                paths=[ExitPath(name="exit", type=ExitType.SIGNAL_REVERSAL)],
                priority=ExitPriority.FIRST_TRIGGERED,
            ),
        )

        quality = processor._score_quality(strategy, "test content")

        assert quality.specificity.has_entry_rules is True
        assert quality.specificity.has_exit_rules is True
        assert quality.specificity.has_position_sizing is True
        assert quality.specificity.score >= 3

    def test_trust_score_with_edge(self, processor, workspace):
        """Test trust score increases with edge information."""
        from research_system.schemas.v4 import (
            Strategy, StrategyStatus, StrategyMode, StrategySource,
            Hypothesis, StrategyEdge, EdgeCategory, Universe, UniverseType,
            Entry, EntryType, TechnicalConfig,
            Position, PositionType, PositionLeg, Direction, LegInstrument,
            InstrumentSource, InstrumentAssetType,
            Exit, ExitPath, ExitType, ExitPriority,
        )
        from datetime import datetime

        strategy = Strategy(
            id="STRAT-001",
            name="Test Strategy",
            created=datetime.now(),
            status=StrategyStatus.PENDING,
            source=StrategySource(
                reference="test.txt",
                excerpt="Test",
                hash="abc123",
                extracted_date=datetime.now(),
            ),
            hypothesis=Hypothesis(
                summary="Test hypothesis",
                detail="Detailed description",
                edge=StrategyEdge(
                    mechanism="Momentum capture",
                    category=EdgeCategory.BEHAVIORAL,
                    why_exists="Behavioral bias",
                    counterparty="Late traders",
                    why_persists="Human nature",
                    decay_conditions="HFT competition",
                ),
            ),
            strategy_mode=StrategyMode.SIMPLE,
            universe=Universe(type=UniverseType.STATIC),
            entry=Entry(
                type=EntryType.TECHNICAL,
                technical=TechnicalConfig(indicator="SMA", params={}, condition="cross")
            ),
            position=Position(
                type=PositionType.SINGLE_LEG,
                legs=[PositionLeg(
                    name="main",
                    direction=Direction.LONG,
                    instrument=LegInstrument(source=InstrumentSource.FROM_UNIVERSE),
                    asset_type=InstrumentAssetType.EQUITY,
                )],
            ),
            exit=Exit(
                paths=[ExitPath(name="exit", type=ExitType.SIGNAL_REVERSAL)],
                priority=ExitPriority.FIRST_TRIGGERED,
            ),
        )

        quality = processor._score_quality(strategy, "test content")

        # With full edge info, economic_rationale should be maxed out
        assert quality.trust_score.economic_rationale == 30


# =============================================================================
# TEST RED FLAG DETECTION
# =============================================================================


class TestRedFlagDetection:
    """Test red flag detection."""

    def test_detects_no_transaction_costs(self, processor, workspace):
        """Test detection of missing transaction costs."""
        from research_system.schemas.v4 import (
            Strategy, StrategyStatus, StrategyMode, StrategySource,
            Hypothesis, Universe, UniverseType,
            Entry, EntryType, TechnicalConfig,
            Position, PositionType, PositionLeg, Direction, LegInstrument,
            InstrumentSource, InstrumentAssetType,
            Exit, ExitPath, ExitType, ExitPriority,
        )
        from datetime import datetime

        strategy = Strategy(
            id="STRAT-001",
            name="Test Strategy",
            created=datetime.now(),
            status=StrategyStatus.PENDING,
            source=StrategySource(
                reference="test.txt",
                excerpt="Test",
                hash="abc123",
                extracted_date=datetime.now(),
            ),
            hypothesis=Hypothesis(
                summary="Test",
                detail="Test",
            ),
            strategy_mode=StrategyMode.SIMPLE,
            universe=Universe(type=UniverseType.STATIC),
            entry=Entry(
                type=EntryType.TECHNICAL,
                technical=TechnicalConfig(indicator="SMA", params={}, condition="cross")
            ),
            position=Position(
                type=PositionType.SINGLE_LEG,
                legs=[PositionLeg(
                    name="main",
                    direction=Direction.LONG,
                    instrument=LegInstrument(source=InstrumentSource.FROM_UNIVERSE),
                    asset_type=InstrumentAssetType.EQUITY,
                )],
            ),
            exit=Exit(
                paths=[ExitPath(name="exit", type=ExitType.SIGNAL_REVERSAL)],
                priority=ExitPriority.FIRST_TRIGGERED,
            ),
            assumptions=[],  # No assumptions about costs
        )

        flags = processor._detect_red_flags(strategy, "just a basic strategy")

        # Should detect no_transaction_costs
        flag_ids = [f.flag for f in flags]
        assert "no_transaction_costs" in flag_ids

    def test_detects_selling_author(self, processor, workspace):
        """Test detection of author selling courses."""
        from research_system.schemas.v4 import (
            Strategy, StrategyStatus, StrategyMode, StrategySource,
            Hypothesis, Universe, UniverseType,
            Entry, EntryType, TechnicalConfig,
            Position, PositionType, PositionLeg, Direction, LegInstrument,
            InstrumentSource, InstrumentAssetType,
            Exit, ExitPath, ExitType, ExitPriority,
        )
        from datetime import datetime

        strategy = Strategy(
            id="STRAT-001",
            name="Test Strategy",
            created=datetime.now(),
            status=StrategyStatus.PENDING,
            source=StrategySource(
                reference="test.txt",
                excerpt="Test",
                hash="abc123",
                extracted_date=datetime.now(),
            ),
            hypothesis=Hypothesis(
                summary="Test",
                detail="Test",
            ),
            strategy_mode=StrategyMode.SIMPLE,
            universe=Universe(type=UniverseType.STATIC),
            entry=Entry(
                type=EntryType.TECHNICAL,
                technical=TechnicalConfig(indicator="SMA", params={}, condition="cross")
            ),
            position=Position(
                type=PositionType.SINGLE_LEG,
                legs=[PositionLeg(
                    name="main",
                    direction=Direction.LONG,
                    instrument=LegInstrument(source=InstrumentSource.FROM_UNIVERSE),
                    asset_type=InstrumentAssetType.EQUITY,
                )],
            ),
            exit=Exit(
                paths=[ExitPath(name="exit", type=ExitType.SIGNAL_REVERSAL)],
                priority=ExitPriority.FIRST_TRIGGERED,
            ),
        )

        content = "This strategy is amazing! Buy my course to learn more."
        flags = processor._detect_red_flags(strategy, content)

        flag_ids = [f.flag for f in flags]
        assert "author_selling" in flag_ids


# =============================================================================
# TEST DECISION MAKING
# =============================================================================


class TestDecisionMaking:
    """Test ingestion decision logic."""

    def test_accept_good_strategy(self, processor, workspace, sample_strategy_text):
        """Test that good strategies are accepted."""
        test_file = workspace.inbox_path / "strategy.txt"
        test_file.write_text(sample_strategy_text)

        processor.llm_client = None

        # Mock high quality scores
        with patch.object(processor, '_score_quality') as mock_score:
            mock_score.return_value = IngestionQuality(
                specificity=SpecificityScore(
                    has_entry_rules=True,
                    has_exit_rules=True,
                    has_position_sizing=True,
                    has_universe_definition=True,
                    has_backtest_period=True,
                ),
                trust_score=TrustScore(
                    economic_rationale=25,
                    out_of_sample_evidence=15,
                    implementation_realism=15,
                    source_credibility=10,
                    novelty=5,
                ),
            )

            result = processor.process_file(test_file, dry_run=True)

        assert result.decision == IngestionDecision.ACCEPT

    def test_archive_low_specificity(self, processor, workspace):
        """Test that low specificity strategies are archived."""
        test_file = workspace.inbox_path / "vague.txt"
        test_file.write_text("Just buy when it looks good and sell when it looks bad.")

        processor.llm_client = None

        # Mock low specificity scores
        with patch.object(processor, '_score_quality') as mock_score:
            mock_score.return_value = IngestionQuality(
                specificity=SpecificityScore(
                    has_entry_rules=False,
                    has_exit_rules=False,
                    has_position_sizing=False,
                    has_universe_definition=False,
                ),
                trust_score=TrustScore(
                    economic_rationale=20,
                    implementation_realism=10,
                ),
            )

            result = processor.process_file(test_file, dry_run=True)

        assert result.decision == IngestionDecision.ARCHIVE

    def test_reject_hard_red_flags(self, processor, workspace):
        """Test that strategies with hard red flags are rejected."""
        test_file = workspace.inbox_path / "scam.txt"
        test_file.write_text("This strategy never has losing months!")

        processor.llm_client = None

        # Mock with hard red flag
        with patch.object(processor, '_score_quality') as mock_score:
            from research_system.schemas.v4 import create_hard_red_flag
            mock_score.return_value = IngestionQuality(
                specificity=SpecificityScore(
                    has_entry_rules=True,
                    has_exit_rules=True,
                    has_position_sizing=True,
                    has_universe_definition=True,
                ),
                trust_score=TrustScore(
                    economic_rationale=20,
                    implementation_realism=15,
                ),
                red_flags=[create_hard_red_flag("no_losing_periods")],
            )

            result = processor.process_file(test_file, dry_run=True)

        assert result.decision == IngestionDecision.REJECT


# =============================================================================
# TEST FILE ARCHIVING
# =============================================================================


class TestFileArchiving:
    """Test file archiving behavior."""

    def test_processed_files_archived(self, processor, workspace):
        """Test that processed files are moved to archive."""
        test_file = workspace.inbox_path / "strategy.txt"
        test_file.write_text("Test strategy content")

        processor.llm_client = None

        # Force acceptance
        with patch.object(processor, '_score_quality') as mock_score:
            mock_score.return_value = IngestionQuality(
                specificity=SpecificityScore(
                    has_entry_rules=True,
                    has_exit_rules=True,
                    has_position_sizing=True,
                    has_universe_definition=True,
                ),
                trust_score=TrustScore(
                    economic_rationale=20,
                    implementation_realism=15,
                    source_credibility=10,
                    novelty=5,
                ),
            )

            result = processor.process_file(test_file, dry_run=False)

        # Original file should be moved
        assert not test_file.exists()

        # Should be in archive/processed
        archive_files = list((workspace.archive_path / "processed").rglob("*"))
        assert len(archive_files) == 1

    def test_rejected_files_archived(self, processor, workspace):
        """Test that rejected files are moved to archive/rejected."""
        test_file = workspace.inbox_path / "bad.txt"
        test_file.write_text("Buy my course!")

        processor.llm_client = None

        # Force rejection
        with patch.object(processor, '_score_quality') as mock_score:
            from research_system.schemas.v4 import create_hard_red_flag
            mock_score.return_value = IngestionQuality(
                specificity=SpecificityScore(),
                trust_score=TrustScore(),
                red_flags=[create_hard_red_flag("author_selling")],
            )

            result = processor.process_file(test_file, dry_run=False)

        # Original file should be moved
        assert not test_file.exists()

        # Should be in archive/rejected
        archive_files = list((workspace.archive_path / "rejected").rglob("*"))
        assert len(archive_files) == 1


# =============================================================================
# TEST RESULT CLASSES
# =============================================================================


class TestResultClasses:
    """Test result data classes."""

    def test_ingest_result_to_dict(self):
        """Test IngestResult.to_dict()."""
        result = IngestResult(
            filename="test.txt",
            file_path="/path/to/test.txt",
            success=True,
            strategy_id="STRAT-001",
            strategy_name="Test Strategy",
            decision=IngestionDecision.ACCEPT,
        )

        d = result.to_dict()

        assert d["filename"] == "test.txt"
        assert d["success"] is True
        assert d["strategy_id"] == "STRAT-001"
        assert d["decision"] == "accept"

    def test_ingest_summary_to_dict(self):
        """Test IngestSummary.to_dict()."""
        summary = IngestSummary(
            total_files=5,
            processed=4,
            accepted=3,
            rejected=1,
            errors=1,
        )

        d = summary.to_dict()

        assert d["total_files"] == 5
        assert d["processed"] == 4
        assert d["accepted"] == 3
        assert d["rejected"] == 1


# =============================================================================
# TEST OFFLINE MODE
# =============================================================================


class TestOfflineMode:
    """Test offline mode (no LLM client)."""

    def test_offline_creates_minimal_strategy(self, processor, workspace):
        """Test that offline mode creates minimal strategies."""
        processor.llm_client = None

        test_file = workspace.inbox_path / "strategy.txt"
        test_file.write_text("This is a strategy document.")

        # Extract strategy directly
        content = test_file.read_text()
        strategy = processor._extract_strategy(content, test_file.name)

        assert strategy.name == "strategy"
        assert strategy.id == "PENDING"
        assert "strategy.txt" in strategy.source.reference

    def test_offline_llm_client(self, workspace, config):
        """Test processor with offline LLM client."""
        mock_client = MagicMock()
        mock_client.is_offline = True

        processor = IngestProcessor(workspace, config, mock_client)

        test_file = workspace.inbox_path / "test.txt"
        test_file.write_text("Test content")

        content = test_file.read_text()
        strategy = processor._extract_strategy(content, test_file.name)

        # Should create minimal strategy without calling LLM
        assert strategy is not None
        assert strategy.name == "test"


# =============================================================================
# TEST ATOMIC WRITES
# =============================================================================


class TestAtomicWrites:
    """Test that _save_strategy uses atomic writes (temp file + rename)."""

    def test_save_strategy_creates_valid_yaml(self, processor, workspace):
        """Test that _save_strategy produces a valid, complete YAML file."""
        from research_system.schemas.v4 import (
            Strategy, StrategyStatus, StrategyMode, StrategySource,
            Hypothesis, Universe, UniverseType,
            Entry, EntryType, TechnicalConfig,
            Position, PositionType, PositionLeg, Direction, LegInstrument,
            InstrumentSource, InstrumentAssetType,
            Exit, ExitPath, ExitType, ExitPriority,
        )
        from datetime import datetime

        strategy = Strategy(
            id="STRAT-001",
            name="Atomic Write Test Strategy",
            created=datetime.now(),
            status=StrategyStatus.PENDING,
            source=StrategySource(
                reference="test.txt",
                excerpt="Test",
                hash="abc123",
                extracted_date=datetime.now(),
            ),
            hypothesis=Hypothesis(
                summary="Test hypothesis for atomic write",
                detail="Detailed description",
            ),
            strategy_mode=StrategyMode.SIMPLE,
            universe=Universe(type=UniverseType.STATIC),
            entry=Entry(
                type=EntryType.TECHNICAL,
                technical=TechnicalConfig(
                    indicator="SMA", params={}, condition="cross"
                ),
            ),
            position=Position(
                type=PositionType.SINGLE_LEG,
                legs=[PositionLeg(
                    name="main",
                    direction=Direction.LONG,
                    instrument=LegInstrument(source=InstrumentSource.FROM_UNIVERSE),
                    asset_type=InstrumentAssetType.EQUITY,
                )],
            ),
            exit=Exit(
                paths=[ExitPath(name="exit", type=ExitType.SIGNAL_REVERSAL)],
                priority=ExitPriority.FIRST_TRIGGERED,
            ),
        )

        saved_path = processor._save_strategy(strategy)

        # File must exist
        assert saved_path.exists()

        # File must be valid YAML with the correct strategy id
        with open(saved_path) as f:
            data = yaml.safe_load(f)
        assert data["id"] == "STRAT-001"
        assert data["name"] == "Atomic Write Test Strategy"

    def test_no_tmp_files_after_successful_write(self, processor, workspace):
        """Test that no .tmp files remain after a successful save."""
        from research_system.schemas.v4 import (
            Strategy, StrategyStatus, StrategyMode, StrategySource,
            Hypothesis, Universe, UniverseType,
            Entry, EntryType, TechnicalConfig,
            Position, PositionType, PositionLeg, Direction, LegInstrument,
            InstrumentSource, InstrumentAssetType,
            Exit, ExitPath, ExitType, ExitPriority,
        )
        from datetime import datetime

        strategy = Strategy(
            id="STRAT-002",
            name="No Temp Files Test",
            created=datetime.now(),
            status=StrategyStatus.PENDING,
            source=StrategySource(
                reference="test.txt",
                excerpt="Test",
                hash="abc123",
                extracted_date=datetime.now(),
            ),
            hypothesis=Hypothesis(summary="Test", detail="Test"),
            strategy_mode=StrategyMode.SIMPLE,
            universe=Universe(type=UniverseType.STATIC),
            entry=Entry(
                type=EntryType.TECHNICAL,
                technical=TechnicalConfig(
                    indicator="SMA", params={}, condition="cross"
                ),
            ),
            position=Position(
                type=PositionType.SINGLE_LEG,
                legs=[PositionLeg(
                    name="main",
                    direction=Direction.LONG,
                    instrument=LegInstrument(source=InstrumentSource.FROM_UNIVERSE),
                    asset_type=InstrumentAssetType.EQUITY,
                )],
            ),
            exit=Exit(
                paths=[ExitPath(name="exit", type=ExitType.SIGNAL_REVERSAL)],
                priority=ExitPriority.FIRST_TRIGGERED,
            ),
        )

        saved_path = processor._save_strategy(strategy)
        pending_dir = saved_path.parent

        # No .tmp files should exist in the pending directory
        tmp_files = list(pending_dir.glob("*.yaml.tmp"))
        assert tmp_files == [], f"Leftover tmp files: {tmp_files}"

    def test_interrupt_during_write_leaves_no_partial_file(
        self, processor, workspace
    ):
        """Test that KeyboardInterrupt during yaml.dump leaves no partial file."""
        from research_system.schemas.v4 import (
            Strategy, StrategyStatus, StrategyMode, StrategySource,
            Hypothesis, Universe, UniverseType,
            Entry, EntryType, TechnicalConfig,
            Position, PositionType, PositionLeg, Direction, LegInstrument,
            InstrumentSource, InstrumentAssetType,
            Exit, ExitPath, ExitType, ExitPriority,
        )
        from datetime import datetime

        strategy = Strategy(
            id="STRAT-003",
            name="Interrupt Test Strategy",
            created=datetime.now(),
            status=StrategyStatus.PENDING,
            source=StrategySource(
                reference="test.txt",
                excerpt="Test",
                hash="abc123",
                extracted_date=datetime.now(),
            ),
            hypothesis=Hypothesis(summary="Test", detail="Test"),
            strategy_mode=StrategyMode.SIMPLE,
            universe=Universe(type=UniverseType.STATIC),
            entry=Entry(
                type=EntryType.TECHNICAL,
                technical=TechnicalConfig(
                    indicator="SMA", params={}, condition="cross"
                ),
            ),
            position=Position(
                type=PositionType.SINGLE_LEG,
                legs=[PositionLeg(
                    name="main",
                    direction=Direction.LONG,
                    instrument=LegInstrument(source=InstrumentSource.FROM_UNIVERSE),
                    asset_type=InstrumentAssetType.EQUITY,
                )],
            ),
            exit=Exit(
                paths=[ExitPath(name="exit", type=ExitType.SIGNAL_REVERSAL)],
                priority=ExitPriority.FIRST_TRIGGERED,
            ),
        )

        strategy_path = workspace.strategy_path(strategy.id, status="pending")
        pending_dir = strategy_path.parent
        pending_dir.mkdir(parents=True, exist_ok=True)

        # Mock yaml.dump to raise KeyboardInterrupt mid-write
        with patch("research_system.ingest.strategy_processor.yaml.dump",
                    side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                processor._save_strategy(strategy)

        # The final strategy file must NOT exist (write was interrupted)
        assert not strategy_path.exists(), (
            "Partial strategy file should not exist after interrupted write"
        )

        # No temp files should remain either
        tmp_files = list(pending_dir.glob("*.yaml.tmp"))
        assert tmp_files == [], f"Leftover tmp files after interrupt: {tmp_files}"
