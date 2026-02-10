"""V4 Core Module.

This package provides the core components for the V4 research-kit system:

- Configuration loading and validation (research-kit.yaml)
- Workspace management (directories, ID generation)
- Logging configuration with daily rotation

Example usage:
    from research_system.core.v4 import load_config, get_default_config, Config
    from research_system.core.v4 import Workspace, get_workspace
    from research_system.core.v4 import setup_logging, get_logger, LogManager

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

    # Initialize a workspace
    workspace = Workspace("/path/to/workspace")
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
    Config,
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
    Workspace,
    # Helper functions
    get_workspace,
    require_workspace,
    # Exceptions
    WorkspaceError,
    # Constants
    DEFAULT_WORKSPACE,
    WORKSPACE_ENV_VAR,
)

from research_system.core.v4.logging import (
    # Logging setup
    setup_logging,
    get_logger,
    LogManager,
)

# Backward-compat aliases
V4Config = Config
V4Workspace = Workspace
V4WorkspaceError = WorkspaceError
get_v4_workspace = get_workspace
require_v4_workspace = require_workspace
DEFAULT_V4_WORKSPACE = DEFAULT_WORKSPACE
V4LogManager = LogManager

__all__ = [
    # Configuration models (new names)
    "Config",
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
    # Exceptions (new names)
    "ConfigurationError",
    "WorkspaceError",
    # Workspace (new names)
    "Workspace",
    "get_workspace",
    "require_workspace",
    # Constants (new names)
    "DEFAULT_WORKSPACE",
    "WORKSPACE_ENV_VAR",
    # Logging (new names)
    "setup_logging",
    "get_logger",
    "LogManager",
    # Backward-compat aliases (old names)
    "V4Config",
    "V4Workspace",
    "V4WorkspaceError",
    "get_v4_workspace",
    "require_v4_workspace",
    "DEFAULT_V4_WORKSPACE",
    "V4LogManager",
]
