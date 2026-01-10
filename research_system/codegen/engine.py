"""Template engine for generating strategy code from schema definitions."""

import ast
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from research_system.codegen.filters import CUSTOM_FILTERS
from research_system.codegen.templates import TEMPLATE_DIR, get_template_for_strategy
from research_system.schemas.strategy import StrategyDefinition


class CodeGenerationError(Exception):
    """Error during code generation."""

    pass


class TemplateEngine:
    """Engine for rendering strategy definitions to Python code.

    This engine uses Jinja2 templates to generate QuantConnect-compatible
    Python code from structured StrategyDefinition schemas.

    Design principles:
    - No hardcoded dates in generated code
    - Deterministic output (same input = same output)
    - All parameters injected from schema
    """

    def __init__(self, template_dir: Path | None = None):
        """Initialize the template engine.

        Args:
            template_dir: Optional custom template directory. Defaults to
                          the built-in templates.
        """
        self._template_dir = template_dir or TEMPLATE_DIR
        self._env = Environment(
            loader=FileSystemLoader(self._template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        # Register custom filters
        for name, func in CUSTOM_FILTERS.items():
            self._env.filters[name] = func

    def render(self, strategy: StrategyDefinition) -> str:
        """Render a strategy definition to Python code.

        Args:
            strategy: The strategy definition to render

        Returns:
            Generated Python code as a string

        Raises:
            CodeGenerationError: If rendering fails
        """
        # Build template context from strategy
        context = self._build_context(strategy)

        # Select appropriate template
        template_name = self._select_template(strategy)

        try:
            template = self._env.get_template(template_name)
            code = template.render(**context)
            return code
        except TemplateNotFound as e:
            raise CodeGenerationError(f"Template not found: {e}") from e
        except Exception as e:
            raise CodeGenerationError(f"Template rendering failed: {e}") from e

    def render_to_file(
        self, strategy: StrategyDefinition, output_path: Path, overwrite: bool = False
    ) -> None:
        """Render a strategy definition and save to file.

        Args:
            strategy: The strategy definition to render
            output_path: Path to save the generated code
            overwrite: Whether to overwrite existing files

        Raises:
            CodeGenerationError: If rendering or file writing fails
            FileExistsError: If file exists and overwrite is False
        """
        if output_path.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {output_path}")

        code = self.render(strategy)

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_path.write_text(code)

    def validate_output(self, code: str) -> list[str]:
        """Validate generated code for common issues.

        Args:
            code: The generated Python code

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check Python syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")

        # Check for hardcoded dates (common bug in v1.0)
        date_patterns = [
            r"SetStartDate\s*\(",
            r"SetEndDate\s*\(",
            r"\b20[0-2][0-9],\s*[1-9]|1[0-2],\s*[1-3]?[0-9]\b",  # Date literals like 2020, 1, 15
        ]
        for pattern in date_patterns:
            if re.search(pattern, code):
                errors.append(
                    f"Potential hardcoded date detected (pattern: {pattern}). "
                    "Dates should be controlled by the framework."
                )

        # Check for required imports
        if "from AlgorithmImports import" not in code:
            errors.append("Missing required import: AlgorithmImports")

        # Check for class definition
        if "class " not in code or "(QCAlgorithm)" not in code:
            errors.append("Missing QCAlgorithm class definition")

        # Check for Initialize method
        if "def Initialize(self)" not in code:
            errors.append("Missing Initialize method")

        return errors

    def _build_context(self, strategy: StrategyDefinition) -> dict:
        """Build the template context from a strategy definition.

        Args:
            strategy: The strategy definition

        Returns:
            Dictionary of template variables
        """
        # Generate class name from strategy ID
        class_name = self._generate_class_name(strategy)

        # Build context with all strategy fields
        context = {
            "class_name": class_name,
            "schema_version": strategy.schema_version,
            "tier": strategy.tier,
            "strategy_type": strategy.strategy_type,
            "metadata": {
                "id": strategy.metadata.id,
                "name": strategy.metadata.name,
                "description": strategy.metadata.description,
                "tags": strategy.metadata.tags,
            },
            "universe": {
                "type": strategy.universe.type.value if strategy.universe.type else None,
                "symbols": strategy.universe.symbols,
                "defensive_symbols": strategy.universe.defensive_symbols,
                "index": strategy.universe.index,
                "sector": strategy.universe.sector,
            },
            "position_sizing": {
                "method": (
                    strategy.position_sizing.method.value
                    if strategy.position_sizing.method
                    else None
                ),
                "leverage": strategy.position_sizing.leverage,
                "max_position_size": strategy.position_sizing.max_position_size,
                "target_volatility": strategy.position_sizing.target_volatility,
            },
            "rebalance": {
                "frequency": (
                    strategy.rebalance.frequency.value if strategy.rebalance.frequency else None
                ),
                "on_signal_change": strategy.rebalance.on_signal_change,
                "threshold": strategy.rebalance.threshold,
            },
        }

        # Add signal config if present
        if strategy.signal:
            context["signal"] = {
                "type": strategy.signal.type.value if strategy.signal.type else None,
                "lookback_days": strategy.signal.lookback_days,
                "selection_method": strategy.signal.selection_method,
                "selection_n": strategy.signal.selection_n,
                "threshold": strategy.signal.threshold,
            }
        else:
            context["signal"] = None

        # Add risk management if present
        if strategy.risk_management:
            context["risk_management"] = strategy.risk_management.model_dump()
        else:
            context["risk_management"] = None

        # Add filters if present
        context["filters"] = [f.model_dump() for f in strategy.filters]

        return context

    def _select_template(self, strategy: StrategyDefinition) -> str:
        """Select the appropriate template for a strategy.

        Args:
            strategy: The strategy definition

        Returns:
            Template filename

        Raises:
            CodeGenerationError: If no template found for strategy type
        """
        signal_type = (
            strategy.signal.type.value if strategy.signal and strategy.signal.type else None
        )
        try:
            return get_template_for_strategy(strategy.strategy_type, signal_type)
        except ValueError as e:
            raise CodeGenerationError(str(e)) from e

    def _generate_class_name(self, strategy: StrategyDefinition) -> str:
        """Generate a Python class name from the strategy.

        Args:
            strategy: The strategy definition

        Returns:
            Valid Python class name
        """
        # Use strategy ID as base, converting to PascalCase
        base = strategy.metadata.id.replace("-", "_")
        words = base.split("_")
        class_name = "".join(word.capitalize() for word in words)

        # Ensure it's a valid identifier
        if not class_name.isidentifier():
            class_name = "Strategy" + class_name

        return class_name
