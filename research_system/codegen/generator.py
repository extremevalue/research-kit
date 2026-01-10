"""Code generator that integrates TemplateEngine with CatalogManager.

This module provides the high-level API for generating strategy code
from catalog entries.
"""

from pathlib import Path

from research_system.codegen.engine import CodeGenerationError, TemplateEngine
from research_system.db import CatalogManager
from research_system.schemas.strategy import StrategyDefinition


class CodeGenerator:
    """High-level code generator that integrates with the catalog.

    This class provides a convenient interface for generating strategy code
    from catalog entries by ID.

    Example:
        >>> generator = CodeGenerator("/path/to/catalog")
        >>> code = generator.generate("STRAT-001")
        >>> generator.generate_to_file("STRAT-001", Path("output/strategy.py"))
    """

    def __init__(self, catalog_path: str | Path | None = None):
        """Initialize the code generator.

        Args:
            catalog_path: Path to the catalog directory. If None, uses
                          current directory.
        """
        self._catalog_path = Path(catalog_path) if catalog_path else Path.cwd()
        self._engine = TemplateEngine()
        self._catalog: CatalogManager | None = None

    def _get_catalog(self) -> CatalogManager:
        """Get or create the catalog manager.

        Returns:
            CatalogManager instance
        """
        if self._catalog is None:
            self._catalog = CatalogManager(self._catalog_path)
        return self._catalog

    def generate(self, strategy_id: str) -> str:
        """Generate code for a strategy by ID.

        Args:
            strategy_id: The strategy ID (e.g., "STRAT-001")

        Returns:
            Generated Python code as a string

        Raises:
            CodeGenerationError: If strategy not found or generation fails
        """
        strategy = self._lookup_strategy(strategy_id)
        return self._engine.render(strategy)

    def generate_from_definition(self, strategy: StrategyDefinition) -> str:
        """Generate code directly from a strategy definition.

        Args:
            strategy: The strategy definition

        Returns:
            Generated Python code as a string

        Raises:
            CodeGenerationError: If generation fails
        """
        return self._engine.render(strategy)

    def generate_to_file(
        self,
        strategy_id: str,
        output_path: Path,
        overwrite: bool = False,
    ) -> Path:
        """Generate code for a strategy and save to file.

        Args:
            strategy_id: The strategy ID (e.g., "STRAT-001")
            output_path: Path to save the generated code
            overwrite: Whether to overwrite existing files

        Returns:
            Path to the generated file

        Raises:
            CodeGenerationError: If strategy not found or generation fails
            FileExistsError: If file exists and overwrite is False
        """
        strategy = self._lookup_strategy(strategy_id)
        self._engine.render_to_file(strategy, output_path, overwrite=overwrite)
        return output_path

    def validate(self, strategy_id: str) -> list[str]:
        """Validate generated code for a strategy without saving.

        Args:
            strategy_id: The strategy ID (e.g., "STRAT-001")

        Returns:
            List of validation error messages (empty if valid)

        Raises:
            CodeGenerationError: If strategy not found or generation fails
        """
        code = self.generate(strategy_id)
        return self._engine.validate_output(code)

    def validate_definition(self, strategy: StrategyDefinition) -> list[str]:
        """Validate generated code from a strategy definition.

        Args:
            strategy: The strategy definition

        Returns:
            List of validation error messages (empty if valid)

        Raises:
            CodeGenerationError: If generation fails
        """
        code = self._engine.render(strategy)
        return self._engine.validate_output(code)

    def _lookup_strategy(self, strategy_id: str) -> StrategyDefinition:
        """Look up a strategy definition from the catalog.

        Args:
            strategy_id: The strategy ID

        Returns:
            StrategyDefinition from the catalog

        Raises:
            CodeGenerationError: If strategy not found
        """
        catalog = self._get_catalog()

        # Get the entry from catalog
        entry = catalog.get_entry(strategy_id)
        if entry is None:
            raise CodeGenerationError(f"Strategy not found: {strategy_id}")

        # Get the full strategy definition
        strategy = catalog.get_strategy_definition(strategy_id)
        if strategy is None:
            raise CodeGenerationError(
                f"Strategy definition not found for: {strategy_id}. "
                "Entry exists but definition JSON may be missing."
            )

        return strategy

    def close(self):
        """Close the catalog connection."""
        if self._catalog is not None:
            self._catalog.close()
            self._catalog = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
