"""Database connection management for research-kit."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# Get the schema SQL file path
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class DatabaseConnection:
    """Manages SQLite database connections."""

    def __init__(self, db_path: Path | str):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._connection: sqlite3.Connection | None = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Return rows as dictionaries
            self._connection.row_factory = sqlite3.Row
        return self._connection

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for database transactions.

        Automatically commits on success, rolls back on error.

        Example:
            with db.transaction() as cursor:
                cursor.execute("INSERT INTO ...")
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for read-only cursor (no auto-commit)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single SQL statement.

        Args:
            sql: SQL statement
            params: Parameters for the statement

        Returns:
            Cursor with results
        """
        conn = self._get_connection()
        return conn.execute(sql, params)

    def executemany(self, sql: str, params_list: list[tuple]) -> sqlite3.Cursor:
        """Execute SQL statement for multiple parameter sets.

        Args:
            sql: SQL statement
            params_list: List of parameter tuples

        Returns:
            Cursor with results
        """
        conn = self._get_connection()
        return conn.executemany(sql, params_list)

    def commit(self) -> None:
        """Commit current transaction."""
        if self._connection:
            self._connection.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        if self._connection:
            self._connection.rollback()

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> "DatabaseConnection":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager, closing connection."""
        self.close()


def init_database(db_path: Path | str, schema_path: Path | None = None) -> DatabaseConnection:
    """Initialize a new database with the schema.

    Args:
        db_path: Path for the database file
        schema_path: Path to schema SQL file (default: built-in schema)

    Returns:
        DatabaseConnection instance
    """
    db_path = Path(db_path)
    schema_path = schema_path or SCHEMA_PATH

    # Create parent directory if needed
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if database already exists
    db_exists = db_path.exists()

    db = DatabaseConnection(db_path)

    if not db_exists:
        # Apply schema to new database
        with open(schema_path) as f:
            schema_sql = f.read()

        with db.transaction() as cursor:
            cursor.executescript(schema_sql)

    return db


def get_schema_version(db: DatabaseConnection) -> int:
    """Get the current schema version.

    Args:
        db: Database connection

    Returns:
        Current schema version number
    """
    try:
        result = db.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()
        return result[0] if result and result[0] else 0
    except sqlite3.OperationalError:
        return 0
