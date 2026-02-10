"""Tests for V4 logging system.

This module tests the V4 logging configuration:
1. Log file creation in correct location
2. Log messages written to file
3. Log level configuration
4. Log file naming format
5. Log rotation at midnight
6. Console output alongside file
7. Multiple named loggers
8. Log file cleanup
9. Log file listing
"""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from research_system.core.v4.config import Config, LoggingConfig, LogLevel
from research_system.core.v4.logging import (
    setup_logging,
    get_logger,
    LogManager,
    DEFAULT_LOGGER_NAME,
    LOG_FILE_PREFIX,
    LOG_FILE_EXTENSION,
    DEFAULT_BACKUP_COUNT,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def workspace_path(tmp_path):
    """Create a temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "logs").mkdir()
    return workspace


@pytest.fixture
def workspace_with_config(workspace_path):
    """Create a workspace with a config file."""
    import yaml

    config_data = {
        "version": "1.0",
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    }
    config_file = workspace_path / "research-kit.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
    return workspace_path


@pytest.fixture
def debug_config():
    """Create a config with DEBUG level."""
    return Config(logging=LoggingConfig(level=LogLevel.DEBUG))


@pytest.fixture(autouse=True)
def cleanup_loggers():
    """Clean up loggers after each test to avoid handler accumulation."""
    yield
    # Remove all handlers from test loggers
    for name in [DEFAULT_LOGGER_NAME, "research_system", "research_system.ingest", "test_logger"]:
        logger = logging.getLogger(name)
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


# =============================================================================
# TEST SETUP_LOGGING FUNCTION
# =============================================================================


class TestSetupLogging:
    """Test the setup_logging function."""

    def test_setup_logging_creates_log_directory(self, tmp_path):
        """Test that setup_logging creates the logs directory."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        logs_path = workspace / "logs"
        assert not logs_path.exists()

        setup_logging(workspace)

        assert logs_path.exists()
        assert logs_path.is_dir()

    def test_setup_logging_creates_log_file(self, workspace_path):
        """Test that setup_logging creates a log file."""
        logger = setup_logging(workspace_path)
        logger.info("Test message")

        today = datetime.now().strftime("%Y-%m-%d")
        expected_file = workspace_path / "logs" / f"{LOG_FILE_PREFIX}-{today}{LOG_FILE_EXTENSION}"

        # Flush handlers
        for handler in logger.handlers:
            handler.flush()

        assert expected_file.exists()

    def test_setup_logging_returns_logger(self, workspace_path):
        """Test that setup_logging returns a logger instance."""
        logger = setup_logging(workspace_path)

        assert isinstance(logger, logging.Logger)
        assert logger.name == DEFAULT_LOGGER_NAME

    def test_setup_logging_with_custom_name(self, workspace_path):
        """Test setup_logging with a custom logger name."""
        logger = setup_logging(workspace_path, name="custom_logger")

        assert logger.name == "custom_logger"

    def test_setup_logging_with_config(self, workspace_path, debug_config):
        """Test setup_logging with explicit config."""
        logger = setup_logging(workspace_path, config=debug_config)

        assert logger.level == logging.DEBUG


# =============================================================================
# TEST GET_LOGGER FUNCTION
# =============================================================================


class TestGetLogger:
    """Test the get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger()

        assert isinstance(logger, logging.Logger)
        assert logger.name == DEFAULT_LOGGER_NAME

    def test_get_logger_with_custom_name(self):
        """Test get_logger with a custom name."""
        logger = get_logger("my.custom.logger")

        assert logger.name == "my.custom.logger"

    def test_get_logger_returns_same_instance(self):
        """Test that get_logger returns the same logger for same name."""
        logger1 = get_logger("test_logger")
        logger2 = get_logger("test_logger")

        assert logger1 is logger2


# =============================================================================
# TEST V4LOGMANAGER CLASS
# =============================================================================


class TestLogManager:
    """Test the LogManager class."""

    def test_init_with_workspace_path(self, workspace_path):
        """Test initializing log manager with workspace path."""
        manager = LogManager(workspace_path)

        assert manager.workspace_path == workspace_path
        assert manager.logs_path == workspace_path / "logs"

    def test_init_with_config(self, workspace_path, debug_config):
        """Test initializing log manager with explicit config."""
        manager = LogManager(workspace_path, config=debug_config)

        assert manager.config.logging.level == "DEBUG"

    def test_init_loads_config_from_workspace(self, workspace_with_config):
        """Test that log manager loads config from workspace."""
        manager = LogManager(workspace_with_config)

        assert manager.config.logging.level == "INFO"


# =============================================================================
# TEST LOG FILE LOCATION AND NAMING
# =============================================================================


class TestLogFileLocation:
    """Test log file location and naming."""

    def test_get_log_file_path_format(self, workspace_path):
        """Test that log file path has correct format."""
        manager = LogManager(workspace_path)

        log_path = manager.get_log_file_path()
        today = datetime.now().strftime("%Y-%m-%d")

        expected = workspace_path / "logs" / f"{LOG_FILE_PREFIX}-{today}{LOG_FILE_EXTENSION}"
        assert log_path == expected

    def test_log_file_in_logs_directory(self, workspace_path):
        """Test that log file is in workspace/logs directory."""
        manager = LogManager(workspace_path)

        log_path = manager.get_log_file_path()

        assert log_path.parent == workspace_path / "logs"

    def test_log_file_has_date_in_name(self, workspace_path):
        """Test that log file name includes today's date."""
        manager = LogManager(workspace_path)

        log_path = manager.get_log_file_path()
        today = datetime.now().strftime("%Y-%m-%d")

        assert today in log_path.name


# =============================================================================
# TEST LOG MESSAGES
# =============================================================================


class TestLogMessages:
    """Test that log messages are written correctly."""

    def test_info_message_written_to_file(self, workspace_path):
        """Test that INFO messages are written to log file."""
        logger = setup_logging(workspace_path)
        logger.info("Test info message")

        # Flush handlers
        for handler in logger.handlers:
            handler.flush()

        log_file = LogManager(workspace_path).get_log_file_path()
        content = log_file.read_text()

        assert "Test info message" in content
        assert "INFO" in content

    def test_warning_message_written_to_file(self, workspace_path):
        """Test that WARNING messages are written to log file."""
        logger = setup_logging(workspace_path)
        logger.warning("Test warning message")

        for handler in logger.handlers:
            handler.flush()

        log_file = LogManager(workspace_path).get_log_file_path()
        content = log_file.read_text()

        assert "Test warning message" in content
        assert "WARNING" in content

    def test_error_message_written_to_file(self, workspace_path):
        """Test that ERROR messages are written to log file."""
        logger = setup_logging(workspace_path)
        logger.error("Test error message")

        for handler in logger.handlers:
            handler.flush()

        log_file = LogManager(workspace_path).get_log_file_path()
        content = log_file.read_text()

        assert "Test error message" in content
        assert "ERROR" in content

    def test_log_format_includes_timestamp(self, workspace_path):
        """Test that log messages include timestamp."""
        logger = setup_logging(workspace_path)
        logger.info("Test message")

        for handler in logger.handlers:
            handler.flush()

        log_file = LogManager(workspace_path).get_log_file_path()
        content = log_file.read_text()

        # Check for timestamp format YYYY-MM-DD HH:MM:SS
        import re

        timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        assert re.search(timestamp_pattern, content)

    def test_log_format_includes_logger_name(self, workspace_path):
        """Test that log messages include logger name."""
        logger = setup_logging(workspace_path, name="test.logger.name")
        logger.info("Test message")

        for handler in logger.handlers:
            handler.flush()

        log_file = LogManager(workspace_path).get_log_file_path()
        content = log_file.read_text()

        assert "test.logger.name" in content


# =============================================================================
# TEST LOG LEVEL CONFIGURATION
# =============================================================================


class TestLogLevel:
    """Test log level configuration."""

    def test_debug_level_logs_debug_messages(self, workspace_path, debug_config):
        """Test that DEBUG level logs debug messages."""
        logger = setup_logging(workspace_path, config=debug_config)
        logger.debug("Debug message")

        for handler in logger.handlers:
            handler.flush()

        log_file = LogManager(workspace_path).get_log_file_path()
        content = log_file.read_text()

        assert "Debug message" in content
        assert "DEBUG" in content

    def test_info_level_does_not_log_debug(self, workspace_path):
        """Test that INFO level does not log debug messages."""
        config = Config(logging=LoggingConfig(level=LogLevel.INFO))
        logger = setup_logging(workspace_path, config=config)
        logger.debug("Debug message that should not appear")
        logger.info("Info message that should appear")

        for handler in logger.handlers:
            handler.flush()

        log_file = LogManager(workspace_path).get_log_file_path()
        content = log_file.read_text()

        assert "Debug message that should not appear" not in content
        assert "Info message that should appear" in content

    def test_warning_level_filters_info(self, workspace_path):
        """Test that WARNING level filters out INFO messages."""
        config = Config(logging=LoggingConfig(level=LogLevel.WARNING))
        logger = setup_logging(workspace_path, config=config)
        logger.info("Info message that should not appear")
        logger.warning("Warning message that should appear")

        for handler in logger.handlers:
            handler.flush()

        log_file = LogManager(workspace_path).get_log_file_path()
        content = log_file.read_text()

        assert "Info message that should not appear" not in content
        assert "Warning message that should appear" in content


# =============================================================================
# TEST LOG ROTATION
# =============================================================================


class TestLogRotation:
    """Test log rotation functionality."""

    def test_file_handler_is_timed_rotating(self, workspace_path):
        """Test that file handler is a TimedRotatingFileHandler."""
        from logging.handlers import TimedRotatingFileHandler

        logger = setup_logging(workspace_path)

        file_handlers = [h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)]
        assert len(file_handlers) == 1

    def test_rotation_configured_for_midnight(self, workspace_path):
        """Test that rotation is configured for midnight."""
        from logging.handlers import TimedRotatingFileHandler

        logger = setup_logging(workspace_path)

        file_handler = next(h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler))
        assert file_handler.when == "MIDNIGHT"

    def test_backup_count_is_set(self, workspace_path):
        """Test that backup count is set."""
        from logging.handlers import TimedRotatingFileHandler

        logger = setup_logging(workspace_path)

        file_handler = next(h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler))
        assert file_handler.backupCount == DEFAULT_BACKUP_COUNT


