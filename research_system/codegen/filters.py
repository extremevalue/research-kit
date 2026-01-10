"""Custom Jinja2 filters for template rendering."""

import re


def snake_case(value: str) -> str:
    """Convert a string to snake_case.

    Args:
        value: String to convert (e.g., "MyStrategy" or "my-strategy")

    Returns:
        snake_case string (e.g., "my_strategy")
    """
    # Handle camelCase and PascalCase
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", value)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    # Handle hyphens and spaces
    s3 = s2.replace("-", "_").replace(" ", "_")
    return s3.lower()


def pascal_case(value: str) -> str:
    """Convert a string to PascalCase.

    Args:
        value: String to convert (e.g., "my_strategy" or "my-strategy")

    Returns:
        PascalCase string (e.g., "MyStrategy")
    """
    # Split on underscores, hyphens, and spaces
    words = re.split(r"[_\-\s]+", value)
    return "".join(word.capitalize() for word in words if word)


def format_symbols(symbols: list[str]) -> str:
    """Format a list of symbols as a Python list literal.

    Args:
        symbols: List of symbol strings

    Returns:
        Python list literal string (e.g., '["SPY", "TLT", "GLD"]')
    """
    quoted = [f'"{s}"' for s in symbols]
    return "[" + ", ".join(quoted) + "]"


def format_symbol_set(symbols: list[str]) -> str:
    """Format a list of symbols as a Python set literal.

    Args:
        symbols: List of symbol strings

    Returns:
        Python set literal string (e.g., '{"SPY", "TLT", "GLD"}')
    """
    quoted = [f'"{s}"' for s in symbols]
    return "{" + ", ".join(quoted) + "}"


def safe_identifier(value: str) -> str:
    """Convert a string to a safe Python identifier.

    Args:
        value: String to convert

    Returns:
        Valid Python identifier
    """
    # Replace non-alphanumeric characters with underscores
    result = re.sub(r"[^a-zA-Z0-9_]", "_", value)
    # Ensure it doesn't start with a number
    if result and result[0].isdigit():
        result = "_" + result
    return result


def default_if_none(value, default):
    """Return default if value is None.

    Args:
        value: Value to check
        default: Default value to return if value is None

    Returns:
        value if not None, else default
    """
    return default if value is None else value


# Registry of all custom filters
CUSTOM_FILTERS = {
    "snake_case": snake_case,
    "pascal_case": pascal_case,
    "format_symbols": format_symbols,
    "format_symbol_set": format_symbol_set,
    "safe_identifier": safe_identifier,
    "default_if_none": default_if_none,
}
