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

# Re-exports from core.v4 (for clean access without .v4 subpath)
# NOTE: Workspace, WorkspaceError, get_workspace, require_workspace,
# DEFAULT_WORKSPACE, and WORKSPACE_ENV_VAR are NOT re-exported here under
# their short names because the legacy workspace module already claims those names.
# Import from core.v4 directly for the current workspace implementation.
from research_system.core.v4 import (
    # Config models
    Config,
    V4Config,  # backward-compat alias
    GatesConfig,
    IngestionConfig,
    VerificationConfig,
    ScoringConfig,
    RedFlagsConfig,
    BacktestConfig as V4BacktestConfig,
    LoggingConfig,
    APIConfig,
    # Config functions
    load_config,
    get_default_config,
    validate_config,
    ConfigurationError,
    # Logging
    setup_logging,
    get_logger,
    LogManager,
    V4LogManager,  # backward-compat alias
    # Workspace (prefixed to avoid collision with legacy workspace module)
    V4Workspace,
    V4WorkspaceError,
    get_v4_workspace,
    require_v4_workspace,
    DEFAULT_V4_WORKSPACE,
)

# Alias (avoids collision with legacy WORKSPACE_ENV_VAR)
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
    # Config
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
    # Logging
    "setup_logging",
    "get_logger",
    "LogManager",
    "V4LogManager",
    # Workspace (prefixed aliases to avoid legacy collision)
    "V4Workspace",
    "V4WorkspaceError",
    "get_v4_workspace",
    "require_v4_workspace",
    "DEFAULT_V4_WORKSPACE",
    "V4_WORKSPACE_ENV_VAR",
]