# =============================================================================
# TEST CONSOLE OUTPUT
# =============================================================================


class TestConsoleOutput:
    """Test console output functionality."""

    def test_console_handler_added(self, workspace_path):
        """Test that a console handler is added."""
        logger = setup_logging(workspace_path)

        console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler) and not hasattr(h, 'baseFilename')]
        # Note: TimedRotatingFileHandler inherits from StreamHandler, so we exclude file handlers
        assert len(console_handlers) >= 1

    def test_console_handler_has_formatter(self, workspace_path):
        """Test that console handler has a formatter."""
        logger = setup_logging(workspace_path)

        for handler in logger.handlers:
            assert handler.formatter is not None


# =============================================================================
# TEST MULTIPLE NAMED LOGGERS
# =============================================================================


class TestMultipleLoggers:
    """Test support for multiple named loggers."""

    def test_child_logger_inherits_handlers(self, workspace_path):
        """Test that child loggers inherit handlers from parent."""
        # Setup parent logger
        parent_logger = setup_logging(workspace_path, name="research_system")

        # Get child logger
        child_logger = get_logger("research_system.ingest")
        child_logger.info("Child logger message")

        for handler in parent_logger.handlers:
            handler.flush()

        log_file = LogManager(workspace_path).get_log_file_path()
        content = log_file.read_text()

        assert "Child logger message" in content
        assert "research_system.ingest" in content

    def test_multiple_named_loggers_write_to_same_file(self, workspace_path):
        """Test that multiple loggers write to the same file."""
        parent_logger = setup_logging(workspace_path, name="research_system")

        logger1 = get_logger("research_system.component1")
        logger2 = get_logger("research_system.component2")

        logger1.info("Message from component 1")
        logger2.info("Message from component 2")

        for handler in parent_logger.handlers:
            handler.flush()

        log_file = LogManager(workspace_path).get_log_file_path()
        content = log_file.read_text()

        assert "Message from component 1" in content
        assert "Message from component 2" in content
        assert "research_system.component1" in content
        assert "research_system.component2" in content


