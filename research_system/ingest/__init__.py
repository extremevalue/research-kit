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
from research_system.ingest.v4_processor import (
    V4IngestProcessor,
    V4IngestResult,
    V4IngestSummary,
)

__all__ = [
    "IngestProcessor",
    "IngestResult",
    "MetadataExtractor",
    # V4
    "V4IngestProcessor",
    "V4IngestResult",
    "V4IngestSummary",
]
