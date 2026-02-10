"""Integration tests for V4 workflow.

Tests the complete workflow: init → ingest → list → show → status
"""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def workspace_path(tmp_path):
    """Return temporary workspace path."""
    return tmp_path / "test_workspace"


@pytest.fixture
def sample_transcript():
    """Sample podcast transcript for ingestion."""
    return """
PODCAST TRANSCRIPT: MacroVoices Episode 412

Host: Today we're discussing a volatility breakout strategy with trader John Smith.

John Smith: Thanks for having me. I've been trading this strategy for 10 years
at my hedge fund with consistent results.

The strategy is simple: we wait for VIX to spike above 25, then buy SPY
when VIX drops back below 20. The entry signal is when VIX crosses below
the 20-day moving average of VIX.

For exits, we use a trailing stop of 5% from the highest price reached.
We also exit if VIX spikes above 30 again, which signals renewed volatility.

The position size is always 10% of portfolio per trade. We've achieved
a Sharpe ratio of about 1.2 over the past decade.

Host: What about drawdowns?

John: Our maximum drawdown was about 15% in 2020, but we recovered within
3 months. The strategy tends to work well in mean-reverting volatility
environments.

Host: Any transaction costs considerations?

John: Yes, we factor in about 5 basis points per trade for SPY. It's very
liquid so costs are minimal.
"""


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestV4Integration:
    """Full workflow integration tests."""

    def test_init_creates_workspace(self, workspace_path):
        """Test init --v4 creates proper workspace."""
        from research_system.core.v4.workspace import Workspace

        ws = Workspace(workspace_path)
        result = ws.init()

        assert result is True
        assert ws.exists
        assert (workspace_path / "research-kit.yaml").exists()
        assert (workspace_path / "inbox").is_dir()
        assert (workspace_path / "strategies" / "pending").is_dir()

    def test_ingest_processes_transcript(self, workspace_path, sample_transcript):
        """Test ingest processes transcript file."""
        from research_system.core.v4.workspace import Workspace
        from research_system.ingest.strategy_processor import IngestProcessor
        from research_system.schemas.v4.ingestion import IngestionDecision

        # Initialize workspace
        ws = Workspace(workspace_path)
        ws.init()

        # Add transcript to inbox
        transcript_file = ws.inbox_path / "podcast_transcript.txt"
        transcript_file.write_text(sample_transcript)

        # Run ingest (without LLM - offline mode creates minimal strategy)
        processor = IngestProcessor(ws, ws.config, llm_client=None)
        result = processor.process_file(transcript_file)

        # Result should exist with a decision
        assert result is not None
        # In offline mode with the sample transcript, decision should be one of these
        assert result.decision in (
            IngestionDecision.ACCEPT,
            IngestionDecision.QUEUE,
            IngestionDecision.ARCHIVE,
            IngestionDecision.REJECT,
        )

    def test_list_shows_strategies(self, workspace_path):
        """Test list shows strategies after ingestion."""
        from research_system.core.v4.workspace import Workspace

        # Initialize and add a strategy
        ws = Workspace(workspace_path)
        ws.init()

        # Create a test strategy
        strategy = {
            "id": "STRAT-001",
            "name": "Test Strategy",
            "created": "2024-01-15T10:00:00Z",
            "status": "pending",
        }
        filepath = ws.strategies_path / "pending" / "STRAT-001.yaml"
        with open(filepath, "w") as f:
            yaml.dump(strategy, f)

        # List strategies
        strategies = ws.list_strategies()

        assert len(strategies) == 1
        assert strategies[0]["id"] == "STRAT-001"
        assert strategies[0]["name"] == "Test Strategy"

    def test_show_displays_strategy(self, workspace_path):
        """Test show displays strategy details."""
        from research_system.core.v4.workspace import Workspace

        # Initialize and add a strategy
        ws = Workspace(workspace_path)
        ws.init()

        # Create a test strategy
        strategy = {
            "id": "STRAT-001",
            "name": "Test Strategy",
            "created": "2024-01-15T10:00:00Z",
            "source": {"type": "podcast", "author": "John Smith"},
            "hypothesis": {"thesis": "Volatility mean reversion works"},
        }
        filepath = ws.strategies_path / "pending" / "STRAT-001.yaml"
        with open(filepath, "w") as f:
            yaml.dump(strategy, f)

        # Get strategy
        result = ws.get_strategy("STRAT-001")

        assert result is not None
        assert result["id"] == "STRAT-001"
        assert result["source"]["author"] == "John Smith"

    def test_status_shows_counts(self, workspace_path):
        """Test status shows correct counts."""
        from research_system.core.v4.workspace import Workspace

        ws = Workspace(workspace_path)
        ws.init()

        # Add strategies in different states
        for status in ["pending", "validated"]:
            strategy = {
                "id": f"STRAT-{status.upper()[:3]}",
                "name": f"Strategy in {status}",
            }
            filepath = ws.strategies_path / status / f"STRAT-{status.upper()[:3]}.yaml"
            with open(filepath, "w") as f:
                yaml.dump(strategy, f)

        # Get status
        status_info = ws.status()

        assert status_info["strategies"]["pending"] == 1
        assert status_info["strategies"]["validated"] == 1

    def test_full_workflow(self, workspace_path, sample_transcript, capsys):
        """Test complete workflow from init to show."""
        from research_system.cli.main import (
            cmd_list,
            cmd_show,
            cmd_status,
        )
        from research_system.core.v4.workspace import Workspace

        # 1. Initialize
        ws = Workspace(workspace_path)
        ws.init()

        # 2. Add content to inbox
        transcript_file = ws.inbox_path / "podcast.txt"
        transcript_file.write_text(sample_transcript)

        # 3. Check status shows inbox file
        args = SimpleNamespace(v4_workspace=str(workspace_path))
        cmd_status(args)
        captured = capsys.readouterr()
        assert "1 file(s) ready to ingest" in captured.out

        # 4. Create a strategy manually (simulating ingestion result)
        strategy = {
            "id": "STRAT-001",
            "name": "VIX Volatility Breakout",
            "created": "2024-01-15T10:00:00Z",
            "source": {"type": "podcast", "author": "John Smith"},
            "hypothesis": {"thesis": "Buy SPY when VIX drops from spike"},
        }
        filepath = ws.strategies_path / "pending" / "STRAT-001.yaml"
        with open(filepath, "w") as f:
            yaml.dump(strategy, f)

        # 5. List strategies
        args = SimpleNamespace(
            v4_workspace=str(workspace_path),
            status=None,
            tags=None,
            format="table"
        )
        cmd_list(args)
        captured = capsys.readouterr()
        assert "STRAT-001" in captured.out
        assert "VIX Volatility Breakout" in captured.out

        # 6. Show strategy
        args = SimpleNamespace(
            strategy_id="STRAT-001",
            v4_workspace=str(workspace_path),
            format="text"
        )
        cmd_show(args)
        captured = capsys.readouterr()
        assert "STRAT-001" in captured.out
        assert "John Smith" in captured.out


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestV4IntegrationErrors:
    """Tests for error handling."""

    def test_ingest_empty_inbox(self, workspace_path):
        """Test ingest handles empty inbox."""
        from research_system.core.v4.workspace import Workspace
        from research_system.ingest.strategy_processor import IngestProcessor

        ws = Workspace(workspace_path)
        ws.init()

        processor = IngestProcessor(ws, ws.config, llm_client=None)
        summary = processor.process_inbox()

        assert summary.total_files == 0
        assert summary.accepted == 0

    def test_show_nonexistent_strategy(self, workspace_path, capsys):
        """Test show handles missing strategy."""
        from research_system.cli.main import cmd_show
        from research_system.core.v4.workspace import Workspace

        ws = Workspace(workspace_path)
        ws.init()

        args = SimpleNamespace(
            strategy_id="STRAT-999",
            v4_workspace=str(workspace_path),
            format="text"
        )

        result = cmd_show(args)
        assert result == 1

        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_list_empty_workspace(self, workspace_path, capsys):
        """Test list handles empty workspace."""
        from research_system.cli.main import cmd_list
        from research_system.core.v4.workspace import Workspace

        ws = Workspace(workspace_path)
        ws.init()

        args = SimpleNamespace(
            v4_workspace=str(workspace_path),
            status=None,
            tags=None,
            format="table"
        )

        result = cmd_list(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "No strategies" in captured.out


# =============================================================================
# DRY-RUN TESTS
# =============================================================================


class TestV4DryRun:
    """Tests for dry-run modes."""

    def test_ingest_dry_run_no_files_created(self, workspace_path, sample_transcript):
        """Test ingest dry-run doesn't create files."""
        from research_system.core.v4.workspace import Workspace
        from research_system.ingest.strategy_processor import IngestProcessor

        ws = Workspace(workspace_path)
        ws.init()

        # Add transcript
        transcript_file = ws.inbox_path / "podcast.txt"
        transcript_file.write_text(sample_transcript)

        # Run dry-run ingest
        processor = IngestProcessor(ws, ws.config, llm_client=None)
        result = processor.process_file(transcript_file, dry_run=True)

        # File should still be in inbox
        assert transcript_file.exists()

        # No strategy file should be created
        pending_files = list(ws.strategies_path.glob("pending/*.yaml"))
        assert len(pending_files) == 0
