"""Database layer for research-kit v2.0."""

from research_system.db.catalog_manager import (
    CatalogEntry,
    CatalogManager,
)
from research_system.db.connection import (
    DatabaseConnection,
    get_schema_version,
    init_database,
)

__all__ = [
    "DatabaseConnection",
    "init_database",
    "get_schema_version",
    "CatalogManager",
    "CatalogEntry",
]
