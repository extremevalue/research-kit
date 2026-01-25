"""V4 Code Generator - Generate QuantConnect code from V4 strategy documents.

This module provides code generation capabilities for V4 strategies:
- Template-based generation for common strategy types
- LLM-based generation for complex/novel strategies
- Post-processing to fix common QC API issues

Template-first approach: Use deterministic templates when possible,
fall back to LLM for strategies that don't fit templates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import jinja2

from research_system.codegen.templates.v4 import (
    V4_TEMPLATE_DIR,
    get_template_for_v4_strategy,
)

import logging

logger = logging.getLogger(__name__)


@dataclass
class V4CodeGenResult:
    """Result of V4 code generation."""

    success: bool
    code: str | None = None
    template_used: str | None = None
    method: str = "template"  # "template" or "llm"
    error: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "code": self.code,
            "template_used": self.template_used,
            "method": self.method,
            "error": self.error,
            "warnings": self.warnings,
        }


@dataclass
class V4CodeCorrectionResult:
    """Result of code correction attempt."""

    success: bool
    corrected_code: str | None = None
    error: str | None = None
    attempt: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "corrected_code": self.corrected_code,
            "error": self.error,
            "attempt": self.attempt,
        }


class V4CodeGenerator:
    """Generate QuantConnect Python code for V4 strategies.

    Uses a template-first approach:
    1. Check if strategy matches a known template
    2. If yes, use Jinja2 template for deterministic code generation
    3. If no, fall back to LLM-based generation

    Post-processes all generated code to fix common QC API issues.
    """

    def __init__(self, llm_client=None):
        """Initialize the code generator.

        Args:
            llm_client: Optional LLM client for fallback generation
        """
        self.llm_client = llm_client
        self._jinja_env = self._setup_jinja_env()

    def _setup_jinja_env(self) -> jinja2.Environment:
        """Set up Jinja2 environment with V4 templates."""
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(V4_TEMPLATE_DIR)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(
        self,
        strategy: dict[str, Any],
        force_llm: bool = False,
    ) -> V4CodeGenResult:
        """Generate QuantConnect code for a strategy.

        Args:
            strategy: Strategy document dictionary
            force_llm: If True, skip template matching and use LLM

        Returns:
            V4CodeGenResult with generated code or error
        """
        strategy_id = strategy.get("id", "unknown")
        logger.info(f"Generating code for {strategy_id}")

        # Try template-based generation first (unless forced to LLM)
        if not force_llm and self._matches_template(strategy):
            result = self._generate_from_template(strategy)
            if result.success:
                # Post-process to fix common issues
                result.code = self._fix_qc_api_issues(result.code)
                return result
            # If template failed, fall through to LLM
            logger.warning(f"Template generation failed for {strategy_id}, trying LLM")

        # LLM-based generation
        if self.llm_client:
            result = self._generate_from_llm(strategy)
            if result.success:
                result.code = self._fix_qc_api_issues(result.code)
            return result
        else:
            return V4CodeGenResult(
                success=False,
                error="No LLM client available and strategy doesn't match template",
            )

    def _matches_template(self, strategy: dict[str, Any]) -> bool:
        """Check if strategy matches a known template.

        Args:
            strategy: Strategy document

        Returns:
            True if a suitable template exists
        """
        strategy_type = strategy.get("strategy_type", "")
        signal_type = strategy.get("signal_type", "")

        # Check parameters - need at least some defined
        params = strategy.get("parameters", {})
        if not params:
            # No parameters = probably needs LLM
            return False

        template = get_template_for_v4_strategy(strategy_type, signal_type)
        return template != "base.py.j2"

    def _generate_from_template(self, strategy: dict[str, Any]) -> V4CodeGenResult:
        """Generate code using Jinja2 template.

        Args:
            strategy: Strategy document

        Returns:
            V4CodeGenResult with generated code
        """
        try:
            strategy_type = strategy.get("strategy_type", "")
            signal_type = strategy.get("signal_type", "")
            template_name = get_template_for_v4_strategy(strategy_type, signal_type)

            template = self._jinja_env.get_template(template_name)

            # Prepare template context
            context = self._prepare_template_context(strategy)

            # Render template
            code = template.render(**context)

            return V4CodeGenResult(
                success=True,
                code=code,
                template_used=template_name,
                method="template",
            )

        except jinja2.TemplateNotFound as e:
            return V4CodeGenResult(
                success=False,
                error=f"Template not found: {e}",
            )
        except jinja2.TemplateError as e:
            return V4CodeGenResult(
                success=False,
                error=f"Template rendering error: {e}",
            )
        except Exception as e:
            return V4CodeGenResult(
                success=False,
                error=f"Code generation error: {e}",
            )

    def _prepare_template_context(self, strategy: dict[str, Any]) -> dict[str, Any]:
        """Prepare context variables for template rendering.

        Args:
            strategy: Strategy document

        Returns:
            Dictionary of template variables
        """
        strategy_id = strategy.get("id", "STRAT-000")

        # Generate class name from strategy ID
        class_name = "".join(word.capitalize() for word in strategy_id.replace("-", " ").split())
        class_name = f"{class_name}Algorithm"

        return {
            "strategy": strategy,
            "class_name": class_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def _generate_from_llm(self, strategy: dict[str, Any]) -> V4CodeGenResult:
        """Generate code using LLM.

        Args:
            strategy: Strategy document

        Returns:
            V4CodeGenResult with generated code
        """
        if not self.llm_client:
            return V4CodeGenResult(
                success=False,
                error="No LLM client configured",
            )

        try:
            prompt = self._build_llm_prompt(strategy)
            response = self.llm_client.generate(prompt)

            # Extract code from response (response.content is the text)
            code = self._extract_code_from_response(response.content)
            if not code:
                return V4CodeGenResult(
                    success=False,
                    error="LLM response did not contain valid Python code",
                )

            return V4CodeGenResult(
                success=True,
                code=code,
                method="llm",
            )

        except Exception as e:
            return V4CodeGenResult(
                success=False,
                error=f"LLM generation failed: {e}",
            )

    def correct_code_error(
        self,
        original_code: str,
        error_message: str,
        strategy: dict[str, Any],
        attempt: int = 1,
    ) -> V4CodeCorrectionResult:
        """Attempt to correct code based on backtest error.

        Args:
            original_code: The code that failed
            error_message: Error from backtest
            strategy: Original strategy document
            attempt: Current correction attempt number

        Returns:
            V4CodeCorrectionResult with corrected code or error
        """
        if not self.llm_client:
            return V4CodeCorrectionResult(
                success=False,
                error="No LLM client available for correction",
                attempt=attempt,
            )

        try:
            prompt = self._build_correction_prompt(original_code, error_message, strategy)
            response = self.llm_client.generate(prompt)
            corrected = self._extract_code_from_response(response.content)

            if not corrected:
                return V4CodeCorrectionResult(
                    success=False,
                    error="Could not extract corrected code from LLM response",
                    attempt=attempt,
                )

            # Apply post-processing fixes
            corrected = self._fix_qc_api_issues(corrected)

            return V4CodeCorrectionResult(
                success=True,
                corrected_code=corrected,
                attempt=attempt,
            )

        except Exception as e:
            return V4CodeCorrectionResult(
                success=False,
                error=f"Correction failed: {e}",
                attempt=attempt,
            )

    def _build_correction_prompt(
        self,
        code: str,
        error: str,
        strategy: dict[str, Any],
    ) -> str:
        """Build prompt for error correction."""
        return f"""The following QuantConnect algorithm failed with an error.
