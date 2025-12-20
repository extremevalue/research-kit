"""
Ingest processor - two-stage pipeline for processing inbox files.

Stage 1: LLM Extraction (Claude Haiku)
    - Reads raw file content
    - Extracts structured metadata: name, type, summary, data requirements, tags
    - Outputs validated JSON

Stage 2: Deterministic Processing (Python)
    - Validates extracted metadata against schema
    - Checks data requirements against registry
    - Sets status: UNTESTED (all data available) or BLOCKED (missing data)
    - Generates entry ID, writes to catalog, archives source file
"""

import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from research_system.core.workspace import Workspace
from research_system.core.catalog import Catalog
from research_system.core.data_registry import DataRegistry
from research_system.ingest.extractor import MetadataExtractor, ExtractionResult
from research_system.llm.client import LLMClient


@dataclass
class IngestResult:
    """Result of ingesting a single file."""
    filename: str
    success: bool
    entry_id: Optional[str] = None
    entry_type: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None
    skipped_reason: Optional[str] = None
    blocked_data: List[str] = field(default_factory=list)
    dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "success": self.success,
            "entry_id": self.entry_id,
            "entry_type": self.entry_type,
            "status": self.status,
            "error": self.error,
            "skipped_reason": self.skipped_reason,
            "blocked_data": self.blocked_data,
            "dry_run": self.dry_run
        }


@dataclass
class IngestSummary:
    """Summary of batch ingestion."""
    total_files: int = 0
    processed: int = 0
    skipped: int = 0
    errors: int = 0
    blocked: int = 0
    results: List[IngestResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_files": self.total_files,
            "processed": self.processed,
            "skipped": self.skipped,
            "errors": self.errors,
            "blocked": self.blocked,
            "results": [r.to_dict() for r in self.results]
        }


