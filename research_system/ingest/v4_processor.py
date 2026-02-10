"""Backward-compat redirect — use strategy_processor instead."""
from research_system.ingest.strategy_processor import *  # noqa: F401,F403
from research_system.ingest.strategy_processor import (
    IngestResult,
    IngestSummary,
    IngestProcessor,
    V4IngestResult,
    V4IngestSummary,
    V4IngestProcessor,
)
