"""V4 Logging System.

This module provides logging configuration for the V4 research-kit system.

Features:
- Daily rotating log files with TimedRotatingFileHandler
- Configurable log levels via V4Config
- Support for multiple named loggers
- Log cleanup for old files

Log files are stored in the workspace's logs/ directory with the format:
    research-kit-YYYY-MM-DD.log

Example usage:
    from research_system.core.v4.logging import setup_logging, get_logger, LogManager

    # Simple setup
    logger = setup_logging(workspace_path)
    logger.info("Starting ingestion process")

    # Using the log manager
    log_manager = LogManager(workspace_path)
    logger = log_manager.setup()
    logger.info("Processing file")

    # Get a named logger (must call setup_logging first)
    component_logger = get_logger("research_system.ingest")
    component_logger.debug("Processing file: strategy.yaml")

    # Cleanup old logs
    log_manager.cleanup_old_logs(keep_days=30)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

from research_system.core.v4.config import V4Config, load_config


# =============================================================================
# CONSTANTS
# =============================================================================

# Default logger name
DEFAULT_LOGGER_NAME = "research_system"

# Log file prefix
LOG_FILE_PREFIX = "research-kit"

# Log file extension
LOG_FILE_EXTENSION = ".log"

# Default backup count (days to keep)
DEFAULT_BACKUP_COUNT = 30


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================


def setup_logging(
    workspace_path: Path,
    config: Optional[V4Config] = None,
    name: str = DEFAULT_LOGGER_NAME,
) -> logging.Logger:
    """Set up logging for V4 workspace.

    This is a convenience function that creates a LogManager and sets up logging.

    Args:
        workspace_path: Path to the V4 workspace.
        config: Optional V4Config, loads from workspace if not provided.
        name: Logger name (default: research_system).

    Returns:
        Configured logger instance.
    """
    log_manager = LogManager(workspace_path, config)
    return log_manager.setup(name)


def get_logger(name: str = DEFAULT_LOGGER_NAME) -> logging.Logger:
    """Get a logger instance.

    Returns the logger with the given name. The logger may not be configured yet
    if setup_logging has not been called. In that case, it will use the root
    logger's configuration or Python's default.

    Args:
        name: Logger name.

    Returns:
        Logger instance (may not be configured yet).
    """
    return logging.getLogger(name)


# =============================================================================
# LOG MANAGER CLASS
# =============================================================================


class LogManager:
    """Manages logging for V4 workspace.

    This class handles all logging configuration including:
    - Creating log directories
    - Setting up file handlers with daily rotation
    - Configuring console output
    - Cleaning up old log files

    Attributes:
        workspace_path: Path to the V4 workspace.
        config: V4 configuration.
        logs_path: Path to the logs directory.
    """

    def __init__(self, workspace_path: Path, config: Optional[V4Config] = None):
        """Initialize log manager.

        Args:
            workspace_path: Path to the V4 workspace.
            config: Optional V4Config, loads from workspace if not provided.
        """
        self.workspace_path = Path(workspace_path)
        self.logs_path = self.workspace_path / "logs"

        # Load config from workspace if not provided
        if config is not None:
            self.config = config
        else:
            config_file = self.workspace_path / "research-kit.yaml"
            if config_file.exists():
                self.config = load_config(config_file)
            else:
                # Use defaults if no config file
                from research_system.core.v4.config import get_default_config

                self.config = get_default_config()

        self._logger: Optional[logging.Logger] = None

    def setup(self, name: str = DEFAULT_LOGGER_NAME) -> logging.Logger:
        """Set up logging with file and console handlers.

        Creates the logs directory if it doesn't exist, then configures
        a logger with:
        - TimedRotatingFileHandler for daily log rotation
        - StreamHandler for console output

        Args:
            name: Logger name (default: research_system).

        Returns:
            Configured logger instance.
        """
        # Create logs directory
        self.logs_path.mkdir(parents=True, exist_ok=True)

        # Get or create logger
        logger = logging.getLogger(name)

        # Set log level from config
        log_level = getattr(logging, self.config.logging.level, logging.INFO)
        logger.setLevel(log_level)

        # Only add handlers if none exist (avoid duplicates)
        if not logger.handlers:
            # Create formatter
            formatter = logging.Formatter(self.config.logging.format)

            # File handler with daily rotation
            log_file = self.get_log_file_path()
            file_handler = TimedRotatingFileHandler(
                filename=log_file,
                when="midnight",
                interval=1,
                backupCount=DEFAULT_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)

            # Set suffix for rotated files (YYYY-MM-DD)
            file_handler.suffix = "%Y-%m-%d"

            logger.addHandler(file_handler)

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        self._logger = logger
        return logger

    def get_log_file_path(self) -> Path:
        """Get current log file path.

        Returns the path for today's log file using the format:
            workspace/logs/research-kit-YYYY-MM-DD.log

        Returns:
            Path to the current log file.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"{LOG_FILE_PREFIX}-{today}{LOG_FILE_EXTENSION}"
        return self.logs_path / filename

    def list_log_files(self) -> list[Path]:
        """List all log files in workspace.

        Returns log files sorted by name (oldest first).

        Returns:
            List of paths to log files.
        """
        if not self.logs_path.exists():
            return []

        # Match both current and rotated log files
        log_files = []

        # Current format: research-kit-YYYY-MM-DD.log
        for log_file in self.logs_path.glob(f"{LOG_FILE_PREFIX}-*{LOG_FILE_EXTENSION}"):
            log_files.append(log_file)

        # Rotated files may have additional suffix
        for log_file in self.logs_path.glob(f"{LOG_FILE_PREFIX}-*{LOG_FILE_EXTENSION}.*"):
            log_files.append(log_file)

        return sorted(log_files)

    def cleanup_old_logs(self, keep_days: int = DEFAULT_BACKUP_COUNT) -> list[Path]:
        """Remove log files older than keep_days.

        Args:
            keep_days: Number of days of logs to keep. Files older than this
                      will be deleted.

        Returns:
            List of paths to deleted files.
        """
        if not self.logs_path.exists():
            return []

        cutoff_date = datetime.now() - timedelta(days=keep_days)
        deleted_files = []

        for log_file in self.list_log_files():
            # Extract date from filename
            # Format: research-kit-YYYY-MM-DD.log or research-kit.log.YYYY-MM-DD
            file_date = self._extract_date_from_filename(log_file)

            if file_date and file_date < cutoff_date:
                try:
                    log_file.unlink()
                    deleted_files.append(log_file)
                except OSError:
                    # Skip files that can't be deleted
                    pass

        return deleted_files

    def _extract_date_from_filename(self, log_file: Path) -> Optional[datetime]:
        """Extract date from log filename.

        Handles formats:
        - research-kit-YYYY-MM-DD.log
        - research-kit-YYYY-MM-DD.log.YYYY-MM-DD (rotated)

        Args:
            log_file: Path to log file.

        Returns:
            Datetime object or None if date cannot be extracted.
        """
        filename = log_file.name

        # Try to find date pattern YYYY-MM-DD in filename
        import re

        date_pattern = r"(\d{4}-\d{2}-\d{2})"
        matches = re.findall(date_pattern, filename)

        if matches:
            # Use the first date found (the original file date)
            try:
                return datetime.strptime(matches[0], "%Y-%m-%d")
            except ValueError:
                return None

        return None


# Backward-compat aliases
V4LogManager = LogManager
