"""V4 Configuration System.

This package provides configuration loading and validation for the V4 research-kit
system. Configuration is loaded from research-kit.yaml files with sensible defaults.

Example usage:
    from research_system.core.v4 import load_config, get_default_config, V4Config

    # Load config from file or use defaults
    config = load_config()

    # Access configuration values
    min_sharpe = config.gates.min_sharpe
    min_trust = config.ingestion.min_trust_score

    # Get default configuration
    default_config = get_default_config()

    # Validate configuration
    errors = validate_config(config)
    if errors:
        print(f"Configuration errors: {errors}")
"""

from research_system.core.v4.config import (
    # Configuration models
    V4Config,
    GatesConfig,
    IngestionConfig,
    VerificationConfig,
    ScoringConfig,
    RedFlagsConfig,
    LoggingConfig,
    APIConfig,
    # Loading functions
    load_config,
    get_default_config,
    validate_config,
    # Exceptions
    ConfigurationError,
)

__all__ = [
    # Configuration models
    "V4Config",
    "GatesConfig",
    "IngestionConfig",
    "VerificationConfig",
    "ScoringConfig",
    "RedFlagsConfig",
    "LoggingConfig",
    "APIConfig",
    # Loading functions
    "load_config",
    "get_default_config",
    "validate_config",
    # Exceptions
    "ConfigurationError",
]