# =============================================================================
# TEST LOG FILE LISTING
# =============================================================================


class TestListLogFiles:
    """Test log file listing functionality."""

    def test_list_log_files_empty_directory(self, workspace_path):
        """Test listing files in empty logs directory."""
        manager = LogManager(workspace_path)

        files = manager.list_log_files()

        assert files == []

    def test_list_log_files_returns_log_files(self, workspace_path):
        """Test that list_log_files returns log files."""
        logs_dir = workspace_path / "logs"

        # Create some log files
        (logs_dir / "research-kit-2026-01-20.log").touch()
        (logs_dir / "research-kit-2026-01-21.log").touch()
        (logs_dir / "research-kit-2026-01-22.log").touch()

        manager = LogManager(workspace_path)
        files = manager.list_log_files()

        assert len(files) == 3
        assert all(f.suffix == ".log" for f in files)

    def test_list_log_files_sorted_by_name(self, workspace_path):
        """Test that log files are sorted by name (oldest first)."""
        logs_dir = workspace_path / "logs"

        # Create log files out of order
        (logs_dir / "research-kit-2026-01-22.log").touch()
        (logs_dir / "research-kit-2026-01-20.log").touch()
        (logs_dir / "research-kit-2026-01-21.log").touch()

        manager = LogManager(workspace_path)
        files = manager.list_log_files()

        names = [f.name for f in files]
        assert names == sorted(names)

    def test_list_log_files_excludes_non_log_files(self, workspace_path):
        """Test that non-log files are excluded."""
        logs_dir = workspace_path / "logs"

        (logs_dir / "research-kit-2026-01-20.log").touch()
        (logs_dir / "other-file.txt").touch()
        (logs_dir / "readme.md").touch()

        manager = LogManager(workspace_path)
        files = manager.list_log_files()

        assert len(files) == 1
        assert files[0].name == "research-kit-2026-01-20.log"

    def test_list_log_files_handles_missing_directory(self, tmp_path):
        """Test listing when logs directory doesn't exist."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        # Don't create logs directory

        manager = LogManager(workspace)
        files = manager.list_log_files()

        assert files == []


# =============================================================================
# TEST LOG CLEANUP
# =============================================================================


class TestCleanupOldLogs:
    """Test log file cleanup functionality."""

    def test_cleanup_removes_old_files(self, workspace_path):
        """Test that cleanup removes files older than keep_days."""
        logs_dir = workspace_path / "logs"

        # Create log files with different dates
        old_date = (datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d")
        recent_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

        old_file = logs_dir / f"research-kit-{old_date}.log"
        recent_file = logs_dir / f"research-kit-{recent_date}.log"

        old_file.touch()
        recent_file.touch()

        manager = LogManager(workspace_path)
        deleted = manager.cleanup_old_logs(keep_days=30)

        assert len(deleted) == 1
        assert old_file in deleted
        assert not old_file.exists()
        assert recent_file.exists()

    def test_cleanup_keeps_recent_files(self, workspace_path):
        """Test that cleanup keeps files within keep_days."""
        logs_dir = workspace_path / "logs"

        # Create recent log files
        for days_ago in range(5):
            date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            (logs_dir / f"research-kit-{date}.log").touch()

        manager = LogManager(workspace_path)
        deleted = manager.cleanup_old_logs(keep_days=30)

        assert len(deleted) == 0
        assert len(manager.list_log_files()) == 5

    def test_cleanup_with_custom_keep_days(self, workspace_path):
        """Test cleanup with custom keep_days value."""
        logs_dir = workspace_path / "logs"

        # Create log files
        for days_ago in [1, 5, 10, 15, 20]:
            date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            (logs_dir / f"research-kit-{date}.log").touch()

        manager = LogManager(workspace_path)
        deleted = manager.cleanup_old_logs(keep_days=7)

        # Files older than 7 days should be deleted (10, 15, 20 days ago)
        assert len(deleted) == 3
        # Files within 7 days should remain (1, 5 days ago)
        assert len(manager.list_log_files()) == 2

    def test_cleanup_returns_deleted_paths(self, workspace_path):
        """Test that cleanup returns paths of deleted files."""
        logs_dir = workspace_path / "logs"

        old_date = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")
        old_file = logs_dir / f"research-kit-{old_date}.log"
        old_file.touch()

        manager = LogManager(workspace_path)
        deleted = manager.cleanup_old_logs(keep_days=30)

        assert len(deleted) == 1
        assert deleted[0] == old_file

    def test_cleanup_handles_empty_directory(self, workspace_path):
        """Test cleanup with empty logs directory."""
        manager = LogManager(workspace_path)
        deleted = manager.cleanup_old_logs(keep_days=30)

        assert deleted == []

    def test_cleanup_handles_missing_directory(self, tmp_path):
        """Test cleanup when logs directory doesn't exist."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        manager = LogManager(workspace)
        deleted = manager.cleanup_old_logs(keep_days=30)

        assert deleted == []


