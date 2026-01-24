"""V4 Workspace Management.

This module provides workspace management for the V4 research-kit system.
A workspace contains all user data separate from the application code:

- inbox/: Files to ingest
- strategies/: Strategy documents organized by status
- validations/: Walk-forward validation results
- learnings/: Extracted learnings from validations
- ideas/: Strategy ideas (pre-formalization)
- personas/: Persona configurations
- archive/: Archived/rejected strategies
- logs/: Daily rotating logs

The workspace path can be set via:
1. Explicit path parameter
2. RESEARCH_WORKSPACE environment variable
3. ~/.research-workspace-v4 (default)
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from research_system.core.v4.config import V4Config, get_default_config


# =============================================================================
# CONSTANTS
# =============================================================================

# Default workspace location
DEFAULT_V4_WORKSPACE = Path.home() / ".research-workspace-v4"

# Environment variable for workspace
WORKSPACE_ENV_VAR = "RESEARCH_WORKSPACE"

# Configuration filename
CONFIG_FILENAME = "research-kit.yaml"

# State directory
STATE_DIR = ".state"

# Counter file
COUNTERS_FILE = "counters.json"

# Lock file
LOCK_FILE = "lock"

# .env template content
ENV_TEMPLATE = """# Research-Kit V4 Environment Variables
# Copy to .env and fill in values

# Anthropic API Key (for LLM calls)
ANTHROPIC_API_KEY=

# Optional: Override workspace path
# RESEARCH_WORKSPACE=

