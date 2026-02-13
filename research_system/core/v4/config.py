"""V4 Configuration System.

This module provides the configuration system for V4 research-kit, including:
- Pydantic models for all configuration sections
- YAML file loading with default fallbacks
- Partial config merging
- Validation with clear error messages
- Environment variable support for sensitive values

Configuration is loaded from research-kit.yaml files. If no file exists,
sensible defaults are used. Partial configurations are merged with defaults.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# EXCEPTIONS
# =============================================================================


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""

    pass


# =============================================================================
# ENUMS
# =============================================================================


class LogLevel(str, Enum):
    """Logging level options."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# =============================================================================
# CONFIGURATION MODELS
# =============================================================================


class GatesConfig(BaseModel):
    """Validation gate thresholds.

    These thresholds define the minimum requirements a strategy must meet
    during walk-forward validation to be considered validated.
    """

    min_sharpe: float = Field(
        1.0, ge=0, description="Minimum Sharpe ratio required"
    )
    min_consistency: float = Field(
        0.6, ge=0, le=1.0, description="Minimum consistency (% of windows profitable)"
    )
    max_drawdown: float = Field(
        0.25, ge=0, le=1.0, description="Maximum allowed drawdown (as decimal, e.g., 0.25 for 25%)"
    )
    min_cagr: float = Field(
        0.05, ge=0, description="Minimum CAGR required"
    )
    min_trades: int = Field(
        30, ge=0, description="Minimum number of trades required"
    )


class IngestionConfig(BaseModel):
    """Ingestion quality thresholds.

    These thresholds filter strategies during ingestion before they
    enter the validation pipeline.
    """

    min_specificity_score: int = Field(
        4, ge=0, le=8, description="Minimum specificity score (0-8 scale)"
    )
    min_trust_score: int = Field(
        50, ge=0, le=100, description="Minimum trust score (0-100 scale)"
    )


class VerificationConfig(BaseModel):
    """Verification test settings.

    Verification tests are run before validation to catch issues like
    look-ahead bias, survivorship bias, etc.
    """

    enabled: bool = Field(True, description="Whether verification is enabled")
    tests: list[str] = Field(
        default_factory=lambda: [
            "look_ahead_bias",
            "survivorship_bias",
            "position_sizing",
            "data_availability",
            "parameter_sanity",
        ],
        description="List of verification tests to run",
    )

    @field_validator("tests")
    @classmethod
    def validate_tests(cls, v: list[str]) -> list[str]:
        """Validate that test names are valid."""
        valid_tests = {
            "look_ahead_bias",
            "survivorship_bias",
            "position_sizing",
            "data_availability",
            "parameter_sanity",
            "hardcoded_values",
        }
        for test in v:
            if test not in valid_tests:
                raise ValueError(
                    f"Invalid verification test '{test}'. "
                    f"Valid tests: {', '.join(sorted(valid_tests))}"
                )
        return v


class ScoringConfig(BaseModel):
    """Trust score calculation weights.

    These weights determine how different factors contribute to the
    overall trust score during ingestion.
    """

    economic_rationale_weight: int = Field(
        30, ge=0, le=100, description="Weight for economic rationale (0-30)"
    )
    out_of_sample_weight: int = Field(
        25, ge=0, le=100, description="Weight for out-of-sample evidence (0-25)"
    )
    implementation_realism_weight: int = Field(
        20, ge=0, le=100, description="Weight for implementation realism (0-20)"
    )
    source_credibility_weight: int = Field(
        15, ge=0, le=100, description="Weight for source credibility (0-15)"
    )
    novelty_weight: int = Field(
        10, ge=0, le=100, description="Weight for novelty (0-10)"
    )

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "ScoringConfig":
        """Validate that weights sum to 100."""
        total = (
            self.economic_rationale_weight
            + self.out_of_sample_weight
            + self.implementation_realism_weight
            + self.source_credibility_weight
            + self.novelty_weight
        )
        if total != 100:
            raise ValueError(
                f"Scoring weights must sum to 100, got {total}. "
                f"Adjust weights to total 100."
            )
        return self


class RedFlagsConfig(BaseModel):
    """Red flag configuration for ingestion filtering.

    Hard reject flags cause immediate rejection.
    Soft warning flags require investigation but don't auto-reject.
    """

    hard_reject: list[str] = Field(
        default_factory=lambda: [
            "sharpe_above_3",
            "no_losing_periods",
            "author_selling",
            "excessive_parameters",
            "convenient_start_date",
        ],
        description="Red flags that cause immediate rejection",
    )
    soft_warning: list[str] = Field(
        default_factory=lambda: [
            "works_all_conditions",
            "unknown_rationale",
            "no_transaction_costs",
            "no_drawdown_mentioned",
            "single_market",
            "single_regime",
            "small_sample",
            "high_leverage",
            "crowded_factor",
            "magic_numbers",
        ],
        description="Red flags that trigger warnings but not rejection",
    )


class BacktestConfig(BaseModel):
    """Backtest execution configuration.

    Controls timeouts and other execution parameters for backtests.
    """

    timeout: int = Field(
        600, ge=60, description="Backtest execution timeout in seconds (default: 600)"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: LogLevel = Field(LogLevel.INFO, description="Logging level")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )


