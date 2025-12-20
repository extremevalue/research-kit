"""
Logging configuration for the Research Validation System.

Provides consistent logging across all scripts with:
- Console output for interactive use
- File logging for audit trail
- Structured format for parseability
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


# Default log directory
LOG_DIR = Path(__file__).parent.parent.parent / "logs"


def setup_logging(
    name: str = "research-system",
    level: int = logging.INFO,
    log_dir: Optional[Path] = None,
    log_to_file: bool = True,
    log_to_console: bool = True
) -> logging.Logger:
    """
    Set up logging for a script.

    Args:
        name: Logger name (usually __name__ or script purpose)
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files (default: ./logs/)
        log_to_file: Whether to write to file
        log_to_console: Whether to write to console

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear any existing handlers
    logger.handlers = []

    # Format with timestamp, level, logger name, and message
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_to_file:
        log_dir = log_dir or LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)

        # Daily log file
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"{name}_{date_str}.log"

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance. Sets up default config if not already configured.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logging(name)
    return logger


class LogContext:
    """
    Context manager for logging operations with automatic success/failure logging.

    Usage:
        with LogContext(logger, "Processing file", file_path=path):
            process_file(path)
    """

    def __init__(self, logger: logging.Logger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
        self.logger.info(f"START: {self.operation} [{context_str}]")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type is None:
            self.logger.info(f"SUCCESS: {self.operation} (took {duration:.2f}s)")
        else:
            self.logger.error(f"FAILED: {self.operation} after {duration:.2f}s - {exc_type.__name__}: {exc_val}")

        # Don't suppress exceptions
        return False


def log_validation_event(
    logger: logging.Logger,
    component_id: str,
    event: str,
    details: Optional[dict] = None
):
    """
    Log a validation pipeline event with consistent format.

    Args:
        logger: Logger instance
        component_id: Component being validated (e.g., IND-002)
        event: Event name (e.g., DATA_AUDIT_PASSED, IS_TESTING_STARTED)
        details: Optional additional details
    """
    detail_str = f" | {details}" if details else ""
    logger.info(f"[{component_id}] {event}{detail_str}")


def log_gate_result(
    logger: logging.Logger,
    component_id: str,
    gate_name: str,
    passed: bool,
    reason: Optional[str] = None
):
    """
    Log a gate pass/fail result.

    Args:
        logger: Logger instance
        component_id: Component being validated
        gate_name: Name of the gate (e.g., DATA_AUDIT, SANITY_CHECK)
        passed: Whether the gate passed
        reason: Reason for failure (if failed)
    """
    status = "PASSED" if passed else "FAILED"
    reason_str = f" - {reason}" if reason and not passed else ""
    logger.info(f"[{component_id}] GATE {gate_name}: {status}{reason_str}")


if __name__ == "__main__":
    # Self-test
    logger = setup_logging("test-logger", level=logging.DEBUG)

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning")
    logger.error("This is an error")

    # Test context manager
    with LogContext(logger, "Test operation", param1="value1"):
        logger.info("Inside operation")

    # Test validation event logging
    log_validation_event(logger, "IND-002", "DATA_AUDIT_STARTED")
    log_gate_result(logger, "IND-002", "DATA_AUDIT", True)
    log_gate_result(logger, "IND-002", "SANITY_CHECK", False, "Sharpe > 2.0")

    print("\nLogging test completed. Check logs/ directory for output.")
