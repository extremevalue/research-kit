"""
Ingest pipeline for the Research Validation System.

Provides two-stage processing of inbox files:
1. LLM extraction (Haiku) - extract structured metadata
2. Deterministic processing - validate, check data, create entry
"""

from research_system.ingest.processor import IngestProcessor, IngestResult
from research_system.ingest.extractor import MetadataExtractor

__all__ = ["IngestProcessor", "IngestResult", "MetadataExtractor"]