Fix the code to resolve the error.

STRATEGY: {strategy.get('name', 'Unknown')}
STRATEGY ID: {strategy.get('id', 'unknown')}

ERROR:
{error}

FAILED CODE:
```python
{code}
```

COMMON FIXES:
- Resolution enum uses UPPERCASE: Resolution.DAILY, Resolution.MINUTE, Resolution.HOUR
- Algorithm methods use snake_case: self.add_equity(), self.set_holdings(), self.liquidate()
- Option filter methods use PascalCase (exception): .IncludeWeeklys(), .Strikes(), .Expiration()
- Options require DataNormalizationMode.RAW on underlying:
  equity = self.add_equity("SPY", Resolution.MINUTE)
  equity.set_data_normalization_mode(DataNormalizationMode.RAW)
- Always check if indicators are ready before using: if not self.sma.is_ready: return
- Access data safely: bar = data.bars.get(symbol); if bar is None: return
- Use self.history() for historical data, not self.History()
- Import everything from AlgorithmImports: from AlgorithmImports import *

Return ONLY the corrected Python code, no explanations."""

    def _build_llm_prompt(self, strategy: dict[str, Any]) -> str:
        """Build LLM prompt for code generation."""
        return f"""Generate a QuantConnect Python algorithm for this strategy:

