"""Database layer for research-kit v2.0."""

from research_system.db.connection import (
    DatabaseConnection,
    init_database,
    get_schema_version,
)
from research_system.db.catalog_manager import (
    CatalogManager,
    CatalogEntry,
)

__all__ = [
    "DatabaseConnection",
    "init_database",
    "get_schema_version",
    "CatalogManager",
    "CatalogEntry",
]
