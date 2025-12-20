"""Core modules for Research Validation System."""

from .workspace import (
    Workspace,
    WorkspaceConfig,
    WorkspaceError,
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

__all__ = [
    # Workspace
    "Workspace",
    "WorkspaceConfig",
    "WorkspaceError",
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
]