# Optional: QuantConnect credentials
# QC_USER_ID=
# QC_API_TOKEN=
"""


# =============================================================================
# EXCEPTIONS
# =============================================================================


class V4WorkspaceError(Exception):
    """Raised when V4 workspace operations fail."""

    pass


# =============================================================================
# V4 WORKSPACE CLASS
# =============================================================================


class V4Workspace:
    """V4 workspace management.

    A workspace is a directory containing all user data for the V4 research system.
    It includes configuration, strategies organized by status, validation results,
    learnings, ideas, and logs.
    """

    WORKSPACE_DIRS = [
        ".state",
        "inbox",
        "strategies/pending",
        "strategies/validated",
        "strategies/invalidated",
        "strategies/blocked",
        "validations",
        "learnings",
        "ideas",
        "personas",
        "archive",
        "logs",
    ]

    VALID_STATUSES = {"pending", "validated", "invalidated", "blocked"}

    def __init__(self, path: Path | str | None = None):
        """Initialize workspace at the given path.

        Args:
            path: Workspace path. If None, uses environment variable or default.
        """
        self.path = self._resolve_path(path)
        self._config: V4Config | None = None

    @staticmethod
    def _resolve_path(path: Path | str | None) -> Path:
        """Resolve workspace path from argument, env, or default.

        Args:
            path: Explicit path, or None to use env/default.

        Returns:
            Resolved absolute Path.
        """
        if path:
            return Path(path).expanduser().resolve()

        env_path = os.environ.get(WORKSPACE_ENV_VAR)
        if env_path:
            return Path(env_path).expanduser().resolve()

        return DEFAULT_V4_WORKSPACE

    # =========================================================================
    # EXISTENCE AND CONFIGURATION
    # =========================================================================

    @property
    def exists(self) -> bool:
        """Check if workspace has been initialized.

        Returns:
            True if research-kit.yaml exists in the workspace.
        """
        return (self.path / CONFIG_FILENAME).exists()

    @property
    def config(self) -> V4Config:
        """Load workspace configuration.

        Returns:
            V4Config loaded from research-kit.yaml, or defaults if not found.

        Raises:
            V4WorkspaceError: If workspace not initialized.
        """
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> V4Config:
        """Load configuration from workspace.

        Returns:
            V4Config loaded and validated.

        Raises:
            V4WorkspaceError: If workspace not initialized.
        """
        config_file = self.path / CONFIG_FILENAME

        if not config_file.exists():
            raise V4WorkspaceError(
                f"V4 workspace not initialized at {self.path}. "
                f"Run 'research init --v4' first."
            )

        # Load and parse YAML
        with open(config_file) as f:
            data = yaml.safe_load(f) or {}

        # Get defaults and merge
        default_dict = get_default_config().model_dump()
        merged = self._deep_merge(default_dict, data)

        return V4Config(**merged)

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries.

        Args:
            base: Base dictionary.
            override: Dictionary with values to override.

        Returns:
            Merged dictionary.
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = V4Workspace._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _save_config(self, config: V4Config) -> None:
        """Save configuration to workspace.

        Args:
            config: V4Config to save.
        """
        config_file = self.path / CONFIG_FILENAME
        # Use mode='json' to ensure enums and other types are serialized properly
        data = config.model_dump(mode="json")

        with open(config_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    # =========================================================================
    # INITIALIZATION
    # =========================================================================

    def init(self, name: str = "My V4 Research Workspace", force: bool = False) -> bool:
        """Initialize a new V4 workspace.

        Creates the directory structure, default configuration, and templates.

        Args:
            name: Workspace name for display purposes.
            force: If True, reinitialize even if workspace exists.

        Returns:
            True if created, False if already exists and force=False.

        Raises:
            V4WorkspaceError: If initialization fails.
        """
        if self.exists and not force:
            return False

        # Create directory structure
        self.path.mkdir(parents=True, exist_ok=True)

        for dir_path in self.WORKSPACE_DIRS:
            (self.path / dir_path).mkdir(parents=True, exist_ok=True)

        # Create default configuration with metadata
        config = get_default_config()
        self._save_config(config)
        self._config = config

        # Create .env.template
        self._create_env_template()

        # Initialize counters
        self._init_counters()

        return True

    def _create_env_template(self) -> None:
        """Create .env.template file."""
        env_template_path = self.path / ".env.template"
        with open(env_template_path, "w") as f:
            f.write(ENV_TEMPLATE)

    def _init_counters(self) -> None:
        """Initialize the counters.json file."""
        counters_path = self.path / STATE_DIR / COUNTERS_FILE
        counters = {"strategy": 0, "idea": 0}
        with open(counters_path, "w") as f:
            json.dump(counters, f, indent=2)

    # =========================================================================
    # ID GENERATION
    # =========================================================================

    def _read_counters(self) -> dict[str, int]:
        """Read counters from file.

        Returns:
            Dictionary with counter values.
        """
        counters_path = self.path / STATE_DIR / COUNTERS_FILE
        if not counters_path.exists():
            return {"strategy": 0, "idea": 0}

        with open(counters_path) as f:
            return json.load(f)

    def _write_counters(self, counters: dict[str, int]) -> None:
        """Write counters to file.

        Args:
            counters: Dictionary with counter values.
        """
        counters_path = self.path / STATE_DIR / COUNTERS_FILE
        with open(counters_path, "w") as f:
            json.dump(counters, f, indent=2)

    def _next_id(self, counter_name: str, prefix: str) -> str:
        """Generate next ID with thread-safe file locking.

        Args:
            counter_name: Name of the counter (e.g., "strategy", "idea").
            prefix: ID prefix (e.g., "STRAT", "IDEA").

        Returns:
            Next ID string (e.g., "STRAT-001").
        """
        lock_path = self.path / STATE_DIR / LOCK_FILE
        counters_path = self.path / STATE_DIR / COUNTERS_FILE

        # Ensure state directory and lock file exist
        (self.path / STATE_DIR).mkdir(parents=True, exist_ok=True)
        lock_path.touch(exist_ok=True)

        # Use file locking for thread safety
        with open(lock_path, "r+") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                # Read current counters
                counters = self._read_counters()

                # Increment counter
                counters[counter_name] = counters.get(counter_name, 0) + 1
                new_value = counters[counter_name]

                # Write back
                self._write_counters(counters)

                # Format ID with zero-padding
                return f"{prefix}-{new_value:03d}"
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def next_strategy_id(self) -> str:
        """Generate next strategy ID.

        Returns:
            Next strategy ID (e.g., "STRAT-001", "STRAT-002").
        """
        return self._next_id("strategy", "STRAT")

    def next_idea_id(self) -> str:
        """Generate next idea ID.

        Returns:
            Next idea ID (e.g., "IDEA-001", "IDEA-002").
        """
        return self._next_id("idea", "IDEA")

    # =========================================================================
    # PATH HELPERS
    # =========================================================================

    @property
    def inbox_path(self) -> Path:
        """Path to inbox directory for files to ingest."""
        return self.path / "inbox"

    @property
    def strategies_path(self) -> Path:
        """Path to strategies directory."""
        return self.path / "strategies"

    @property
    def validations_path(self) -> Path:
        """Path to validations directory."""
        return self.path / "validations"

    @property
    def learnings_path(self) -> Path:
        """Path to learnings directory."""
        return self.path / "learnings"

    @property
    def ideas_path(self) -> Path:
        """Path to ideas directory."""
        return self.path / "ideas"

    @property
    def personas_path(self) -> Path:
        """Path to personas directory."""
        return self.path / "personas"

    @property
    def archive_path(self) -> Path:
        """Path to archive directory."""
        return self.path / "archive"

    @property
    def logs_path(self) -> Path:
        """Path to logs directory."""
        return self.path / "logs"

    @property
    def state_path(self) -> Path:
        """Path to internal state directory."""
        return self.path / STATE_DIR

    def strategy_path(self, strategy_id: str, status: str = "pending") -> Path:
        """Get path for a strategy file.

        Args:
            strategy_id: Strategy ID (e.g., "STRAT-001").
            status: Strategy status (pending, validated, invalidated, blocked).

        Returns:
            Path to the strategy file.

        Raises:
            ValueError: If status is invalid.
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. "
                f"Must be one of: {', '.join(sorted(self.VALID_STATUSES))}"
            )

        return self.strategies_path / status / f"{strategy_id}.yaml"

    def move_strategy(self, strategy_id: str, from_status: str, to_status: str) -> Path:
        """Move strategy between status directories.

        Args:
            strategy_id: Strategy ID (e.g., "STRAT-001").
            from_status: Current status directory.
            to_status: Target status directory.

        Returns:
            New path to the strategy file.

        Raises:
            ValueError: If status is invalid.
            V4WorkspaceError: If strategy file not found.
        """
        if from_status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid from_status '{from_status}'. "
                f"Must be one of: {', '.join(sorted(self.VALID_STATUSES))}"
            )

        if to_status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid to_status '{to_status}'. "
                f"Must be one of: {', '.join(sorted(self.VALID_STATUSES))}"
            )

        source_path = self.strategy_path(strategy_id, from_status)
        target_path = self.strategy_path(strategy_id, to_status)

        if not source_path.exists():
            raise V4WorkspaceError(
                f"Strategy file not found: {source_path}"
            )

        # Ensure target directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Move the file
        shutil.move(str(source_path), str(target_path))

        return target_path

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def require_initialized(self) -> None:
        """Raise error if workspace not initialized.

        Raises:
            V4WorkspaceError: If workspace not initialized.
        """
        if not self.exists:
            raise V4WorkspaceError(
                f"V4 workspace not initialized at {self.path}. "
                f"Run 'research init --v4' first."
            )

    def status(self) -> dict[str, Any]:
        """Get workspace status summary.

        Returns:
            Dictionary with workspace status information.
        """
        self.require_initialized()

        # Count strategies by status
        strategy_counts = {}
        for status in self.VALID_STATUSES:
            status_dir = self.strategies_path / status
            if status_dir.exists():
                strategy_counts[status] = len(list(status_dir.glob("*.yaml")))
            else:
                strategy_counts[status] = 0

        # Count other items
        idea_count = len(list(self.ideas_path.glob("*.yaml"))) if self.ideas_path.exists() else 0
        validation_count = len(list(self.validations_path.iterdir())) if self.validations_path.exists() else 0
        inbox_count = len([f for f in self.inbox_path.rglob("*") if f.is_file()]) if self.inbox_path.exists() else 0

        # Get counters
        counters = self._read_counters()

        return {
            "path": str(self.path),
            "strategies": strategy_counts,
            "ideas": idea_count,
            "validations": validation_count,
            "inbox_files": inbox_count,
            "counters": counters,
        }

    def list_strategies(
        self,
        status: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """List strategies in the workspace.

        Args:
            status: Filter by status (pending, validated, invalidated, blocked).
                    If None, lists all strategies.
            tags: Filter by tags (strategies must have all specified tags).
                  If None, no tag filtering.

        Returns:
            List of strategy summaries with id, name, status, created, tags.
        """
        self.require_initialized()

        strategies = []
        statuses_to_check = [status] if status else list(self.VALID_STATUSES)

        for check_status in statuses_to_check:
            status_dir = self.strategies_path / check_status
            if not status_dir.exists():
                continue

            for yaml_file in status_dir.glob("*.yaml"):
                try:
                    with open(yaml_file) as f:
                        data = yaml.safe_load(f) or {}

                    # Extract summary fields
                    strategy_id = data.get("id", yaml_file.stem)
                    name = data.get("name", "Unknown")
                    created = data.get("created")
                    strategy_tags = data.get("tags", {})

                    # Handle tags - could be dict with 'custom' key or list
                    if isinstance(strategy_tags, dict):
                        tag_list = strategy_tags.get("custom", [])
                    elif isinstance(strategy_tags, list):
                        tag_list = strategy_tags
                    else:
                        tag_list = []

                    # Apply tag filter
                    if tags:
                        if not all(t in tag_list for t in tags):
                            continue

                    # Parse created date if string
                    if isinstance(created, str):
                        try:
                            created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        except ValueError:
                            pass

                    strategies.append({
                        "id": strategy_id,
                        "name": name,
                        "status": check_status,
                        "created": created,
                        "tags": tag_list,
                        "file": str(yaml_file),
                    })

                except Exception as e:
                    # Skip malformed files but log them
                    strategies.append({
                        "id": yaml_file.stem,
                        "name": f"<error: {e}>",
                        "status": check_status,
                        "created": None,
                        "tags": [],
                        "file": str(yaml_file),
                    })

        # Sort by created date (newest first), with None dates at the end
        strategies.sort(
            key=lambda s: (s["created"] is None, s["created"] or datetime.min),
            reverse=True
        )

        return strategies

    def get_strategy(self, strategy_id: str) -> dict[str, Any] | None:
        """Get a strategy by ID.

        Args:
            strategy_id: Strategy ID (e.g., "STRAT-001").

        Returns:
            Strategy data as dict, or None if not found.
        """
        self.require_initialized()

        # Search all status directories
        for status in self.VALID_STATUSES:
            yaml_file = self.strategies_path / status / f"{strategy_id}.yaml"
            if yaml_file.exists():
                with open(yaml_file) as f:
                    data = yaml.safe_load(f) or {}
                data["_file"] = str(yaml_file)
                data["_status"] = status
                return data

        return None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_v4_workspace(path: str | Path | None = None) -> V4Workspace:
    """Get V4 workspace instance.

    Args:
        path: Optional workspace path.

    Returns:
        V4Workspace instance.
    """
    workspace_path = Path(path) if path else None
    return V4Workspace(workspace_path)


def require_v4_workspace(path: str | Path | None = None) -> V4Workspace:
    """Get V4 workspace, raising error if not initialized.

    Args:
        path: Optional workspace path.

    Returns:
        Initialized V4Workspace instance.

    Raises:
        V4WorkspaceError: If workspace not initialized.
    """
    ws = get_v4_workspace(path)
    ws.require_initialized()
    return ws