class APIConfig(BaseModel):
    """API configuration.

    API keys can be specified here or via environment variables.
    Environment variables take precedence.
    """

    anthropic_model: str = Field(
        "claude-3-5-sonnet-20241022",
        description="Anthropic model to use for LLM operations",
    )
    anthropic_api_key: str | None = Field(
        None,
        description="Anthropic API key (can also be set via ANTHROPIC_API_KEY env var)",
    )

    @model_validator(mode="after")
    def resolve_env_vars(self) -> "APIConfig":
        """Resolve API keys from environment variables if not set."""
        if self.anthropic_api_key is None:
            self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        return self


class Config(BaseModel):
    """Complete configuration.

    This is the main configuration model containing all configuration sections.
    Configuration is loaded from research-kit.yaml with defaults for missing values.
    """

    version: str = Field("1.0", description="Configuration version")
    gates: GatesConfig = Field(
        default_factory=GatesConfig, description="Validation gate thresholds"
    )
    ingestion: IngestionConfig = Field(
        default_factory=IngestionConfig, description="Ingestion quality thresholds"
    )
    verification: VerificationConfig = Field(
        default_factory=VerificationConfig, description="Verification test settings"
    )
    scoring: ScoringConfig = Field(
        default_factory=ScoringConfig, description="Trust score calculation weights"
    )
    red_flags: RedFlagsConfig = Field(
        default_factory=RedFlagsConfig, description="Red flag configuration"
    )
    backtest: BacktestConfig = Field(
        default_factory=BacktestConfig, description="Backtest execution configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )
    api: APIConfig = Field(
        default_factory=APIConfig, description="API configuration"
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


# =============================================================================
# DEFAULT CONFIGURATION
# =============================================================================


def get_default_config() -> Config:
    """Return the default configuration.

    Returns:
        Config with all default values.
    """
    return Config()


# =============================================================================
# CONFIG LOADING
# =============================================================================


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.

    Values from override take precedence. Nested dicts are merged recursively.
    Lists are replaced entirely (not merged).

    Args:
        base: Base dictionary
        override: Dictionary with values to override

    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: Path | str | None = None) -> Config:
    """Load configuration from a YAML file.

    If no path is provided, looks for research-kit.yaml in the current directory.
    If the file doesn't exist, returns default configuration.
    Partial configurations are merged with defaults.

    Args:
        path: Path to configuration file. If None, looks for research-kit.yaml
              in current directory.

    Returns:
        Loaded and validated Config.

    Raises:
        ConfigurationError: If YAML is invalid or configuration values are invalid.
    """
    # Determine config file path
    if path is None:
        config_path = Path.cwd() / "research-kit.yaml"
    else:
        config_path = Path(path)

    # If file doesn't exist, return defaults
    if not config_path.exists():
        return get_default_config()

    # Load YAML file
    try:
        with open(config_path) as f:
            user_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in {config_path}: {e}") from e
    except OSError as e:
        raise ConfigurationError(f"Error reading {config_path}: {e}") from e

    # Handle empty file
    if user_config is None:
        return get_default_config()

    # Get default config as dict
    default_dict = get_default_config().model_dump()

    # Deep merge user config with defaults
    merged = _deep_merge(default_dict, user_config)

    # Create and validate config
    try:
        return Config(**merged)
    except Exception as e:
        raise ConfigurationError(f"Invalid configuration: {e}") from e


# =============================================================================
# CONFIG VALIDATION
# =============================================================================


def validate_config(config: Config) -> list[str]:
    """Validate a configuration and return any errors.

    This performs additional validation beyond Pydantic's built-in validation,
    checking for logical consistency and best practices.

    Args:
        config: Configuration to validate

    Returns:
        List of validation error messages. Empty list if valid.
    """
    errors: list[str] = []

    # Check gate thresholds are reasonable
    if config.gates.min_sharpe > 5.0:
        errors.append(
            f"gates.min_sharpe={config.gates.min_sharpe} is unusually high. "
            "Consider a value between 0.5 and 3.0."
        )

    if config.gates.min_trades < 10:
        errors.append(
            f"gates.min_trades={config.gates.min_trades} may be too low for "
            "statistical significance. Consider at least 30 trades."
        )

    # Check ingestion thresholds
    if config.ingestion.min_specificity_score < 3:
        errors.append(
            f"ingestion.min_specificity_score={config.ingestion.min_specificity_score} "
            "is low. Strategies may be too vague to test effectively."
        )

    if config.ingestion.min_trust_score < 30:
        errors.append(
            f"ingestion.min_trust_score={config.ingestion.min_trust_score} "
            "is low. Consider at least 40-50 to filter low-quality strategies."
        )

    # Check verification is enabled
    if not config.verification.enabled:
        errors.append(
            "verification.enabled=false may allow strategies with issues "
            "(look-ahead bias, etc.) to pass through."
        )

    if config.verification.enabled and len(config.verification.tests) == 0:
        errors.append(
            "verification.enabled=true but no tests configured. "
            "Add verification tests or disable verification."
        )

    # Check red flags configuration
    if len(config.red_flags.hard_reject) == 0:
        errors.append(
            "red_flags.hard_reject is empty. "
            "No strategies will be automatically rejected for red flags."
        )

    return errors


# Backward-compat aliases
V4Config = Config
