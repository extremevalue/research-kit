"""
LLM-based metadata extraction from source files.

Uses Claude Haiku for fast, cheap extraction of structured metadata
from research documents (PDFs, HTML, Python code, markdown, etc.).
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from research_system.llm.client import LLMClient


# Extraction prompt template
EXTRACTION_SYSTEM_PROMPT = """You are a research document analyzer. Your task is to extract structured metadata from research documents about trading strategies, indicators, and market analysis.

Extract information accurately and conservatively. If something is unclear or not present, use null rather than guessing.

IMPORTANT:
- Be specific about data requirements (e.g., "spy_prices", "vix_index", "breadth_data")
- Identify the type accurately: indicator (technical signal), strategy (trading system), idea (concept to explore), learning (insight from analysis)
- Keep summaries concise but informative
- Extract any testable hypothesis if present"""

EXTRACTION_USER_PROMPT = """Analyze this research document and extract structured metadata.

Document content:
---
{content}
---

Extract the following in JSON format:
{{
  "type": "indicator|strategy|idea|learning|tool|data",
  "name": "Human-readable name (max 50 chars)",
  "summary": "One-line description (max 200 chars)",
  "hypothesis": "Testable hypothesis if applicable, null if not clear",
  "data_requirements": ["list", "of", "data_source_ids"],
  "tags": ["categorization", "tags"],
  "source_origin": "paper|blog|code|forum|book|other",
  "confidence": "high|medium|low"
}}

Guidelines for data_requirements:
- Use lowercase with underscores: "spy_prices", "vix_index", "breadth_data"
- Be specific: "mcclellan_oscillator" not just "breadth"
- Common IDs: spy_prices, qqq_prices, vix_index, treasury_yields, sector_etfs

