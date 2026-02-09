"""V4 Core Module.

This package provides the core components for the V4 research-kit system:

- Configuration loading and validation (research-kit.yaml)
- Workspace management (directories, ID generation)
- Logging configuration with daily rotation

Example usage:
    from research_system.core.v4 import load_config, get_default_config, V4Config
    from research_system.core.v4 import V4Workspace, get_v4_workspace
    from research_system.core.v4 import setup_logging, get_logger, V4LogManager

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

    # Initialize a V4 workspace
    workspace = V4Workspace("/path/to/workspace")
    workspace.init(name="My Research")

    # Generate IDs
    strat_id = workspace.next_strategy_id()  # STRAT-001
    idea_id = workspace.next_idea_id()       # IDEA-001

    # Set up logging
    logger = setup_logging(workspace.path)
    logger.info("Starting research process")

    # Get named loggers for components
    ingest_logger = get_logger("research_system.ingest")
    ingest_logger.debug("Processing file")
"""

from research_system.core.v4.config import (
    # Configuration models
    V4Config,
    GatesConfig,
    IngestionConfig,
    VerificationConfig,
    ScoringConfig,
    RedFlagsConfig,
    BacktestConfig,
    LoggingConfig,
    APIConfig,
    # Loading functions
    load_config,
    get_default_config,
    validate_config,
    # Exceptions
    ConfigurationError,
)

from research_system.core.v4.workspace import (
    # Workspace class
    V4Workspace,
    # Helper functions
    get_v4_workspace,
    require_v4_workspace,
    # Exceptions
    V4WorkspaceError,
    # Constants
    DEFAULT_V4_WORKSPACE,
    WORKSPACE_ENV_VAR,
)

from research_system.core.v4.logging import (
    # Logging setup
    setup_logging,
    get_logger,
    V4LogManager,
)

__all__ = [
    # Configuration models
    "V4Config",
    "GatesConfig",
    "IngestionConfig",
    "VerificationConfig",
    "ScoringConfig",
    "RedFlagsConfig",
    "BacktestConfig",
    "LoggingConfig",
    "APIConfig",
    # Loading functions
    "load_config",
    "get_default_config",
    "validate_config",
    # Exceptions
    "ConfigurationError",
    # Workspace
    "V4Workspace",
    "get_v4_workspace",
    "require_v4_workspace",
    "V4WorkspaceError",
    # Constants
    "DEFAULT_V4_WORKSPACE",
    "WORKSPACE_ENV_VAR",
    # Logging
    "setup_logging",
    "get_logger",
    "V4LogManager",
]
