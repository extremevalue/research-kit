"""V4 Ingest Processor - Process inbox files into V4 strategy documents.

This module provides the V4IngestProcessor class that:
1. Uses LLM to extract strategy metadata from files
2. Creates V4Strategy documents
3. Runs ingestion quality scoring (specificity, trust, red flags)
4. Saves strategies to workspace/strategies/pending/
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from research_system.core.v4 import V4Config, V4Workspace
from research_system.llm.client import LLMClient
from research_system.schemas.v4 import (
    # Strategy models
    V4Strategy,
    StrategyStatus,
    StrategyMode,
    StrategySource,
    SourceCredibility,
    SourceType,
    AuthorTrackRecord,
    Hypothesis,
    StrategyEdge,
    EdgeCategory,
    Universe,
    UniverseType,
    StaticInstrument,
    InstrumentAssetType,
    Entry,
    EntryType,
    TechnicalConfig,
    Position,
    PositionType,
    PositionLeg,
    Direction,
    LegInstrument,
    InstrumentSource,
    PositionSizing,
    SizingMethod,
    Exit,
    ExitPath,
    ExitType,
    ExitPriority,
    DataRequirements,
    PriceDataRequirement,
    PriceDataType,
    Assumption,
    AssumptionCategory,
    Risk,
    RiskCategory,
    RiskSeverity,
    StrategyTags,
    HypothesisType,
    AssetClass,
    Complexity,
    # Ingestion models
    IngestionQuality,
    IngestionDecision,
    SpecificityScore,
    TrustScore,
    RedFlag,
    RedFlagSeverity,
    HARD_RED_FLAGS,
    SOFT_RED_FLAGS,
    create_hard_red_flag,
    create_soft_red_flag,
)


# =============================================================================
# CONSTANTS
# =============================================================================

# Files to ignore during processing
IGNORE_PATTERNS = [".DS_Store", ".gitkeep", "*.tmp", "*.log", "*.pyc", "__pycache__"]

# Maximum retries for LLM calls
MAX_LLM_RETRIES = 3


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class V4IngestResult:
    """Result of processing a single file."""

    filename: str
    file_path: str = ""
    success: bool = False
    strategy_id: str | None = None
    strategy_name: str | None = None
    quality: IngestionQuality | None = None
    decision: IngestionDecision | None = None
    error: str | None = None
    saved_path: str | None = None
    dry_run: bool = False
    content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "filename": self.filename,
            "file_path": self.file_path,
            "success": self.success,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "decision": self.decision.value if self.decision else None,
            "specificity_score": self.quality.specificity.score if self.quality else None,
            "trust_score": self.quality.trust_score.total if self.quality else None,
            "error": self.error,
            "saved_path": self.saved_path,
            "dry_run": self.dry_run,
        }


@dataclass
class V4IngestSummary:
    """Summary of batch ingestion."""

    total_files: int = 0
    processed: int = 0
    accepted: int = 0
    queued: int = 0
    archived: int = 0
    rejected: int = 0
    errors: int = 0
    results: list[V4IngestResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_files": self.total_files,
            "processed": self.processed,
            "accepted": self.accepted,
            "queued": self.queued,
            "archived": self.archived,
            "rejected": self.rejected,
            "errors": self.errors,
            "results": [r.to_dict() for r in self.results],
        }


# =============================================================================
# LLM EXTRACTION PROMPT
# =============================================================================

STRATEGY_EXTRACTION_SYSTEM_PROMPT = """You are a trading strategy analyst extracting structured information from documents.

Your task is to extract strategy details from the provided document and return them in a specific JSON format.
Be thorough but also acknowledge when information is not present - use null for missing fields.

IMPORTANT GUIDELINES:
1. Extract ONLY what is explicitly stated or can be directly inferred
2. Do NOT invent or hallucinate details not in the source
3. For numeric values, extract exact numbers when given
4. For entry/exit rules, extract the specific conditions mentioned
5. If the document is vague about something, mark it as null
6. Focus on actionable, testable strategy components