Strategy ID: {strategy.get('id', 'unknown')}
Name: {strategy.get('name', 'Unknown Strategy')}
Description: {strategy.get('description', 'No description')}

Signal Type: {strategy.get('signal_type', 'Not specified')}
Strategy Type: {strategy.get('strategy_type', 'Not specified')}

Parameters:
{self._format_parameters(strategy.get('parameters', {}))}

Universe: {strategy.get('universe', ['SPY'])}

CRITICAL - Use these EXACT QuantConnect Python API patterns:

1. Resolution enum (ALL CAPS): Resolution.DAILY, Resolution.HOUR
2. Adding securities (snake_case): self.add_equity("SPY", Resolution.DAILY)
3. Indicators (snake_case): self.rsi("SPY", 14), self.sma("SPY", 50)
4. Safe data access: bar = data.bars.get(self.spy); if bar is None: return
5. Trading: self.set_holdings("SPY", 1.0), self.liquidate()
6. Benchmark: self.set_benchmark("SPY")

IMPORTANT: Do NOT set dates in the code - they are injected by the framework.
IMPORTANT: Use snake_case for all QuantConnect methods.
IMPORTANT: Always check if indicators are ready before using them.

FOR OPTIONS STRATEGIES:
- MUST set DataNormalizationMode.Raw on the underlying equity:
  equity = self.add_equity("SPY", Resolution.MINUTE)
  equity.set_data_normalization_mode(DataNormalizationMode.RAW)
- Add options with: option = self.add_option("SPY")
- Option filter methods use PascalCase (exception to snake_case rule):
  option.set_filter(lambda u: u.IncludeWeeklys().Strikes(-5, 5).Expiration(7, 45))
  Note: It's "IncludeWeeklys" (not "Weeklies"), "Strikes", "Expiration" (PascalCase)