class IngestProcessor:
    """
    Processes inbox files into catalog entries.

    Two-stage pipeline:
    1. LLM extraction using Claude Haiku
    2. Deterministic processing (validation, data check, catalog write)
    """

    # Files to ignore in inbox
    IGNORE_PATTERNS = [".DS_Store", ".gitkeep", "*.tmp", "*.log"]

    def __init__(
        self,
        workspace: Workspace,
        llm_client: Optional[LLMClient] = None
    ):
        """
        Initialize the ingest processor.

        Args:
            workspace: Workspace instance
            llm_client: LLM client for extraction. If None, runs in offline mode.
        """
        self.workspace = workspace
        self.llm_client = llm_client
        self.catalog = Catalog(workspace.catalog_path)
        self.registry = DataRegistry(workspace.data_registry_path)
        self.extractor = MetadataExtractor(llm_client)

    def process_all(self, dry_run: bool = False) -> IngestSummary:
        """
        Process all files in inbox.

        Args:
            dry_run: If True, show what would be done without making changes

        Returns:
            IngestSummary with results for all files
        """
        summary = IngestSummary()

        # Get all files in inbox
        inbox_files = [
            f for f in self.workspace.inbox_path.iterdir()
            if f.is_file() and not self._should_ignore(f)
        ]

        summary.total_files = len(inbox_files)

        for file_path in sorted(inbox_files):
            result = self.process_file(file_path, dry_run)
            summary.results.append(result)

            if result.success:
                summary.processed += 1
                if result.status == "BLOCKED":
                    summary.blocked += 1
            elif result.skipped_reason:
                summary.skipped += 1
            else:
                summary.errors += 1

        return summary

    def process_file(self, file_path: Path, dry_run: bool = False) -> IngestResult:
        """
        Process a single file through the two-stage pipeline.

        Args:
            file_path: Path to the file to process
            dry_run: If True, don't make any changes

        Returns:
            IngestResult with processing outcome
        """
        result = IngestResult(filename=file_path.name, dry_run=dry_run)

        # Stage 1: LLM Extraction
        extraction = self.extractor.extract(file_path)

        if not extraction.success:
            result.success = False
            result.skipped_reason = extraction.error or "Extraction failed"
            return result

        metadata = extraction.metadata
        result.entry_type = metadata.get("type", "idea")

        # Stage 2: Deterministic Processing

        # Check data requirements
        data_reqs = metadata.get("data_requirements", [])
        missing_data = self._check_data_requirements(data_reqs)

        if missing_data:
            result.status = "BLOCKED"
            result.blocked_data = missing_data
        else:
            result.status = "UNTESTED"

        if dry_run:
            result.success = True
            result.entry_id = f"[DRY-RUN] Would create {result.entry_type.upper()}-XXX"
            return result

        # Create catalog entry
        try:
            entry = self._create_catalog_entry(metadata, file_path, result.status, missing_data)
            result.entry_id = entry.id
            result.success = True

            # Archive source file
            self._archive_file(file_path)

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result

    def _should_ignore(self, file_path: Path) -> bool:
        """Check if file should be ignored."""
        name = file_path.name

        for pattern in self.IGNORE_PATTERNS:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True

        return False

    def _check_data_requirements(self, data_reqs: List[str]) -> List[str]:
        """
        Check which data requirements are not available.

        Returns list of missing data source IDs.
        """
        missing = []

        for req in data_reqs:
            if not req:
                continue

            # Normalize ID
            req = req.lower().replace("-", "_").replace(" ", "_")

            # Check registry
            source = self.registry.get(req)
            if source is None or not source.is_available():
                missing.append(req)

        return missing

    def _create_catalog_entry(
        self,
        metadata: Dict[str, Any],
        source_file: Path,
        status: str,
        missing_data: List[str]
    ):
        """Create catalog entry from extracted metadata."""
        # Build entry data
        entry_type = metadata.get("type", "idea")
        name = metadata.get("name", source_file.stem)[:100]  # Limit name length

        # Prepare source info
        archive_path = self.workspace.archive_path / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{source_file.name}"

        entry = self.catalog.add(
            entry_type=entry_type,
            name=name,
            source_files=[str(archive_path.relative_to(self.workspace.path))],
            summary=metadata.get("summary"),
            hypothesis=metadata.get("hypothesis"),
            tags=metadata.get("tags", [])
        )

        # If blocked, add blocked reason
        if status == "BLOCKED" and missing_data:
            self.catalog.update_status(
                entry.id,
                "BLOCKED",
                blocked_reason=f"Missing data: {', '.join(missing_data)}"
            )

        return entry

    def _archive_file(self, file_path: Path):
        """Move file to archive with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{timestamp}_{file_path.name}"
        archive_path = self.workspace.archive_path / archive_name

        # Ensure archive directory exists
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        # Move file
        shutil.move(str(file_path), str(archive_path))

    def process_text(
        self,
        content: str,
        source_name: str,
        dry_run: bool = False
    ) -> IngestResult:
        """
        Process raw text content (not from a file).

        Useful for programmatic ingestion from APIs, web scraping, etc.

        Args:
            content: Text content to process
            source_name: Name to identify the source
            dry_run: If True, don't make any changes

        Returns:
            IngestResult with processing outcome
        """
        result = IngestResult(filename=source_name, dry_run=dry_run)

        # Stage 1: LLM Extraction
        extraction = self.extractor.extract_from_text(content, source_name)

        if not extraction.success:
            result.success = False
            result.skipped_reason = extraction.error or "Extraction failed"
            return result

        metadata = extraction.metadata
        result.entry_type = metadata.get("type", "idea")

        # Stage 2: Deterministic Processing
        data_reqs = metadata.get("data_requirements", [])
        missing_data = self._check_data_requirements(data_reqs)

        if missing_data:
            result.status = "BLOCKED"
            result.blocked_data = missing_data
        else:
            result.status = "UNTESTED"

        if dry_run:
            result.success = True
            result.entry_id = f"[DRY-RUN] Would create {result.entry_type.upper()}-XXX"
            return result

        # Create catalog entry (no file to archive)
        try:
            entry_type = metadata.get("type", "idea")
            name = metadata.get("name", source_name)[:100]

            entry = self.catalog.add(
                entry_type=entry_type,
                name=name,
                source_files=[f"text:{source_name}"],
                summary=metadata.get("summary"),
                hypothesis=metadata.get("hypothesis"),
                tags=metadata.get("tags", [])
            )

            result.entry_id = entry.id
            result.success = True

            if result.status == "BLOCKED" and missing_data:
                self.catalog.update_status(
                    entry.id,
                    "BLOCKED",
                    blocked_reason=f"Missing data: {', '.join(missing_data)}"
                )

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result
