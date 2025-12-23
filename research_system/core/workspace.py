"""
Workspace Management

Handles the separation between application code and user data.
Each user has their own workspace containing their catalog, validations, and data.

The workspace path can be set via:
1. --workspace flag on any command
2. RESEARCH_WORKSPACE environment variable
3. ~/.research-workspace (default)
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


# Default workspace location
DEFAULT_WORKSPACE = Path.home() / ".research-workspace"

# Environment variable for workspace
WORKSPACE_ENV_VAR = "RESEARCH_WORKSPACE"

# Lean CLI credentials location
LEAN_CREDENTIALS_PATH = Path.home() / ".lean" / "credentials"


@dataclass
class QCCredentials:
    """QuantConnect API credentials."""
    user_id: str
    api_token: str
    organization_id: Optional[str] = None
    source: str = "unknown"  # "config", "lean_cli", or "unknown"


def _load_lean_cli_credentials() -> Optional[QCCredentials]:
    """
    Load QuantConnect credentials from Lean CLI config.

    The Lean CLI stores credentials at ~/.lean/credentials in JSON format:
    {
        "user-id": "123456",
        "api-token": "abc123...",
        "organization-id": "789" (optional)
    }

    Returns:
        QCCredentials if found, None otherwise
    """
    if not LEAN_CREDENTIALS_PATH.exists():
        return None

    try:
        with open(LEAN_CREDENTIALS_PATH, 'r') as f:
            data = json.load(f)

        user_id = data.get("user-id", "")
        api_token = data.get("api-token", "")

        if not user_id or not api_token:
            return None

        return QCCredentials(
            user_id=str(user_id),
            api_token=api_token,
            organization_id=data.get("organization-id"),
            source="lean_cli"
        )
    except (json.JSONDecodeError, IOError):
        return None


@dataclass
class WorkspaceConfig:
    """User workspace configuration."""
    name: str = "My Research Workspace"
    created_at: str = ""
    version: str = "1.0"

    # QC settings
    qc_user_id: str = ""
    qc_api_token: str = ""
    qc_organization_id: str = ""

    # Validation settings
    min_is_years: int = 15
    min_oos_years: int = 4
    base_alpha: float = 0.01
    min_sharpe_improvement: float = 0.10
    min_alpha_threshold: float = 0.01

    # Paths (relative to workspace)
    inbox_dir: str = "inbox"
    reviewed_dir: str = "reviewed"  # Processed files that didn't create entries
    catalog_dir: str = "catalog"
    data_registry_dir: str = "data-registry"
    validations_dir: str = "validations"
    combinations_dir: str = "combinations"
    work_dir: str = ".work"


class WorkspaceError(Exception):
    """Raised when workspace operations fail."""
    pass


class Workspace:
    """
    Manages a user's research workspace.

    The workspace contains all user data separate from the application:
    - inbox/: Files to ingest
    - catalog/: Research entries and their source files
      - entries/: Individual entry JSON files
      - sources/: Original files that created catalog entries
    - reviewed/: Processed files that didn't create entries (purgeable)
    - validations/: Test results
    - data-registry/: Data source definitions
    """

    WORKSPACE_DIRS = [
        "inbox",
        "reviewed",
        "catalog/entries",
        "catalog/sources",
        "data-registry/sources",
        "validations",
        "combinations",
        ".work"
    ]

    def __init__(self, path: Optional[Path] = None):
        """
        Initialize workspace at the given path.

        Args:
            path: Workspace path. If None, uses environment or default.
        """
        self.path = self._resolve_path(path)
        self._config: Optional[WorkspaceConfig] = None

    @staticmethod
    def _resolve_path(path: Optional[Path]) -> Path:
        """Resolve workspace path from argument, env, or default."""
        if path:
            return Path(path).expanduser().resolve()

        env_path = os.environ.get(WORKSPACE_ENV_VAR)
        if env_path:
            return Path(env_path).expanduser().resolve()

        return DEFAULT_WORKSPACE

    @property
    def exists(self) -> bool:
        """Check if workspace has been initialized."""
        return (self.path / "config.json").exists()

    @property
    def config(self) -> WorkspaceConfig:
        """Load workspace configuration."""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> WorkspaceConfig:
        """Load configuration from workspace."""
        config_file = self.path / "config.json"

        if not config_file.exists():
            raise WorkspaceError(
                f"Workspace not initialized at {self.path}. "
                f"Run 'research init {self.path}' first."
            )

        with open(config_file, 'r') as f:
            data = json.load(f) or {}

        return WorkspaceConfig(**data)

    def _save_config(self, config: WorkspaceConfig):
        """Save configuration to workspace."""
        config_file = self.path / "config.json"

        with open(config_file, 'w') as f:
            json.dump({
                "name": config.name,
                "created_at": config.created_at,
                "version": config.version,
                "qc_user_id": config.qc_user_id,
                "qc_api_token": config.qc_api_token,
                "qc_organization_id": config.qc_organization_id,
                "min_is_years": config.min_is_years,
                "min_oos_years": config.min_oos_years,
                "base_alpha": config.base_alpha,
                "min_sharpe_improvement": config.min_sharpe_improvement,
                "min_alpha_threshold": config.min_alpha_threshold,
                "inbox_dir": config.inbox_dir,
                "reviewed_dir": config.reviewed_dir,
                "catalog_dir": config.catalog_dir,
                "data_registry_dir": config.data_registry_dir,
                "validations_dir": config.validations_dir,
                "combinations_dir": config.combinations_dir,
                "work_dir": config.work_dir,
            }, f, indent=2)

    def init(self, name: str = "My Research Workspace", force: bool = False) -> bool:
        """
        Initialize a new workspace.

        Creates the directory structure and default configuration.

        Args:
            name: Workspace name
            force: Overwrite existing workspace

        Returns:
            True if created, False if already exists
        """
        if self.exists and not force:
            return False

        # Create directory structure
        self.path.mkdir(parents=True, exist_ok=True)

        for dir_path in self.WORKSPACE_DIRS:
            (self.path / dir_path).mkdir(parents=True, exist_ok=True)

        # Create default configuration
        config = WorkspaceConfig(
            name=name,
            created_at=datetime.utcnow().isoformat() + "Z"
        )
        self._save_config(config)
        self._config = config

        # Create default data registry
        self._create_default_registry()

        # Create empty catalog index
        self._create_empty_catalog()

        return True

    def _create_default_registry(self):
        """Create default data registry structure."""
        registry_dir = self.path / "data-registry"

        # Main registry file
        registry = {
            "version": "1.0",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "hierarchy_order": [
                "qc_native",
                "qc_object_store",
                "internal_purchased",
                "internal_curated",
                "internal_experimental"
            ],
            "data_sources": []
        }

        with open(registry_dir / "registry.json", 'w') as f:
            json.dump(registry, f, indent=2)

    def _create_empty_catalog(self):
        """Create empty catalog index."""
        catalog_dir = self.path / "catalog"

        index = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_entries": 0,
            "by_type": {},
            "by_status": {},
            "entries": []
        }

        with open(catalog_dir / "index.json", 'w') as f:
            json.dump(index, f, indent=2)

    # Path helpers
    @property
    def inbox_path(self) -> Path:
        return self.path / self.config.inbox_dir

    @property
    def reviewed_path(self) -> Path:
        """Path for processed files that didn't create entries (purgeable)."""
        return self.path / self.config.reviewed_dir

    @property
    def catalog_path(self) -> Path:
        return self.path / self.config.catalog_dir

    @property
    def entries_path(self) -> Path:
        return self.catalog_path / "entries"

    @property
    def sources_path(self) -> Path:
        """Path for source files that created catalog entries."""
        return self.catalog_path / "sources"

    @property
    def data_registry_path(self) -> Path:
        return self.path / self.config.data_registry_dir

    @property
    def validations_path(self) -> Path:
        return self.path / self.config.validations_dir

    @property
    def combinations_path(self) -> Path:
        return self.path / self.config.combinations_dir

    @property
    def work_path(self) -> Path:
        return self.path / self.config.work_dir

    def validation_path(self, component_id: str) -> Path:
        """Get validation directory for a component."""
        return self.validations_path / component_id

    def entry_path(self, entry_id: str) -> Path:
        """Get path to a catalog entry file."""
        return self.entries_path / f"{entry_id}.json"

    def require_initialized(self):
        """Raise error if workspace not initialized."""
        if not self.exists:
            raise WorkspaceError(
                f"Workspace not initialized at {self.path}. "
                f"Run 'research init {self.path}' first."
            )

    def status(self) -> Dict[str, Any]:
        """Get workspace status summary."""
        self.require_initialized()

        # Count entries
        entry_count = len(list(self.entries_path.glob("*.json")))

        # Count validations
        validation_count = len([
            d for d in self.validations_path.iterdir()
            if d.is_dir()
        ]) if self.validations_path.exists() else 0

        # Count inbox files (recursive)
        inbox_count = len([f for f in self.inbox_path.rglob("*") if f.is_file()]) if self.inbox_path.exists() else 0

        return {
            "path": str(self.path),
            "name": self.config.name,
            "created_at": self.config.created_at,
            "catalog_entries": entry_count,
            "validations": validation_count,
            "inbox_files": inbox_count,
        }

    def get_qc_credentials(self) -> Optional[QCCredentials]:
        """
        Get QuantConnect API credentials with fallback resolution.

        Resolution order:
        1. Workspace config (qc_user_id, qc_api_token, qc_organization)
        2. Lean CLI credentials (~/.lean/credentials)

        Returns:
            QCCredentials if found, None otherwise
        """
        # First try workspace config
        config = self.config
        if config.qc_user_id and config.qc_api_token:
            return QCCredentials(
                user_id=config.qc_user_id,
                api_token=config.qc_api_token,
                organization_id=config.qc_organization_id,
                source="config"
            )

        # Fall back to Lean CLI credentials
        return _load_lean_cli_credentials()


def get_workspace(path: Optional[str] = None) -> Workspace:
    """
    Get workspace instance.

    Args:
        path: Optional workspace path

    Returns:
        Workspace instance
    """
    workspace_path = Path(path) if path else None
    return Workspace(workspace_path)


def require_workspace(path: Optional[str] = None) -> Workspace:
    """
    Get workspace, raising error if not initialized.

    Args:
        path: Optional workspace path

    Returns:
        Initialized Workspace instance
    """
    ws = get_workspace(path)
    ws.require_initialized()
    return ws
