"""Catalog manager for CRUD operations on research entries."""

import json
from datetime import datetime
from pathlib import Path

from research_system.db.connection import init_database
from research_system.schemas.common import EntryStatus, EntryType
from research_system.schemas.proposal import Proposal, ProposalStatus
from research_system.schemas.strategy import StrategyDefinition
from research_system.schemas.validation import ValidationResult


class CatalogEntry:
    """Represents a catalog entry with all metadata."""

    def __init__(
        self,
        id: str,
        type: EntryType,
        name: str,
        status: EntryStatus = EntryStatus.UNTESTED,
        description: str | None = None,
        tier: int | None = None,
        strategy_type: str | None = None,
        definition_hash: str | None = None,
        parent_id: str | None = None,
        source_document: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        blocking_reason: str | None = None,
        tags: list[str] | None = None,
    ):
        self.id = id
        self.type = type
        self.name = name
        self.status = status
        self.description = description
        self.tier = tier
        self.strategy_type = strategy_type
        self.definition_hash = definition_hash
        self.parent_id = parent_id
        self.source_document = source_document
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at
        self.blocking_reason = blocking_reason
        self.tags = tags or []


class CatalogManager:
    """Manages the research catalog with JSON files and SQLite backend."""

    def __init__(self, workspace_path: Path | str):
        """Initialize catalog manager.

        Args:
            workspace_path: Path to workspace containing strategies/ and catalog.db
        """
        self.workspace_path = Path(workspace_path)
        self.strategies_path = self.workspace_path / "strategies"
        self.db_path = self.workspace_path / "catalog.db"

        # Ensure directories exist
        self.strategies_path.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._db = init_database(self.db_path)

    def close(self) -> None:
        """Close database connection."""
        self._db.close()

    def __enter__(self) -> "CatalogManager":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ==================== Entry Operations ====================

    def create_entry(
        self,
        strategy: StrategyDefinition,
        entry_type: EntryType = EntryType.STRAT,
    ) -> str:
        """Create a new catalog entry from a strategy definition.

        Args:
            strategy: Strategy definition
            entry_type: Type of entry

        Returns:
            Entry ID
        """
        entry_id = strategy.metadata.id
        definition_hash = strategy.compute_hash()

        # Save JSON file
        json_path = self.strategies_path / f"{entry_id}.json"
        with open(json_path, "w") as f:
            f.write(strategy.model_dump_json(indent=2))

        # Insert into database
        with self._db.transaction() as cursor:
            cursor.execute(
                """
                INSERT INTO entries (
                    id, type, name, description, status, tier, strategy_type,
                    definition_hash, parent_id, source_document, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    entry_type.value,
                    strategy.metadata.name,
                    strategy.metadata.description,
                    EntryStatus.UNTESTED.value,
                    strategy.tier,
                    strategy.strategy_type,
                    definition_hash,
                    strategy.metadata.parent_id,
                    strategy.metadata.source_document,
                    datetime.utcnow().isoformat(),
                ),
            )

            # Insert into strategy_files
            cursor.execute(
                """
                INSERT INTO strategy_files (entry_id, file_path, definition_hash)
                VALUES (?, ?, ?)
                """,
                (entry_id, str(json_path.relative_to(self.workspace_path)), definition_hash),
            )

            # Add tags
            for tag in strategy.metadata.tags:
                cursor.execute(
                    "INSERT INTO entry_tags (entry_id, tag) VALUES (?, ?)",
                    (entry_id, tag),
                )

        return entry_id

    def get_entry(self, entry_id: str) -> CatalogEntry | None:
        """Get an entry by ID.

        Args:
            entry_id: Entry ID

        Returns:
            CatalogEntry or None if not found
        """
        row = self._db.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()

        if not row:
            return None

        # Get tags
        tags_rows = self._db.execute(
            "SELECT tag FROM entry_tags WHERE entry_id = ?", (entry_id,)
        ).fetchall()
        tags = [r[0] for r in tags_rows]

        return CatalogEntry(
            id=row["id"],
            type=EntryType(row["type"]),
            name=row["name"],
            status=EntryStatus(row["status"]),
            description=row["description"],
            tier=row["tier"],
            strategy_type=row["strategy_type"],
            definition_hash=row["definition_hash"],
            parent_id=row["parent_id"],
            source_document=row["source_document"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
            blocking_reason=row["blocking_reason"],
            tags=tags,
        )

    def get_strategy_definition(self, entry_id: str) -> StrategyDefinition | None:
        """Get the full strategy definition JSON.

        Args:
            entry_id: Entry ID

        Returns:
            StrategyDefinition or None
        """
        row = self._db.execute(
            "SELECT file_path FROM strategy_files WHERE entry_id = ?", (entry_id,)
        ).fetchone()

        if not row:
            return None

        json_path = self.workspace_path / row["file_path"]
        if not json_path.exists():
            return None

        with open(json_path) as f:
            data = json.load(f)

        return StrategyDefinition.model_validate(data)

    def update_status(
        self,
        entry_id: str,
        status: EntryStatus,
        blocking_reason: str | None = None,
    ) -> bool:
        """Update entry status.

        Args:
            entry_id: Entry ID
            status: New status
            blocking_reason: Reason if BLOCKED

        Returns:
            True if updated
        """
        with self._db.transaction() as cursor:
            if status == EntryStatus.BLOCKED:
                cursor.execute(
                    """
                    UPDATE entries
                    SET status = ?, blocking_reason = ?, blocked_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        status.value,
                        blocking_reason,
                        datetime.utcnow().isoformat(),
                        datetime.utcnow().isoformat(),
                        entry_id,
                    ),
                )
            else:
                cursor.execute(
                    """
                    UPDATE entries
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status.value, datetime.utcnow().isoformat(), entry_id),
                )
            return cursor.rowcount > 0

    def archive_entry(
        self,
        entry_id: str,
        reason: str,
        canonical_id: str | None = None,
    ) -> bool:
        """Archive an entry (for deduplication).

        Args:
            entry_id: Entry to archive
            reason: Reason for archiving
            canonical_id: ID of canonical entry if consolidating duplicates

        Returns:
            True if archived
        """
        with self._db.transaction() as cursor:
            cursor.execute(
                """
                UPDATE entries
                SET status = ?, archived_reason = ?, archived_at = ?,
                    canonical_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    EntryStatus.ARCHIVED.value,
                    reason,
                    datetime.utcnow().isoformat(),
                    canonical_id,
                    datetime.utcnow().isoformat(),
                    entry_id,
                ),
            )
            return cursor.rowcount > 0

    # ==================== Query Operations ====================

    def list_entries(
        self,
        status: EntryStatus | None = None,
        entry_type: EntryType | None = None,
        min_sharpe: float | None = None,
        tag: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CatalogEntry]:
        """Query entries with filters.

        Args:
            status: Filter by status
            entry_type: Filter by type
            min_sharpe: Filter by minimum Sharpe (requires validation)
            tag: Filter by tag
            limit: Max results
            offset: Result offset

        Returns:
            List of matching entries
        """
        conditions = []
        params: list = []

        if status:
            conditions.append("e.status = ?")
            params.append(status.value)

        if entry_type:
            conditions.append("e.type = ?")
            params.append(entry_type.value)

        if tag:
            conditions.append("e.id IN (SELECT entry_id FROM entry_tags WHERE tag = ?)")
            params.append(tag)

        if min_sharpe is not None:
            conditions.append(
                """
                e.id IN (
                    SELECT entry_id FROM validations
                    WHERE mean_sharpe >= ?
                )
                """
            )
            params.append(min_sharpe)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT e.* FROM entries e
            WHERE {where_clause}
            ORDER BY e.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = self._db.execute(query, tuple(params)).fetchall()

        entries = []
        for row in rows:
            entries.append(
                CatalogEntry(
                    id=row["id"],
                    type=EntryType(row["type"]),
                    name=row["name"],
                    status=EntryStatus(row["status"]),
                    description=row["description"],
                    tier=row["tier"],
                    strategy_type=row["strategy_type"],
                    definition_hash=row["definition_hash"],
                    parent_id=row["parent_id"],
                    created_at=datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else None,
                    blocking_reason=row["blocking_reason"],
                )
            )

        return entries

    def count_entries(
        self,
        status: EntryStatus | None = None,
        entry_type: EntryType | None = None,
    ) -> int:
        """Count entries matching filters.

        Args:
            status: Filter by status
            entry_type: Filter by type

        Returns:
            Count of matching entries
        """
        conditions = []
        params: list = []

        if status:
            conditions.append("status = ?")
            params.append(status.value)

        if entry_type:
            conditions.append("type = ?")
            params.append(entry_type.value)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        result = self._db.execute(
            f"SELECT COUNT(*) FROM entries WHERE {where_clause}",
            tuple(params),
        ).fetchone()

        return result[0] if result else 0

    # ==================== Validation Operations ====================

    def add_validation_result(
        self,
        entry_id: str,
        result: ValidationResult,
    ) -> int:
        """Store a validation result.

        Args:
            entry_id: Entry ID
            result: Validation result

        Returns:
            Validation ID
        """
        with self._db.transaction() as cursor:
            # Insert validation
            cursor.execute(
                """
                INSERT INTO validations (
                    entry_id, validation_timestamp, definition_hash, code_hash,
                    status, confidence, mean_sharpe, sharpe_std,
                    sharpe_95_ci_low, sharpe_95_ci_high, mean_cagr,
                    mean_max_drawdown, worst_drawdown, consistency_score,
                    p_value, p_value_adjusted, result_json, notes, blocking_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    result.validation_timestamp.isoformat(),
                    result.strategy_definition_hash,
                    result.generated_code_hash,
                    result.validation_status.value,
                    result.confidence.value if result.confidence else None,
                    result.aggregate_metrics.mean_sharpe,
                    result.aggregate_metrics.sharpe_std,
                    result.aggregate_metrics.sharpe_95_ci_low,
                    result.aggregate_metrics.sharpe_95_ci_high,
                    result.aggregate_metrics.mean_cagr,
                    result.aggregate_metrics.mean_max_drawdown,
                    result.aggregate_metrics.worst_drawdown,
                    result.aggregate_metrics.consistency_score,
                    result.aggregate_metrics.p_value,
                    result.aggregate_metrics.p_value_adjusted,
                    result.model_dump_json(),
                    result.notes,
                    result.blocking_reason,
                ),
            )
            validation_id = cursor.lastrowid
            assert validation_id is not None  # SQLite guarantees this after INSERT

            # Insert window results
            for window in result.walk_forward_results:
                cursor.execute(
                    """
                    INSERT INTO window_results (
                        validation_id, window_id, start_date, end_date,
                        cagr, sharpe, sortino, max_drawdown, win_rate,
                        profit_factor, trades, volatility,
                        benchmark_cagr, benchmark_sharpe,
                        regime_direction, regime_volatility, regime_rates,
                        regime_sector, regime_cap
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        validation_id,
                        window.window_id,
                        window.start_date,
                        window.end_date,
                        window.metrics.cagr,
                        window.metrics.sharpe,
                        window.metrics.sortino,
                        window.metrics.max_drawdown,
                        window.metrics.win_rate,
                        window.metrics.profit_factor,
                        window.metrics.trades,
                        window.metrics.volatility,
                        window.benchmark_cagr,
                        window.benchmark_sharpe,
                        window.regime_tags.direction.value,
                        window.regime_tags.volatility.value,
                        window.regime_tags.rate_environment.value,
                        window.regime_tags.sector_leader.value
                        if window.regime_tags.sector_leader
                        else None,
                        window.regime_tags.cap_leadership.value
                        if window.regime_tags.cap_leadership
                        else None,
                    ),
                )

            # Update entry status based on validation
            new_status = EntryStatus.VALIDATED if result.is_valid() else EntryStatus.INVALIDATED
            cursor.execute(
                "UPDATE entries SET status = ?, updated_at = ? WHERE id = ?",
                (new_status.value, datetime.utcnow().isoformat(), entry_id),
            )

            return validation_id

    def get_latest_validation(self, entry_id: str) -> ValidationResult | None:
        """Get the most recent validation for an entry.

        Args:
            entry_id: Entry ID

        Returns:
            ValidationResult or None
        """
        row = self._db.execute(
            """
            SELECT result_json FROM validations
            WHERE entry_id = ?
            ORDER BY validation_timestamp DESC
            LIMIT 1
            """,
            (entry_id,),
        ).fetchone()

        if not row or not row["result_json"]:
            return None

        return ValidationResult.model_validate_json(row["result_json"])

    # ==================== Proposal Operations ====================

    def create_proposal(self, proposal: Proposal) -> str:
        """Create a proposal in the queue.

        Args:
            proposal: Proposal to create

        Returns:
            Proposal ID
        """
        with self._db.transaction() as cursor:
            cursor.execute(
                """
                INSERT INTO proposals (
                    id, type, status, created_at, created_by,
                    title, description, proposal_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.id,
                    proposal.type.value,
                    proposal.status.value,
                    proposal.created_at.isoformat(),
                    proposal.created_by,
                    proposal.title,
                    proposal.description,
                    proposal.model_dump_json(),
                ),
            )
        return proposal.id

    def list_proposals(
        self,
        status: ProposalStatus | None = None,
        limit: int = 100,
    ) -> list[Proposal]:
        """List proposals.

        Args:
            status: Filter by status
            limit: Max results

        Returns:
            List of proposals
        """
        if status:
            rows = self._db.execute(
                """
                SELECT proposal_json FROM proposals
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (status.value, limit),
            ).fetchall()
        else:
            rows = self._db.execute(
                """
                SELECT proposal_json FROM proposals
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            Proposal.model_validate_json(row["proposal_json"])
            for row in rows
            if row["proposal_json"]
        ]

    def review_proposal(
        self,
        proposal_id: str,
        status: ProposalStatus,
        notes: str,
        reviewed_by: str,
    ) -> bool:
        """Record a review decision on a proposal.

        Args:
            proposal_id: Proposal ID
            status: New status (approved, rejected, deferred)
            notes: Review notes
            reviewed_by: Reviewer identifier

        Returns:
            True if updated
        """
        with self._db.transaction() as cursor:
            cursor.execute(
                """
                UPDATE proposals
                SET status = ?, review_notes = ?, reviewed_by = ?,
                    reviewed_at = ?, decision = ?
                WHERE id = ?
                """,
                (
                    status.value,
                    notes,
                    reviewed_by,
                    datetime.utcnow().isoformat(),
                    status.value,
                    proposal_id,
                ),
            )
            return cursor.rowcount > 0

    # ==================== Statistics ====================

    def get_catalog_stats(self) -> dict:
        """Get catalog statistics.

        Returns:
            Dictionary with counts by status and type
        """
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        total = 0

        # Count by status
        rows = self._db.execute(
            "SELECT status, COUNT(*) as count FROM entries GROUP BY status"
        ).fetchall()
        for row in rows:
            by_status[row["status"]] = row["count"]
            total += row["count"]

        # Count by type
        rows = self._db.execute(
            "SELECT type, COUNT(*) as count FROM entries GROUP BY type"
        ).fetchall()
        for row in rows:
            by_type[row["type"]] = row["count"]

        return {"total": total, "by_status": by_status, "by_type": by_type}