Return ONLY the Python code, no explanations."""

    def _format_parameters(self, params: dict[str, Any]) -> str:
        """Format parameters for prompt."""
        if not params:
            return "  None specified"
        lines = []
        for key, value in params.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def _extract_code_from_response(self, response: str) -> str | None:
        """Extract Python code from LLM response."""
        # Look for code blocks
        code_block_match = re.search(r"```(?:python)?\s*(.*?)```", response, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1).strip()

        # If no code block, check if the entire response is code
        if "class " in response and "def " in response:
            return response.strip()

        return None

    def _fix_qc_api_issues(self, code: str) -> str:
        """Post-process code to fix common QC API issues.

        Args:
            code: Generated Python code

        Returns:
            Fixed code
        """
        # Fix 1: Ensure proper import
        if "from AlgorithmImports import *" not in code:
            code = "from AlgorithmImports import *\n" + code

        # Fix 2: Replace PascalCase with snake_case for common methods
        replacements = [
            (r"\.SetCash\(", ".set_cash("),
            (r"\.SetStartDate\(", ".set_start_date("),
            (r"\.SetEndDate\(", ".set_end_date("),
            (r"\.SetBenchmark\(", ".set_benchmark("),
            (r"\.SetWarmUp\(", ".set_warm_up("),
            (r"\.AddEquity\(", ".add_equity("),
            (r"\.AddCrypto\(", ".add_crypto("),
            (r"\.AddFuture\(", ".add_future("),
            (r"\.SetHoldings\(", ".set_holdings("),
            (r"\.Liquidate\(", ".liquidate("),
            (r"\.IsWarmingUp", ".is_warming_up"),
            (r"\.Portfolio", ".portfolio"),
            (r"\.Securities", ".securities"),
            (r"\.Time", ".time"),
            (r"\.History\(", ".history("),
            (r"\.Schedule\.On\(", ".schedule.on("),
            (r"\.DateRules\.", ".date_rules."),
            (r"\.TimeRules\.", ".time_rules."),
        ]

        for pattern, replacement in replacements:
            code = re.sub(pattern, replacement, code)

        # Fix 3: Ensure Resolution is uppercase
        code = re.sub(r"Resolution\.daily", "Resolution.DAILY", code, flags=re.IGNORECASE)
        code = re.sub(r"Resolution\.hour", "Resolution.HOUR", code, flags=re.IGNORECASE)
        code = re.sub(r"Resolution\.minute", "Resolution.MINUTE", code, flags=re.IGNORECASE)

        # Fix 4: Option filter methods use PascalCase (opposite of algorithm methods)
        option_filter_replacements = [
            (r"\.include_weeklies\(\)", ".IncludeWeeklys()"),
            (r"\.include_weeklys\(\)", ".IncludeWeeklys()"),
            (r"\.strikes\(", ".Strikes("),
            (r"\.expiration\(", ".Expiration("),
            (r"\.contracts\(", ".Contracts("),
            (r"\.front_month\(\)", ".FrontMonth()"),
            (r"\.back_months\(\)", ".BackMonths()"),
            (r"\.back_month\(\)", ".BackMonth()"),
            (r"\.calls_only\(\)", ".CallsOnly()"),
            (r"\.puts_only\(\)", ".PutsOnly()"),
        ]

        for pattern, replacement in option_filter_replacements:
            code = re.sub(pattern, replacement, code, flags=re.IGNORECASE)

        # Fix 5: Add warning for potential issues
        warnings = []

        # Check for hardcoded dates
        if re.search(r"set_start_date\(\d{4},", code):
            warnings.append("Contains hardcoded dates - framework will override")

        # Check for missing benchmark
        if "set_benchmark" not in code:
            # Add benchmark after set_cash
            code = re.sub(
                r"(self\.set_cash\([^)]+\))",
                r"\1\n        self.set_benchmark('SPY')",
                code,
            )

        # Fix 5: Options strategies require DataNormalizationMode.Raw on underlying
        options_patterns = [
            r"add_option\(",
            r"add_option_contract\(",
            r"option_chain",
            r"OptionChain",
        ]
        is_options_strategy = any(re.search(p, code, re.IGNORECASE) for p in options_patterns)

        if is_options_strategy and "DataNormalizationMode" not in code:
            # Add normalization mode after add_equity calls
            code = re.sub(
                r"((\w+)\s*=\s*self\.add_equity\([^)]+\))",
                r"\1\n        \2.set_data_normalization_mode(DataNormalizationMode.RAW)",
                code,
            )

        return code


def generate_v4_code(
    strategy: dict[str, Any],
    llm_client=None,
    force_llm: bool = False,
) -> V4CodeGenResult:
    """Convenience function to generate V4 code.

    Args:
        strategy: Strategy document
        llm_client: Optional LLM client
        force_llm: Force LLM generation

    Returns:
        V4CodeGenResult
    """
    generator = V4CodeGenerator(llm_client)
    return generator.generate(strategy, force_llm=force_llm)