Return a JSON object with this structure:
{
    "name": "Strategy name (max 100 chars)",
    "hypothesis": {
        "summary": "One-line description (max 200 chars)",
        "detail": "Full explanation of how the strategy works",
        "edge_mechanism": "What drives returns",
        "edge_category": "structural|behavioral|informational|risk_premium|other",
        "why_exists": "Economic rationale for the edge",
        "counterparty": "Who is on the other side of the trade",
        "why_persists": "Why hasn't this been arbitraged away",
        "decay_conditions": "When/why will this edge stop working"
    },
    "source": {
        "type": "academic|podcast|blog|practitioner|personal",
        "author_track_record": "verified_fund_manager|academic|retail_verified|retail_unverified|unknown",
        "author_skin_in_game": true/false,
        "author_conflicts": "Description of conflicts or null"
    },
    "universe": {
        "type": "static|filtered|research_derived|signal_derived",
        "instruments": ["symbol1", "symbol2"] or null,
        "description": "Description of the trading universe"
    },
    "entry": {
        "type": "technical|event_driven|statistical|fundamental|alternative_data|compound",
        "rules": ["Entry rule 1", "Entry rule 2"],
        "indicators": ["Indicator1", "Indicator2"],
        "conditions": "Human-readable entry conditions"
    },
    "exit": {
        "rules": ["Exit rule 1", "Exit rule 2"],
        "stop_loss": "Stop loss description or null",
        "take_profit": "Take profit description or null",
        "time_based": "Time-based exit or null"
    },
    "position_sizing": {
        "method": "equal_weight|volatility_adjusted|risk_parity|kelly|fixed_fractional|custom",
        "description": "Position sizing description"
    },
    "data_requirements": ["price_data", "volume_data", "options_data", etc],
    "assumptions": [
        {"category": "market|data|execution|model", "assumption": "...", "impact_if_wrong": "..."}
    ],
    "risks": [
        {"category": "market|liquidity|execution|model|data|operational|regulatory", "risk": "...", "severity": "low|medium|high", "mitigation": "..."}
    ],
    "tags": {
        "hypothesis_types": ["trend_following", "mean_reversion", "momentum", "volatility", "event_driven", "statistical_arbitrage", "income", "relative_value", "regime_adaptive"],
        "asset_classes": ["equity", "fx", "options", "futures", "crypto", "multi_asset", "etf"],
        "complexity": "simple|moderate|complex"
    },
    "claimed_performance": {
        "sharpe": number or null,
        "cagr": number or null,
        "max_drawdown": number or null,
        "sample_period": "description or null",
        "is_out_of_sample": true/false/null
    },
    "red_flags": {
        "detected": ["flag_id1", "flag_id2"],
        "notes": "Any concerning patterns observed"
    }
}

IMPORTANT: Return ONLY valid JSON. No markdown, no explanation, just the JSON object."""


STRATEGY_EXTRACTION_USER_PROMPT = """Extract strategy details from this document.

Filename: {filename}

Content:
---
{content}
---