Respond with ONLY the JSON object, no other text."""


@dataclass
class ExtractionResult:
    """Result of metadata extraction."""
    success: bool
    metadata: Optional[Dict[str, Any]] = None
    raw_response: Optional[str] = None
    error: Optional[str] = None
    confidence: str = "low"


class MetadataExtractor:
    """
    Extracts structured metadata from research documents using LLM.

    Uses Claude Haiku for speed and cost efficiency.
    """

    # Supported file extensions and their readers
    SUPPORTED_EXTENSIONS = {
        ".py": "code",
        ".txt": "text",
        ".md": "markdown",
        ".html": "html",
        ".htm": "html",
        ".pdf": "pdf",
        ".json": "json"
    }

    # Maximum content length to send to LLM
    MAX_CONTENT_LENGTH = 15000

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize the extractor.

        Args:
            llm_client: LLM client instance. If None, creates new one.
        """
        self.llm_client = llm_client

    def extract(self, file_path: Path) -> ExtractionResult:
        """
        Extract metadata from a file.

        Args:
            file_path: Path to the file to process

        Returns:
            ExtractionResult with extracted metadata or error
        """
        # Check if file type is supported
        suffix = file_path.suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            return ExtractionResult(
                success=False,
                error=f"Unsupported file type: {suffix}"
            )

        # Read file content
        try:
            content = self._read_file(file_path)
        except Exception as e:
            return ExtractionResult(
                success=False,
                error=f"Failed to read file: {str(e)}"
            )

        if not content or len(content.strip()) < 50:
            return ExtractionResult(
                success=False,
                error="File content too short or empty"
            )

        # Truncate if too long
        if len(content) > self.MAX_CONTENT_LENGTH:
            content = content[:self.MAX_CONTENT_LENGTH] + "\n\n[... content truncated ...]"

        # Extract using LLM
        return self._extract_with_llm(content, file_path.name)

    def _read_file(self, file_path: Path) -> str:
        """Read file content based on type."""
        suffix = file_path.suffix.lower()
        file_type = self.SUPPORTED_EXTENSIONS.get(suffix, "text")

        if file_type == "pdf":
            return self._read_pdf(file_path)
        elif file_type == "html":
            return self._read_html(file_path)
        else:
            # Plain text, code, markdown, json
            return file_path.read_text(encoding="utf-8", errors="replace")

    def _read_pdf(self, file_path: Path) -> str:
        """Read PDF file content."""
        try:
            # Try pypdf first
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text = []
            for page in reader.pages[:20]:  # Limit to first 20 pages
                text.append(page.extract_text() or "")
            return "\n\n".join(text)
        except ImportError:
            pass

        try:
            # Fall back to pdfplumber
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text = []
                for page in pdf.pages[:20]:
                    text.append(page.extract_text() or "")
                return "\n\n".join(text)
        except ImportError:
            pass

        # If no PDF library available, return file name only
        return f"[PDF file: {file_path.name}]\n\nNote: Install pypdf or pdfplumber to extract PDF content."

    def _read_html(self, file_path: Path) -> str:
        """Read HTML file and extract text."""
        html_content = file_path.read_text(encoding="utf-8", errors="replace")

        try:
            from html.parser import HTMLParser

            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                    self.skip_tags = {"script", "style", "meta", "link"}
                    self.current_tag = None

                def handle_starttag(self, tag, attrs):
                    self.current_tag = tag

                def handle_endtag(self, tag):
                    if tag in ("p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
                        self.text.append("\n")
                    self.current_tag = None

                def handle_data(self, data):
                    if self.current_tag not in self.skip_tags:
                        text = data.strip()
                        if text:
                            self.text.append(text + " ")

            parser = TextExtractor()
            parser.feed(html_content)
            return "".join(parser.text)

        except Exception:
            # Fall back to raw HTML
            return html_content

    def _extract_with_llm(self, content: str, filename: str) -> ExtractionResult:
        """Extract metadata using LLM."""
        if self.llm_client is None:
            # Offline mode - return structure for manual filling
            return ExtractionResult(
                success=False,
                error="LLM client not available (offline mode)",
                raw_response=None
            )

        # Call LLM
        prompt = EXTRACTION_USER_PROMPT.format(content=content)
        response = self.llm_client.generate_haiku(
            user=prompt,
            system=EXTRACTION_SYSTEM_PROMPT,
            max_tokens=1024
        )

        if response.offline:
            return ExtractionResult(
                success=False,
                error="LLM is in offline mode",
                raw_response=response.content
            )

        # Parse response
        metadata = self.llm_client.extract_json(response)

        if metadata is None:
            return ExtractionResult(
                success=False,
                error="Failed to parse JSON from LLM response",
                raw_response=response.content
            )

        # Validate required fields
        required_fields = ["type", "name"]
        missing = [f for f in required_fields if not metadata.get(f)]

        if missing:
            return ExtractionResult(
                success=False,
                error=f"Missing required fields: {missing}",
                raw_response=response.content,
                metadata=metadata
            )

        # Fallback for null/empty name - use source filename
        if not metadata.get("name") or metadata.get("name") in ("null", "None", ""):
            # Generate name from source or use placeholder
            fallback_name = filename.replace("_", " ").replace("-", " ")
            fallback_name = fallback_name.rsplit(".", 1)[0]  # Remove extension
            fallback_name = fallback_name[:50]  # Truncate to max length
            metadata["name"] = fallback_name if fallback_name else "Untitled"

        # Normalize type
        valid_types = ["indicator", "strategy", "idea", "learning", "tool", "data"]
        if metadata.get("type") not in valid_types:
            metadata["type"] = "idea"  # Default to idea if unclear

        return ExtractionResult(
            success=True,
            metadata=metadata,
            raw_response=response.content,
            confidence=metadata.get("confidence", "medium")
        )

    def extract_from_text(self, content: str, source_name: str = "unknown") -> ExtractionResult:
        """
        Extract metadata from raw text content.

        Args:
            content: Text content to analyze
            source_name: Name to identify the source

        Returns:
            ExtractionResult with extracted metadata or error
        """
        if len(content.strip()) < 50:
            return ExtractionResult(
                success=False,
                error="Content too short"
            )

        if len(content) > self.MAX_CONTENT_LENGTH:
            content = content[:self.MAX_CONTENT_LENGTH] + "\n\n[... content truncated ...]"

        return self._extract_with_llm(content, source_name)
