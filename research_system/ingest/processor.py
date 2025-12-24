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
    - Generates entry ID, writes to catalog
    - Moves source file to catalog/sources/ (if entry created) or reviewed/ (if skipped)
"""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
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
    relative_path: str = ""  # Path relative to inbox
    success: bool = False
    entry_id: Optional[str] = None
    entry_type: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None
    skipped_reason: Optional[str] = None
    blocked_data: List[str] = field(default_factory=list)
    content_hash: Optional[str] = None  # SHA-256 hash of file content
    destination: Optional[str] = None  # Where file was moved (sources/ or reviewed/)
    dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "relative_path": self.relative_path,
            "success": self.success,
            "entry_id": self.entry_id,
            "entry_type": self.entry_type,
            "status": self.status,
            "error": self.error,
            "skipped_reason": self.skipped_reason,
            "blocked_data": self.blocked_data,
            "content_hash": self.content_hash,
            "destination": self.destination,
            "dry_run": self.dry_run
        }


@dataclass
class IngestSummary:
    """Summary of batch ingestion."""
    total_files: int = 0
    processed: int = 0
    skipped: int = 0
    duplicates: int = 0  # Files with same content as already processed
    errors: int = 0
    blocked: int = 0
    results: List[IngestResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_files": self.total_files,
            "processed": self.processed,
            "skipped": self.skipped,
            "duplicates": self.duplicates,
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

    Features:
    - Content hashing to detect duplicate files
    - Preserves subdirectory structure from inbox
    - Moves files to catalog/sources/ (if entry created) or reviewed/ (if skipped)
    - Auto-recognition of QuantConnect Native data sources
    """

    # Files to ignore in inbox
    IGNORE_PATTERNS = [".DS_Store", ".gitkeep", "*.tmp", "*.log"]

    # Patterns that indicate standard market data available in QuantConnect
    # These don't need explicit registry entries - QC has comprehensive coverage
    # for equities, ETFs, futures, options, crypto, forex, etc.
    QC_STANDARD_DATA_SUFFIXES = {"_prices", "_data", "_ohlcv"}

    # Special data sources that are always available in QuantConnect
    QC_NATIVE_SPECIAL = {
        "risk_free_rate",      # Available via RiskFreeInterestRateModel
        "treasury_yields",     # Available via FRED data
        "options_data",        # QC has comprehensive options data
        "futures_data",        # QC has comprehensive futures data
        "forex_data",          # QC has forex data
        "crypto_data",         # QC has crypto data
    }

    # Hash index file for tracking processed content
    HASH_INDEX_FILE = "processed_hashes.json"

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
        self._processed_hashes: Optional[Dict[str, str]] = None  # hash -> entry_id

    def _get_hash_index_path(self) -> Path:
        """Get path to the hash index file."""
        return self.workspace.work_path / self.HASH_INDEX_FILE

    def _load_processed_hashes(self) -> Dict[str, str]:
        """Load the index of already processed content hashes."""
        if self._processed_hashes is not None:
            return self._processed_hashes

        hash_file = self._get_hash_index_path()
        if hash_file.exists():
            try:
                with open(hash_file, 'r') as f:
                    self._processed_hashes = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._processed_hashes = {}
        else:
            self._processed_hashes = {}

        return self._processed_hashes

    def _save_processed_hash(self, content_hash: str, entry_id: str):
        """Save a new hash to the index."""
        hashes = self._load_processed_hashes()
        hashes[content_hash] = entry_id

        hash_file = self._get_hash_index_path()
        hash_file.parent.mkdir(parents=True, exist_ok=True)
        with open(hash_file, 'w') as f:
            json.dump(hashes, f, indent=2)

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _get_relative_path(self, file_path: Path) -> str:
        """Get path relative to inbox, preserving subdirectory structure."""
        try:
            return str(file_path.relative_to(self.workspace.inbox_path))
        except ValueError:
            return file_path.name

    def process_all(self, dry_run: bool = False) -> IngestSummary:
        """
        Process all files in inbox.

        Args:
            dry_run: If True, show what would be done without making changes

        Returns:
            IngestSummary with results for all files
        """
        summary = IngestSummary()

        # Get all files in inbox (recursive), tracking by full path
        inbox_files = [
            f for f in self.workspace.inbox_path.rglob("*")
            if f.is_file() and not self._should_ignore(f)
        ]

        summary.total_files = len(inbox_files)

        # Load known hashes to detect duplicates
        known_hashes = self._load_processed_hashes()

        for file_path in sorted(inbox_files):
            result = self.process_file(file_path, dry_run, known_hashes)
            summary.results.append(result)

            if result.skipped_reason and "duplicate" in result.skipped_reason.lower():
                summary.duplicates += 1
            elif result.success:
                summary.processed += 1
                if result.status == "BLOCKED":
                    summary.blocked += 1
            elif result.skipped_reason:
                summary.skipped += 1
            else:
                summary.errors += 1

        return summary

    def process_file(
        self,
        file_path: Path,
        dry_run: bool = False,
        known_hashes: Optional[Dict[str, str]] = None
    ) -> IngestResult:
        """
        Process a single file through the two-stage pipeline.

        Args:
            file_path: Path to the file to process
            dry_run: If True, don't make any changes
            known_hashes: Optional dict of content_hash -> entry_id for duplicate detection

        Returns:
            IngestResult with processing outcome
        """
        relative_path = self._get_relative_path(file_path)
        result = IngestResult(
            filename=file_path.name,
            relative_path=relative_path,
            dry_run=dry_run
        )

        # Compute content hash for duplicate detection
        try:
            content_hash = self.compute_file_hash(file_path)
            result.content_hash = content_hash
        except IOError as e:
            result.success = False
            result.error = f"Cannot read file: {e}"
            return result

        # Check for duplicate content
        if known_hashes is None:
            known_hashes = self._load_processed_hashes()

        if content_hash in known_hashes:
            existing_entry = known_hashes[content_hash]
            result.skipped_reason = f"Duplicate content (same as {existing_entry})"
            # Move duplicate to reviewed/
            if not dry_run:
                self._move_to_reviewed(file_path, content_hash)
                result.destination = "reviewed"
            return result

        # Stage 1: LLM Extraction
        extraction = self.extractor.extract(file_path)

        if not extraction.success:
            result.success = False
            result.skipped_reason = extraction.error or "Extraction failed"
            # Move failed extractions to reviewed/
            if not dry_run:
                self._move_to_reviewed(file_path, content_hash)
                result.destination = "reviewed"
            return result

        metadata = extraction.metadata
        result.entry_type = metadata.get("type", "idea")

        # Stage 2: Deterministic Processing

        # Check data requirements
        data_reqs = metadata.get("data_requirements") or []
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
            entry = self._create_catalog_entry(metadata, file_path, result.status, missing_data, content_hash)
            result.entry_id = entry.id
            result.success = True

            # Move source file to catalog/sources/
            self._move_to_sources(file_path, content_hash)
            result.destination = "catalog/sources"

            # Record hash for future duplicate detection
            self._save_processed_hash(content_hash, entry.id)

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

    def _is_qc_native_data(self, req: str) -> bool:
        """
        Check if a data requirement is available as QC Native data.

        QuantConnect provides comprehensive market data coverage including:
        - All US equities and ETFs
        - International equities
        - Futures, options, forex, crypto

        Rather than maintaining a whitelist, we assume standard market data
        patterns ({ticker}_prices, {ticker}_data) are available. The registry
        is only needed for specialized/custom data sources.

        Args:
            req: Normalized data requirement ID (lowercase, underscores)

        Returns:
            True if likely available as QC Native data
        """
        # Check special data sources first
        if req in self.QC_NATIVE_SPECIAL:
            return True

        # Check for standard market data patterns: {ticker}_prices, {ticker}_data, etc.
        # Any ticker followed by a standard suffix is assumed available in QC
        for suffix in self.QC_STANDARD_DATA_SUFFIXES:
            if req.endswith(suffix):
                ticker = req[:-len(suffix)]
                # Basic validation: ticker should be 1-6 alphanumeric chars
                # (covers stocks, ETFs, futures symbols, crypto pairs, etc.)
                if ticker and len(ticker) <= 6 and ticker.replace("_", "").isalnum():
                    return True

        return False

    def _check_data_requirements(self, data_reqs: List[str]) -> List[str]:
        """
        Check which data requirements are not available.

        Checks in order:
        1. Explicit registry entries
        2. Auto-recognized QC Native symbols (e.g., spy_prices, gld_prices)

        Returns list of missing data source IDs.
        """
        missing = []

        for req in data_reqs:
            if not req:
                continue

            # Normalize ID
            req = req.lower().replace("-", "_").replace(" ", "_")

            # Check registry first
            source = self.registry.get(req)
            if source is not None and source.is_available():
                continue

            # Check if it's a recognized QC Native data source
            if self._is_qc_native_data(req):
                continue

            # Not found in registry and not recognized as QC Native
            missing.append(req)

        return missing

    def _create_catalog_entry(
        self,
        metadata: Dict[str, Any],
        source_file: Path,
        status: str,
        missing_data: List[str],
        content_hash: str
    ):
        """Create catalog entry from extracted metadata."""
        # Build entry data
        entry_type = metadata.get("type", "idea")
        name = metadata.get("name", source_file.stem)[:100]  # Limit name length

        # Prepare source info - will be in catalog/sources/ with preserved subdirs
        relative_path = self._get_relative_path(source_file)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_prefix = content_hash[:8]

        # Preserve subdirectory structure
        if "/" in relative_path or "\\" in relative_path:
            subdir = str(Path(relative_path).parent)
            filename = f"{timestamp}_{hash_prefix}_{source_file.name}"
            sources_path = self.workspace.sources_path / subdir / filename
        else:
            filename = f"{timestamp}_{hash_prefix}_{source_file.name}"
            sources_path = self.workspace.sources_path / filename

        entry = self.catalog.add(
            entry_type=entry_type,
            name=name,
            source_files=[str(sources_path.relative_to(self.workspace.path))],
            summary=metadata.get("summary"),
            hypothesis=metadata.get("hypothesis"),
            tags=metadata.get("tags") or []
        )

        # If blocked, add blocked reason
        if status == "BLOCKED" and missing_data:
            self.catalog.update_status(
                entry.id,
                "BLOCKED",
                blocked_reason=f"Missing data: {', '.join(missing_data)}"
            )

        return entry

    def _move_to_sources(self, file_path: Path, content_hash: str):
        """Move file to catalog/sources/ with preserved subdirectory structure."""
        relative_path = self._get_relative_path(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_prefix = content_hash[:8]

        # Preserve subdirectory structure
        if "/" in relative_path or "\\" in relative_path:
            subdir = str(Path(relative_path).parent)
            filename = f"{timestamp}_{hash_prefix}_{file_path.name}"
            dest_path = self.workspace.sources_path / subdir / filename
        else:
            filename = f"{timestamp}_{hash_prefix}_{file_path.name}"
            dest_path = self.workspace.sources_path / filename

        # Ensure directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Move file
        shutil.move(str(file_path), str(dest_path))

    def _move_to_reviewed(self, file_path: Path, content_hash: str):
        """Move file to reviewed/ with preserved subdirectory structure."""
        relative_path = self._get_relative_path(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_prefix = content_hash[:8]

        # Preserve subdirectory structure
        if "/" in relative_path or "\\" in relative_path:
            subdir = str(Path(relative_path).parent)
            filename = f"{timestamp}_{hash_prefix}_{file_path.name}"
            dest_path = self.workspace.reviewed_path / subdir / filename
        else:
            filename = f"{timestamp}_{hash_prefix}_{file_path.name}"
            dest_path = self.workspace.reviewed_path / filename

        # Ensure directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Move file
        shutil.move(str(file_path), str(dest_path))

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
        data_reqs = metadata.get("data_requirements") or []
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
                tags=metadata.get("tags") or []
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
