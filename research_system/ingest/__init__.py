"""
Ingest pipeline for the Research Validation System.

Provides two-stage processing of inbox files:
1. LLM extraction (Haiku) - extract structured metadata
2. Deterministic processing - validate, check data, create entry

V4 Ingest:
- V4IngestProcessor - Process inbox files into V4 strategy documents
- V4IngestResult - Result of processing a single file
- V4IngestSummary - Summary of batch ingestion
"""

from research_system.ingest.processor import IngestProcessor, IngestResult
from research_system.ingest.extractor import MetadataExtractor
from research_system.ingest.strategy_processor import (
    V4IngestProcessor,
    V4IngestResult,
    V4IngestSummary,
)

# New clean aliases for V4 processor (legacy IngestProcessor/IngestResult remain from processor.py)
StrategyIngestProcessor = V4IngestProcessor
StrategyIngestResult = V4IngestResult
StrategyIngestSummary = V4IngestSummary

__all__ = [
    "IngestProcessor",
    "IngestResult",
    "MetadataExtractor",
    # V4 (backward-compat)
    "V4IngestProcessor",
    "V4IngestResult",
    "V4IngestSummary",
    # New clean aliases
    "StrategyIngestProcessor",
    "StrategyIngestResult",
    "StrategyIngestSummary",
]
