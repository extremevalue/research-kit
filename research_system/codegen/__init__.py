"""Code generation module for Tier 1 strategies.

This module provides tools for generating QuantConnect-compatible Python code
from StrategyDefinition schemas.

Key components:
- TemplateEngine: Renders strategy definitions to Python code using Jinja2
- CodeGenerator: High-level API integrating with CatalogManager
- CLI: Command-line interface for code generation

Example:
    >>> from research_system.codegen import TemplateEngine, CodeGenerator
    >>> engine = TemplateEngine()
    >>> code = engine.render(strategy)

    >>> with CodeGenerator("/path/to/catalog") as gen:
    ...     code = gen.generate("STRAT-001")
"""

from research_system.codegen.engine import CodeGenerationError, TemplateEngine
from research_system.codegen.filters import CUSTOM_FILTERS
from research_system.codegen.generator import CodeGenerator

__all__ = [
    "TemplateEngine",
    "CodeGenerator",
    "CodeGenerationError",
    "CUSTOM_FILTERS",
]
