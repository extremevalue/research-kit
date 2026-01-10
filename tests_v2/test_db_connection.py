"""Tests for database connection and initialization."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from research_system.db.connection import (
    DatabaseConnection,
    get_schema_version,
    init_database,
)


class TestDatabaseConnection:
    """Tests for DatabaseConnection class."""

    def test_connection_creates_file(self):
        """Test that connection creates the database file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            assert not db_path.exists()

            db = DatabaseConnection(db_path)
            db.execute("SELECT 1")
            assert db_path.exists()
            db.close()

    def test_connection_context_manager(self):
        """Test using connection as context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            with DatabaseConnection(db_path) as db:
                db.execute("CREATE TABLE test (id INTEGER)")
                db.execute("INSERT INTO test VALUES (1)")
                db.commit()

            # Should be closed now, connection recreates on use
            with DatabaseConnection(db_path) as db:
                result = db.execute("SELECT id FROM test").fetchone()
                assert result[0] == 1

    def test_transaction_commits_on_success(self):
        """Test that transaction commits on success."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            with DatabaseConnection(db_path) as db:
                db.execute("CREATE TABLE test (id INTEGER)")
                with db.transaction() as cursor:
                    cursor.execute("INSERT INTO test VALUES (1)")
                    cursor.execute("INSERT INTO test VALUES (2)")

                result = db.execute("SELECT COUNT(*) FROM test").fetchone()
                assert result[0] == 2

    def test_transaction_rollbacks_on_error(self):
        """Test that transaction rolls back on error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            with DatabaseConnection(db_path) as db:
                db.execute("CREATE TABLE test (id INTEGER UNIQUE)")
                db.commit()

                # First insert succeeds
                with db.transaction() as cursor:
                    cursor.execute("INSERT INTO test VALUES (1)")

                # This transaction should fail and rollback
                with pytest.raises(sqlite3.IntegrityError):  # noqa: SIM117
                    with db.transaction() as cursor:
                        cursor.execute("INSERT INTO test VALUES (2)")
                        cursor.execute("INSERT INTO test VALUES (1)")  # Duplicate

                # Only the first value should exist
                result = db.execute("SELECT COUNT(*) FROM test").fetchone()
                assert result[0] == 1

    def test_cursor_readonly(self):
        """Test cursor for read-only operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            with DatabaseConnection(db_path) as db:
                db.execute("CREATE TABLE test (id INTEGER)")
                db.execute("INSERT INTO test VALUES (1)")
                db.commit()

                with db.cursor() as cursor:
                    result = cursor.execute("SELECT id FROM test").fetchone()
                    assert result[0] == 1

    def test_executemany(self):
        """Test executemany for batch operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            with DatabaseConnection(db_path) as db:
                db.execute("CREATE TABLE test (id INTEGER, name TEXT)")
                db.executemany(
                    "INSERT INTO test VALUES (?, ?)",
                    [(1, "a"), (2, "b"), (3, "c")],
                )
                db.commit()

                result = db.execute("SELECT COUNT(*) FROM test").fetchone()
                assert result[0] == 3

    def test_row_factory_returns_dict_like(self):
        """Test that rows can be accessed like dictionaries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            with DatabaseConnection(db_path) as db:
                db.execute("CREATE TABLE test (id INTEGER, name TEXT)")
                db.execute("INSERT INTO test VALUES (1, 'test')")
                db.commit()

                row = db.execute("SELECT id, name FROM test").fetchone()
                assert row["id"] == 1
                assert row["name"] == "test"

    def test_foreign_keys_enabled(self):
        """Test that foreign keys are enforced."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            with DatabaseConnection(db_path) as db:
                db.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
                db.execute(
                    "CREATE TABLE child (id INTEGER, parent_id INTEGER REFERENCES parent(id))"
                )
                db.commit()

                # Insert parent first
                db.execute("INSERT INTO parent VALUES (1)")
                db.commit()

                # Insert child with valid reference works
                db.execute("INSERT INTO child VALUES (1, 1)")
                db.commit()

                # Insert child with invalid reference should fail
                with pytest.raises(sqlite3.IntegrityError):
                    db.execute("INSERT INTO child VALUES (2, 999)")
                    db.commit()


class TestInitDatabase:
    """Tests for init_database function."""

    def test_creates_new_database_with_schema(self):
        """Test that new database is created with schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "catalog.db"

            db = init_database(db_path)
            try:
                # Check that tables were created
                tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                table_names = {t[0] for t in tables}

                assert "entries" in table_names
                assert "validations" in table_names
                assert "proposals" in table_names
                assert "schema_version" in table_names
            finally:
                db.close()

    def test_existing_database_not_reinitialized(self):
        """Test that existing database schema is preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "catalog.db"

            # Create and add data
            db1 = init_database(db_path)
            db1.execute("INSERT INTO entries (id, type, name) VALUES ('TEST-1', 'STRAT', 'Test')")
            db1.commit()
            db1.close()

            # Reinitialize - should not wipe data
            db2 = init_database(db_path)
            try:
                row = db2.execute("SELECT id FROM entries WHERE id = 'TEST-1'").fetchone()
                assert row is not None
                assert row[0] == "TEST-1"
            finally:
                db2.close()

    def test_creates_parent_directories(self):
        """Test that parent directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nested" / "path" / "catalog.db"
            assert not db_path.parent.exists()

            db = init_database(db_path)
            db.close()

            assert db_path.exists()


class TestGetSchemaVersion:
    """Tests for get_schema_version function."""

    def test_returns_version_from_initialized_db(self):
        """Test getting version from initialized database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "catalog.db"
            db = init_database(db_path)

            version = get_schema_version(db)
            assert version == 1
            db.close()

    def test_returns_zero_for_empty_db(self):
        """Test getting version from database without schema_version table."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "empty.db"
            db = DatabaseConnection(db_path)
            db.execute("CREATE TABLE test (id INTEGER)")
            db.commit()

            version = get_schema_version(db)
            assert version == 0
            db.close()
