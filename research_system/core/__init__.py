"""Core modules for Research Validation System."""

from .workspace import (
    Workspace,
    WorkspaceConfig,
    WorkspaceError,
    QCCredentials,
    get_workspace,
    require_workspace,
    WORKSPACE_ENV_VAR,
    DEFAULT_WORKSPACE,
)

from .catalog import (
    Catalog,
    CatalogEntry,
    CatalogQuery,
    CatalogStats,
)

from .data_registry import (
    DataRegistry,
    DataSource,
    DataAvailability,
)

# V4 system re-exports (for clean access without .v4 subpath)
# NOTE: Workspace, WorkspaceError, get_workspace, require_workspace,
# DEFAULT_WORKSPACE, and WORKSPACE_ENV_VAR are NOT re-exported here under
# their short names because the legacy workspace already claims those names.
# Use the V4-prefixed aliases instead, or import from core.v4 directly.
from research_system.core.v4 import (
    # Config models (no collision)
    Config,
    V4Config,
    GatesConfig,
    IngestionConfig,
    VerificationConfig,
    ScoringConfig,
    RedFlagsConfig,
    BacktestConfig as V4BacktestConfig,
    LoggingConfig,
    APIConfig,
    # Config functions (no collision)
    load_config,
    get_default_config,
    validate_config,
    ConfigurationError,
    # Logging (no collision)
    setup_logging,
    get_logger,
    LogManager,
    V4LogManager,
    # V4-prefixed workspace aliases (safe, no collision with legacy names)
    V4Workspace,
    V4WorkspaceError,
    get_v4_workspace,
    require_v4_workspace,
    DEFAULT_V4_WORKSPACE,
)

# Alias for the V4 workspace env var (avoids collision with legacy WORKSPACE_ENV_VAR)
from research_system.core.v4 import WORKSPACE_ENV_VAR as V4_WORKSPACE_ENV_VAR

__all__ = [
    # Workspace
    "Workspace",
    "WorkspaceConfig",
    "WorkspaceError",
    "QCCredentials",
    "get_workspace",
    "require_workspace",
    "WORKSPACE_ENV_VAR",
    "DEFAULT_WORKSPACE",
    # Catalog
    "Catalog",
    "CatalogEntry",
    "CatalogQuery",
    "CatalogStats",
    # Data Registry
    "DataRegistry",
    "DataSource",
    "DataAvailability",
    # V4 Config
    "Config",
    "V4Config",
    "GatesConfig",
    "IngestionConfig",
    "VerificationConfig",
    "ScoringConfig",
    "RedFlagsConfig",
    "V4BacktestConfig",
    "LoggingConfig",
    "APIConfig",
    "load_config",
    "get_default_config",
    "validate_config",
    "ConfigurationError",
    # V4 Logging
    "setup_logging",
    "get_logger",
    "LogManager",
    "V4LogManager",
    # V4 Workspace (prefixed aliases to avoid legacy collision)
    "V4Workspace",
    "V4WorkspaceError",
    "get_v4_workspace",
    "require_v4_workspace",
    "DEFAULT_V4_WORKSPACE",
    "V4_WORKSPACE_ENV_VAR",
]