# =============================================================================
# TEST HANDLER DEDUPLICATION
# =============================================================================


class TestHandlerDeduplication:
    """Test that handlers are not duplicated on multiple setup calls."""

    def test_setup_does_not_duplicate_handlers(self, workspace_path):
        """Test that calling setup multiple times doesn't duplicate handlers."""
        manager = LogManager(workspace_path)

        logger1 = manager.setup()
        handler_count_1 = len(logger1.handlers)

        # Setup again (simulating re-initialization)
        logger2 = manager.setup()
        handler_count_2 = len(logger2.handlers)

        assert handler_count_1 == handler_count_2
        assert logger1 is logger2


# =============================================================================
# TEST DATE EXTRACTION
# =============================================================================


class TestDateExtraction:
    """Test date extraction from log filenames."""

    def test_extract_date_from_standard_filename(self, workspace_path):
        """Test extracting date from standard log filename."""
        manager = LogManager(workspace_path)

        log_file = workspace_path / "logs" / "research-kit-2026-01-24.log"
        date = manager._extract_date_from_filename(log_file)

        assert date == datetime(2026, 1, 24)

    def test_extract_date_from_rotated_filename(self, workspace_path):
        """Test extracting date from rotated log filename."""
        manager = LogManager(workspace_path)

        log_file = workspace_path / "logs" / "research-kit-2026-01-24.log.2026-01-23"
        date = manager._extract_date_from_filename(log_file)

        # Should extract the first date (original file date)
        assert date == datetime(2026, 1, 24)

    def test_extract_date_returns_none_for_invalid_filename(self, workspace_path):
        """Test that invalid filename returns None."""
        manager = LogManager(workspace_path)

        log_file = workspace_path / "logs" / "invalid-file.log"
        date = manager._extract_date_from_filename(log_file)

        assert date is None