Return ONLY the JSON object with extracted strategy details."""


# =============================================================================
# V4 INGEST PROCESSOR
# =============================================================================


class V4IngestProcessor:
    """Process inbox files into V4 strategy documents.

    This processor:
    1. Reads files from the workspace inbox
    2. Uses LLM to extract strategy metadata
    3. Scores the extraction for quality (specificity, trust)
    4. Checks for red flags
    5. Creates V4Strategy documents in strategies/pending/
    """

    def __init__(
        self,
        workspace: V4Workspace,
        config: V4Config,
        llm_client: LLMClient | None = None,
    ):
        """Initialize the V4 ingest processor.

        Args:
            workspace: V4 workspace instance
            config: V4 configuration
            llm_client: LLM client for extraction. If None, runs in offline mode.
        """
        self.workspace = workspace
        self.config = config
        self.llm_client = llm_client

    def process_inbox(self, dry_run: bool = False) -> V4IngestSummary:
        """Process all files in the inbox directory.

        Args:
            dry_run: If True, show what would happen without saving files.

        Returns:
            V4IngestSummary with results for all files.
        """
        summary = V4IngestSummary()

        # Get all files in inbox (recursive)
        inbox_files = [
            f
            for f in self.workspace.inbox_path.rglob("*")
            if f.is_file() and not self._should_ignore(f)
        ]

        summary.total_files = len(inbox_files)

        for file_path in sorted(inbox_files):
            result = self.process_file(file_path, dry_run=dry_run)
            summary.results.append(result)

            if result.error:
                summary.errors += 1
            elif result.decision:
                summary.processed += 1
                if result.decision == IngestionDecision.ACCEPT:
                    summary.accepted += 1
                elif result.decision == IngestionDecision.QUEUE:
                    summary.queued += 1
                elif result.decision == IngestionDecision.ARCHIVE:
                    summary.archived += 1
                elif result.decision == IngestionDecision.REJECT:
                    summary.rejected += 1

        return summary

    def process_file(
        self, file_path: Path, dry_run: bool = False
    ) -> V4IngestResult:
        """Process a single file into a V4 strategy.

        Args:
            file_path: Path to the file to process.
            dry_run: If True, don't save the strategy or move files.

        Returns:
            V4IngestResult with processing outcome.
        """
        result = V4IngestResult(
            filename=file_path.name,
            file_path=str(file_path),
            dry_run=dry_run,
        )

        # Read file content
        try:
            content = self._read_file_content(file_path)
            result.content_hash = self._compute_hash(content)
        except Exception as e:
            result.error = f"Failed to read file: {e}"
            return result

        # Extract strategy using LLM
        try:
            strategy = self._extract_strategy(content, file_path.name)
        except Exception as e:
            result.error = f"Failed to extract strategy: {e}"
            return result

        result.strategy_name = strategy.name

        # Score the extraction quality
        try:
            quality = self._score_quality(strategy, content)
            result.quality = quality
        except Exception as e:
            result.error = f"Failed to score quality: {e}"
            return result

        # Compute decision based on quality scores
        decision = quality.compute_decision(
            specificity_threshold=self.config.ingestion.min_specificity_score,
            trust_threshold=self.config.ingestion.min_trust_score,
        )
        result.decision = decision

        # Handle based on decision
        if decision == IngestionDecision.REJECT:
            result.success = False
            result.error = quality.rejection_reason
            if not dry_run:
                self._archive_file(file_path, "rejected")
            return result

        if decision == IngestionDecision.ARCHIVE:
            result.success = False
            result.error = quality.rejection_reason
            if not dry_run:
                self._archive_file(file_path, "archived")
            return result

        # Accept or Queue - save the strategy
        if dry_run:
            result.success = True
            result.strategy_id = "[DRY-RUN] Would create STRAT-XXX"
            return result

        # Generate strategy ID and save
        try:
            strategy_id = self.workspace.next_strategy_id()
            strategy.id = strategy_id
            result.strategy_id = strategy_id

            saved_path = self._save_strategy(strategy)
            result.saved_path = str(saved_path)
            result.success = True

            # Move processed file to archive
            self._archive_file(file_path, "processed")

        except Exception as e:
            result.error = f"Failed to save strategy: {e}"
            result.success = False

        return result

    def _should_ignore(self, file_path: Path) -> bool:
        """Check if a file should be ignored."""
        name = file_path.name

        # Ignore hidden files (starting with .)
        if name.startswith("."):
            return True

        for pattern in IGNORE_PATTERNS:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
            elif pattern in str(file_path):
                return True

        return False

    def _read_file_content(self, file_path: Path) -> str:
        """Read file content, handling different file types."""
        suffix = file_path.suffix.lower()

        # Text-based files
        if suffix in {".txt", ".md", ".rst", ".py", ".json", ".yaml", ".yml"}:
            return file_path.read_text(encoding="utf-8", errors="replace")

        # PDF files - would need pdfplumber or similar
        if suffix == ".pdf":
            try:
                import pdfplumber

                text_parts = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                return "\n\n".join(text_parts)
            except ImportError:
                return file_path.read_text(encoding="utf-8", errors="replace")

        # Default: try reading as text
        return file_path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _compute_hash(content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    def _extract_strategy(self, content: str, filename: str) -> V4Strategy:
        """Use LLM to extract strategy from content.

        Args:
            content: File content to analyze.
            filename: Name of the source file.

        Returns:
            V4Strategy with extracted metadata.
        """
        if self.llm_client is None or self.llm_client.is_offline:
            # Offline mode - return minimal strategy
            return self._create_minimal_strategy(content, filename)

        # Prepare prompt
        user_prompt = STRATEGY_EXTRACTION_USER_PROMPT.format(
            filename=filename,
            content=content[:50000],  # Limit content length
        )

        # Call LLM with retries
        last_error = None
        for attempt in range(MAX_LLM_RETRIES):
            try:
                response = self.llm_client.generate_sonnet(
                    user=user_prompt,
                    system=STRATEGY_EXTRACTION_SYSTEM_PROMPT,
                    max_tokens=8000,
                )

                if response.offline:
                    return self._create_minimal_strategy(content, filename)

                # Parse JSON response
                extracted = self.llm_client.extract_json(response)
                if extracted:
                    return self._build_strategy_from_extraction(
                        extracted, content, filename
                    )

                # If JSON parsing failed, try again
                last_error = "Failed to parse JSON from LLM response"

            except Exception as e:
                last_error = str(e)

        # All retries failed - return minimal strategy
        return self._create_minimal_strategy(content, filename, error=last_error)

    def _create_minimal_strategy(
        self, content: str, filename: str, error: str | None = None
    ) -> V4Strategy:
        """Create a minimal strategy when LLM extraction fails."""
        now = datetime.now()
        content_hash = self._compute_hash(content)

        # Try to extract a name from the filename
        name = filename.rsplit(".", 1)[0][:100]
        if not name:
            name = "Untitled Strategy"

        # Add error note if present
        detail = f"Automatically extracted from {filename}."
        if error:
            detail += f" (Extraction error: {error})"

        # Create minimal entry, position, exit for simple mode validation
        minimal_entry = Entry(
            type=EntryType.TECHNICAL,
            technical=TechnicalConfig(
                indicator="unknown",
                params={},
                condition="To be determined from source",
            ),
        )

        minimal_position = Position(
            type=PositionType.SINGLE_LEG,
            legs=[
                PositionLeg(
                    name="main",
                    direction=Direction.LONG,
                    instrument=LegInstrument(source=InstrumentSource.FROM_UNIVERSE),
                    asset_type=InstrumentAssetType.EQUITY,
                )
            ],
        )

        minimal_exit = Exit(
            paths=[
                ExitPath(
                    name="default_exit",
                    type=ExitType.SIGNAL_REVERSAL,
                    condition_description="Exit when entry conditions no longer hold",
                )
            ],
            priority=ExitPriority.FIRST_TRIGGERED,
        )

        return V4Strategy(
            id="PENDING",  # Will be assigned later
            name=name,
            created=now,
            status=StrategyStatus.PENDING,
            source=StrategySource(
                reference=filename,
                excerpt=content[:500] + "..." if len(content) > 500 else content,
                hash=content_hash,
                extracted_date=now,
            ),
            hypothesis=Hypothesis(
                summary=f"Strategy from {filename}",
                detail=detail,
            ),
            strategy_mode=StrategyMode.SIMPLE,
            universe=Universe(type=UniverseType.STATIC),
            entry=minimal_entry,
            position=minimal_position,
            exit=minimal_exit,
        )

    def _build_strategy_from_extraction(
        self, extracted: dict[str, Any], content: str, filename: str
    ) -> V4Strategy:
        """Build V4Strategy from LLM extraction results."""
        now = datetime.now()
        content_hash = self._compute_hash(content)

        # Extract hypothesis
        hyp_data = extracted.get("hypothesis", {})
        edge = None
        if hyp_data.get("edge_mechanism"):
            edge = StrategyEdge(
                mechanism=hyp_data.get("edge_mechanism", "Unknown"),
                category=self._parse_edge_category(hyp_data.get("edge_category")),
                why_exists=hyp_data.get("why_exists", "Not specified"),
                counterparty=hyp_data.get("counterparty", "Unknown"),
                why_persists=hyp_data.get("why_persists", "Not specified"),
                decay_conditions=hyp_data.get("decay_conditions", "Unknown"),
            )

        hypothesis = Hypothesis(
            summary=hyp_data.get("summary", f"Strategy from {filename}")[:200],
            detail=hyp_data.get("detail", f"Extracted from {filename}"),
            edge=edge,
        )

        # Extract source credibility
        src_data = extracted.get("source", {})
        credibility = None
        if src_data:
            credibility = SourceCredibility(
                source_type=self._parse_source_type(src_data.get("type")),
                author_track_record=self._parse_track_record(
                    src_data.get("author_track_record")
                ),
                author_skin_in_game=src_data.get("author_skin_in_game", False),
                author_conflicts=src_data.get("author_conflicts"),
            )

        source = StrategySource(
            reference=filename,
            excerpt=content[:1000] + "..." if len(content) > 1000 else content,
            hash=content_hash,
            extracted_date=now,
            credibility=credibility,
        )

        # Extract universe
        univ_data = extracted.get("universe", {})
        universe = self._build_universe(univ_data)

        # Extract entry
        entry_data = extracted.get("entry", {})
        entry = self._build_entry(entry_data) if entry_data.get("rules") else None

        # Extract position
        sizing_data = extracted.get("position_sizing", {})
        position = self._build_position(sizing_data) if sizing_data else None

        # Extract exit
        exit_data = extracted.get("exit", {})
        exit = self._build_exit(exit_data) if exit_data.get("rules") else None

        # Extract data requirements
        data_reqs = self._build_data_requirements(
            extracted.get("data_requirements", [])
        )

        # Extract assumptions
        assumptions = [
            Assumption(
                category=self._parse_assumption_category(a.get("category")),
                assumption=a.get("assumption", "Unknown"),
                impact_if_wrong=a.get("impact_if_wrong", "Unknown"),
            )
            for a in extracted.get("assumptions", [])
            if a.get("assumption")
        ]

        # Extract risks
        risks = [
            Risk(
                category=self._parse_risk_category(r.get("category")),
                risk=r.get("risk", "Unknown"),
                severity=self._parse_risk_severity(r.get("severity")),
                mitigation=r.get("mitigation", "Not specified"),
            )
            for r in extracted.get("risks", [])
            if r.get("risk")
        ]

        # Extract tags
        tags_data = extracted.get("tags", {})
        tags = StrategyTags(
            hypothesis_type=[
                self._parse_hypothesis_type(t)
                for t in tags_data.get("hypothesis_types", [])
                if self._parse_hypothesis_type(t)
            ],
            asset_class=[
                self._parse_asset_class(a)
                for a in tags_data.get("asset_classes", [])
                if self._parse_asset_class(a)
            ],
            complexity=self._parse_complexity(tags_data.get("complexity")),
        )

        return V4Strategy(
            id="PENDING",  # Will be assigned later
            name=extracted.get("name", filename.rsplit(".", 1)[0])[:100],
            created=now,
            status=StrategyStatus.PENDING,
            source=source,
            tags=tags,
            hypothesis=hypothesis,
            strategy_mode=StrategyMode.SIMPLE,
            universe=universe,
            entry=entry,
            position=position,
            exit=exit,
            data_requirements=data_reqs,
            assumptions=assumptions,
            risks=risks,
        )

    def _score_quality(
        self, strategy: V4Strategy, content: str
    ) -> IngestionQuality:
        """Score the ingestion quality of a strategy.

        Args:
            strategy: The extracted V4Strategy.
            content: Original file content.

        Returns:
            IngestionQuality with all scores and decision.
        """
        # Calculate specificity score
        specificity = SpecificityScore(
            has_entry_rules=strategy.entry is not None,
            has_exit_rules=strategy.exit is not None,
            has_position_sizing=(
                strategy.position is not None
                and strategy.position.sizing is not None
            ),
            has_universe_definition=(
                strategy.universe.type != UniverseType.STATIC
                or len(strategy.universe.instruments) > 0
            ),
            has_backtest_period=strategy.backtest_params is not None,
            has_out_of_sample=(
                strategy.source.credibility is not None
                and strategy.source.credibility.claimed_performance is not None
                and strategy.source.credibility.claimed_performance.is_out_of_sample
                is True
            ),
            has_transaction_costs=any(
                "cost" in str(a.assumption).lower() or "slippage" in str(a.assumption).lower()
                for a in strategy.assumptions
            ),
            has_code_or_pseudocode="```" in content or "def " in content or "class " in content,
        )

        # Calculate trust score
        trust = self._calculate_trust_score(strategy, content)

        # Detect red flags
        red_flags = self._detect_red_flags(strategy, content)

        # Apply red flag penalty to trust score
        trust.red_flag_penalty = -15 * len(
            [rf for rf in red_flags if rf.severity == RedFlagSeverity.HARD]
        )

        return IngestionQuality(
            specificity=specificity,
            trust_score=trust,
            red_flags=red_flags,
        )

    def _calculate_trust_score(
        self, strategy: V4Strategy, content: str
    ) -> TrustScore:
        """Calculate trust score components."""
        # Economic rationale (0-30)
        economic_rationale = 0
        if strategy.hypothesis.edge:
            if strategy.hypothesis.edge.mechanism:
                economic_rationale += 10
            if strategy.hypothesis.edge.why_exists:
                economic_rationale += 10
            if strategy.hypothesis.edge.counterparty:
                economic_rationale += 5
            if strategy.hypothesis.edge.why_persists:
                economic_rationale += 5

        # Out-of-sample evidence (0-25)
        out_of_sample = 0
        if strategy.source.credibility:
            perf = strategy.source.credibility.claimed_performance
            if perf:
                if perf.is_out_of_sample:
                    out_of_sample = 25
                elif perf.sample_period:
                    out_of_sample = 10

        # Implementation realism (0-20)
        implementation = 0
        if strategy.entry is not None:
            implementation += 5
        if strategy.exit is not None:
            implementation += 5
        if strategy.position is not None:
            implementation += 5
        if len(strategy.assumptions) > 0:
            implementation += 5

        # Source credibility (0-15)
        source_cred = 0
        if strategy.source.credibility:
            track = strategy.source.credibility.author_track_record
            if track == AuthorTrackRecord.VERIFIED_FUND_MANAGER:
                source_cred = 15
            elif track == AuthorTrackRecord.ACADEMIC:
                source_cred = 12
            elif track == AuthorTrackRecord.RETAIL_VERIFIED:
                source_cred = 8
            elif track == AuthorTrackRecord.RETAIL_UNVERIFIED:
                source_cred = 4

            if strategy.source.credibility.author_skin_in_game:
                source_cred = min(15, source_cred + 3)

        # Novelty (0-10)
        novelty = 5  # Default mid-range
        # Could be enhanced with more sophisticated analysis

        return TrustScore(
            economic_rationale=economic_rationale,
            out_of_sample_evidence=out_of_sample,
            implementation_realism=implementation,
            source_credibility=source_cred,
            novelty=novelty,
            red_flag_penalty=0,  # Will be set after red flag detection
        )

    def _detect_red_flags(
        self, strategy: V4Strategy, content: str
    ) -> list[RedFlag]:
        """Detect red flags in the strategy."""
        flags: list[RedFlag] = []
        content_lower = content.lower()

        # Check for hard red flags in config
        for flag_id in self.config.red_flags.hard_reject:
            if self._check_red_flag(flag_id, strategy, content_lower):
                flags.append(create_hard_red_flag(flag_id))

        # Check for soft red flags in config
        for flag_id in self.config.red_flags.soft_warning:
            if self._check_red_flag(flag_id, strategy, content_lower):
                flags.append(create_soft_red_flag(flag_id))

        return flags

    def _check_red_flag(
        self, flag_id: str, strategy: V4Strategy, content_lower: str
    ) -> bool:
        """Check if a specific red flag is present."""
        # Check claimed performance
        if strategy.source.credibility and strategy.source.credibility.claimed_performance:
            perf = strategy.source.credibility.claimed_performance

            if flag_id == "sharpe_above_3":
                if perf.sharpe and perf.sharpe > 3.0:
                    return True

        # Check content patterns
        patterns = {
            "no_losing_periods": [
                "never had a losing",
                "no losing months",
                "no losing years",
                "100% win rate",
            ],
            "works_all_conditions": [
                "works in all market",
                "all conditions",
                "any market environment",
            ],
            "author_selling": [
                "buy my course",
                "subscribe to my",
                "join my discord",
                "paid membership",
                "premium signals",
            ],
            "no_transaction_costs": [],  # Check strategy assumptions
            "no_drawdown_mentioned": [],  # Check for drawdown discussion
            "high_leverage": ["10x leverage", "20x leverage", "100x leverage"],
        }

        if flag_id in patterns:
            for pattern in patterns[flag_id]:
                if pattern in content_lower:
                    return True

        # Strategy-level checks
        if flag_id == "no_transaction_costs":
            has_cost_discussion = any(
                "cost" in str(a.assumption).lower() or "slippage" in str(a.assumption).lower()
                for a in strategy.assumptions
            )
            if not has_cost_discussion and "cost" not in content_lower:
                return True

        if flag_id == "unknown_rationale":
            if not strategy.hypothesis.edge:
                return True

        return False

    def _save_strategy(self, strategy: V4Strategy) -> Path:
        """Save strategy to YAML file in strategies/pending/."""
        strategy_path = self.workspace.strategy_path(strategy.id, status="pending")

        # Ensure directory exists
        strategy_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict, handling enums and dates
        strategy_dict = strategy.model_dump(mode="json")

        # Write YAML
        with open(strategy_path, "w") as f:
            yaml.dump(
                strategy_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

        return strategy_path

    def _archive_file(self, file_path: Path, reason: str) -> None:
        """Move a processed file to the archive directory."""
        # Create archive subdirectory based on reason
        archive_dir = self.workspace.archive_path / reason
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Add timestamp to filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{timestamp}_{file_path.name}"
        dest_path = archive_dir / new_name

        shutil.move(str(file_path), str(dest_path))

    # =========================================================================
    # HELPER METHODS FOR PARSING ENUMS
    # =========================================================================

    @staticmethod
    def _parse_edge_category(value: str | None) -> EdgeCategory:
        """Parse edge category from string."""
        if not value:
            return EdgeCategory.OTHER
        try:
            return EdgeCategory(value.lower())
        except ValueError:
            return EdgeCategory.OTHER

    @staticmethod
    def _parse_source_type(value: str | None) -> SourceType:
        """Parse source type from string."""
        if not value:
            return SourceType.PERSONAL
        try:
            return SourceType(value.lower())
        except ValueError:
            return SourceType.PERSONAL

    @staticmethod
    def _parse_track_record(value: str | None) -> AuthorTrackRecord:
        """Parse author track record from string."""
        if not value:
            return AuthorTrackRecord.UNKNOWN
        try:
            return AuthorTrackRecord(value.lower())
        except ValueError:
            return AuthorTrackRecord.UNKNOWN

    @staticmethod
    def _parse_assumption_category(value: str | None) -> AssumptionCategory:
        """Parse assumption category from string."""
        if not value:
            return AssumptionCategory.MODEL
        try:
            return AssumptionCategory(value.lower())
        except ValueError:
            return AssumptionCategory.MODEL

    @staticmethod
    def _parse_risk_category(value: str | None) -> RiskCategory:
        """Parse risk category from string."""
        if not value:
            return RiskCategory.MODEL
        try:
            return RiskCategory(value.lower())
        except ValueError:
            return RiskCategory.MODEL

    @staticmethod
    def _parse_risk_severity(value: str | None) -> RiskSeverity:
        """Parse risk severity from string."""
        if not value:
            return RiskSeverity.MEDIUM
        try:
            return RiskSeverity(value.lower())
        except ValueError:
            return RiskSeverity.MEDIUM

    @staticmethod
    def _parse_hypothesis_type(value: str | None) -> HypothesisType | None:
        """Parse hypothesis type from string."""
        if not value:
            return None
        try:
            return HypothesisType(value.lower().replace(" ", "_").replace("-", "_"))
        except ValueError:
            return None

    @staticmethod
    def _parse_asset_class(value: str | None) -> AssetClass | None:
        """Parse asset class from string."""
        if not value:
            return None
        try:
            return AssetClass(value.lower().replace(" ", "_").replace("-", "_"))
        except ValueError:
            return None

    @staticmethod
    def _parse_complexity(value: str | None) -> Complexity:
        """Parse complexity from string."""
        if not value:
            return Complexity.MODERATE
        try:
            return Complexity(value.lower())
        except ValueError:
            return Complexity.MODERATE

    def _build_universe(self, univ_data: dict[str, Any]) -> Universe:
        """Build Universe from extraction data."""
        univ_type_str = univ_data.get("type", "static")
        try:
            univ_type = UniverseType(univ_type_str.lower())
        except ValueError:
            univ_type = UniverseType.STATIC

        instruments = []
        if univ_data.get("instruments"):
            for symbol in univ_data["instruments"]:
                if isinstance(symbol, str):
                    instruments.append(
                        StaticInstrument(
                            symbol=symbol.upper(),
                            asset_type=InstrumentAssetType.EQUITY,
                        )
                    )

        return Universe(type=univ_type, instruments=instruments)

    def _build_entry(self, entry_data: dict[str, Any]) -> Entry:
        """Build Entry from extraction data."""
        entry_type_str = entry_data.get("type", "technical")
        try:
            entry_type = EntryType(entry_type_str.lower().replace(" ", "_").replace("-", "_"))
        except ValueError:
            entry_type = EntryType.TECHNICAL

        technical = None
        if entry_type == EntryType.TECHNICAL:
            indicators = entry_data.get("indicators", [])
            conditions = entry_data.get("conditions", "")
            rules = entry_data.get("rules", [])
            technical = TechnicalConfig(
                indicator=indicators[0] if indicators else "custom",
                params={"indicators": indicators, "rules": rules},
                condition=conditions or " AND ".join(rules) if rules else "custom",
            )

        return Entry(type=entry_type, technical=technical)

    def _build_position(self, sizing_data: dict[str, Any]) -> Position:
        """Build Position from extraction data."""
        method_str = sizing_data.get("method", "equal_weight")
        try:
            method = SizingMethod(method_str.lower().replace(" ", "_").replace("-", "_"))
        except ValueError:
            method = SizingMethod.EQUAL_WEIGHT

        return Position(
            type=PositionType.SINGLE_LEG,
            legs=[
                PositionLeg(
                    name="main",
                    direction=Direction.LONG,
                    instrument=LegInstrument(source=InstrumentSource.FROM_UNIVERSE),
                    asset_type=InstrumentAssetType.EQUITY,
                )
            ],
            sizing=PositionSizing(
                method=method,
                params={"description": sizing_data.get("description", "")},
            ),
        )

    def _build_exit(self, exit_data: dict[str, Any]) -> Exit:
        """Build Exit from extraction data."""
        paths = []

        rules = exit_data.get("rules", [])
        for i, rule in enumerate(rules):
            paths.append(
                ExitPath(
                    name=f"exit_{i + 1}",
                    type=ExitType.SIGNAL_REVERSAL,
                    condition_description=rule,
                )
            )

        if exit_data.get("stop_loss"):
            paths.append(
                ExitPath(
                    name="stop_loss",
                    type=ExitType.STOP_LOSS,
                    condition_description=exit_data["stop_loss"],
                )
            )

        if exit_data.get("take_profit"):
            paths.append(
                ExitPath(
                    name="take_profit",
                    type=ExitType.TAKE_PROFIT,
                    condition_description=exit_data["take_profit"],
                )
            )

        if exit_data.get("time_based"):
            paths.append(
                ExitPath(
                    name="time_exit",
                    type=ExitType.TIME_BASED,
                    condition_description=exit_data["time_based"],
                )
            )

        # Ensure at least one exit path
        if not paths:
            paths.append(
                ExitPath(
                    name="default_exit",
                    type=ExitType.SIGNAL_REVERSAL,
                    condition_description="Exit when entry conditions no longer hold",
                )
            )

        return Exit(paths=paths, priority=ExitPriority.FIRST_TRIGGERED)

    def _build_data_requirements(
        self, data_reqs: list[str]
    ) -> DataRequirements:
        """Build DataRequirements from extraction data."""
        price_data = []

        # Default price data requirement
        price_data.append(
            PriceDataRequirement(
                type=PriceDataType.DAILY,
                instruments="from_universe",
                history_required="1y",
            )
        )

        # Add additional requirements based on extracted list
        for req in data_reqs:
            req_lower = req.lower()
            if "intraday" in req_lower or "minute" in req_lower:
                price_data.append(
                    PriceDataRequirement(
                        type=PriceDataType.INTRADAY_1MIN,
                        instruments="from_universe",
                        history_required="6m",
                    )
                )

        return DataRequirements(price_data=price_data)
