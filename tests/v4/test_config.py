"""Tests for V4 configuration system.

This module tests the V4 configuration loading and validation:
1. Default config when no file exists
2. Loading valid config from YAML file
3. Partial config merges with defaults
4. Validation errors for invalid values
5. Config access patterns
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from research_system.core.v4 import (
    Config,
    GatesConfig,
    IngestionConfig,
    VerificationConfig,
    ScoringConfig,
    RedFlagsConfig,
    LoggingConfig,
    APIConfig,
    load_config,
    get_default_config,
    validate_config,
    ConfigurationError,
)


# =============================================================================
# TEST DEFAULT CONFIG
# =============================================================================


class TestDefaultConfig:
    """Test default configuration behavior."""

    def test_get_default_config_returns_v4config(self):
        """Test that get_default_config returns a Config instance."""
        config = get_default_config()
        assert isinstance(config, Config)

    def test_default_config_has_expected_version(self):
        """Test default config has version 1.0."""
        config = get_default_config()
        assert config.version == "1.0"

    def test_default_gates_values(self):
        """Test default gate threshold values."""
        config = get_default_config()

        assert config.gates.min_sharpe == 1.0
        assert config.gates.min_consistency == 0.6
        assert config.gates.max_drawdown == 0.25
        assert config.gates.min_trades == 30

    def test_default_ingestion_values(self):
        """Test default ingestion threshold values."""
        config = get_default_config()

        assert config.ingestion.min_specificity_score == 4
        assert config.ingestion.min_trust_score == 50

    def test_default_verification_values(self):
        """Test default verification settings."""
        config = get_default_config()

        assert config.verification.enabled is True
        assert "look_ahead_bias" in config.verification.tests
        assert "survivorship_bias" in config.verification.tests
        assert "position_sizing" in config.verification.tests
        assert "data_availability" in config.verification.tests
        assert "parameter_sanity" in config.verification.tests

    def test_default_scoring_weights_sum_to_100(self):
        """Test that default scoring weights sum to 100."""
        config = get_default_config()

        total = (
            config.scoring.economic_rationale_weight
            + config.scoring.out_of_sample_weight
            + config.scoring.implementation_realism_weight
            + config.scoring.source_credibility_weight
            + config.scoring.novelty_weight
        )
        assert total == 100

    def test_default_scoring_values(self):
        """Test default scoring weight values."""
        config = get_default_config()

        assert config.scoring.economic_rationale_weight == 30
        assert config.scoring.out_of_sample_weight == 25
        assert config.scoring.implementation_realism_weight == 20
        assert config.scoring.source_credibility_weight == 15
        assert config.scoring.novelty_weight == 10

    def test_default_red_flags(self):
        """Test default red flag lists."""
        config = get_default_config()

        assert "sharpe_above_3" in config.red_flags.hard_reject
        assert "author_selling" in config.red_flags.hard_reject
        assert "unknown_rationale" in config.red_flags.soft_warning
        assert "crowded_factor" in config.red_flags.soft_warning

    def test_default_logging_level(self):
        """Test default logging level."""
        config = get_default_config()

        assert config.logging.level == "INFO"
        assert "%(asctime)s" in config.logging.format

    def test_default_api_model(self):
        """Test default API model."""
        config = get_default_config()

        assert config.api.anthropic_model == "claude-3-5-sonnet-20241022"


# =============================================================================
# TEST LOADING CONFIG FROM FILE
# =============================================================================


class TestLoadConfig:
    """Test configuration loading from files."""

    def test_load_config_no_file_returns_defaults(self, tmp_path):
        """Test that missing file returns default config."""
        os.chdir(tmp_path)
        config = load_config()

        assert isinstance(config, Config)
        assert config.gates.min_sharpe == 1.0

    def test_load_config_explicit_missing_path_returns_defaults(self, tmp_path):
        """Test that explicit missing path returns defaults."""
        missing_path = tmp_path / "nonexistent.yaml"
        config = load_config(missing_path)

        assert isinstance(config, Config)
        assert config.gates.min_sharpe == 1.0

    def test_load_config_from_valid_yaml(self, tmp_path):
        """Test loading config from valid YAML file."""
        config_data = {
            "version": "1.0",
            "gates": {
                "min_sharpe": 1.5,
                "min_consistency": 0.7,
            },
            "ingestion": {
                "min_specificity_score": 5,
            },
        }

        config_file = tmp_path / "research-kit.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)

        assert config.gates.min_sharpe == 1.5
        assert config.gates.min_consistency == 0.7
        assert config.ingestion.min_specificity_score == 5

    def test_load_config_from_string_path(self, tmp_path):
        """Test loading config using string path."""
        config_data = {"gates": {"min_sharpe": 2.0}}

        config_file = tmp_path / "research-kit.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(str(config_file))

        assert config.gates.min_sharpe == 2.0

    def test_load_config_empty_file_returns_defaults(self, tmp_path):
        """Test that empty YAML file returns defaults."""
        config_file = tmp_path / "research-kit.yaml"
        config_file.touch()

        config = load_config(config_file)

        assert isinstance(config, Config)
        assert config.gates.min_sharpe == 1.0

    def test_load_config_invalid_yaml_raises_error(self, tmp_path):
        """Test that invalid YAML raises ConfigurationError."""
        config_file = tmp_path / "research-kit.yaml"
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            load_config(config_file)

    def test_load_config_invalid_values_raises_error(self, tmp_path):
        """Test that invalid config values raise ConfigurationError."""
        config_data = {
            "gates": {
                "min_sharpe": -5.0,  # Invalid: negative
            }
        }

        config_file = tmp_path / "research-kit.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        with pytest.raises(ConfigurationError, match="Invalid configuration"):
            load_config(config_file)


# =============================================================================
# TEST PARTIAL CONFIG MERGING
# =============================================================================


class TestPartialConfigMerge:
    """Test that partial configs are merged with defaults."""

    def test_partial_gates_merged_with_defaults(self, tmp_path):
        """Test that partial gates config is merged with defaults."""
        config_data = {
            "gates": {
                "min_sharpe": 2.0,
                # Other gates not specified
            }
        }

        config_file = tmp_path / "research-kit.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)

        # Overridden value
        assert config.gates.min_sharpe == 2.0
        # Default values preserved
        assert config.gates.min_consistency == 0.6
        assert config.gates.max_drawdown == 0.25
        assert config.gates.min_trades == 30

    def test_partial_ingestion_merged_with_defaults(self, tmp_path):
        """Test that partial ingestion config is merged with defaults."""
        config_data = {
            "ingestion": {
                "min_trust_score": 75,
            }
        }

        config_file = tmp_path / "research-kit.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)

        assert config.ingestion.min_trust_score == 75
        assert config.ingestion.min_specificity_score == 4  # Default

    def test_full_sections_not_specified_use_defaults(self, tmp_path):
        """Test that unspecified sections use defaults."""
        config_data = {
            "version": "1.0",
            "gates": {"min_sharpe": 1.5},
            # Other sections not specified
        }

        config_file = tmp_path / "research-kit.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)

        # Gates overridden
        assert config.gates.min_sharpe == 1.5

        # All other sections use defaults
        assert config.ingestion.min_specificity_score == 4
        assert config.verification.enabled is True
        assert config.scoring.economic_rationale_weight == 30
        assert len(config.red_flags.hard_reject) > 0
        assert config.logging.level == "INFO"

    def test_nested_deep_merge(self, tmp_path):
        """Test that nested config is properly deep merged."""
        config_data = {
            "gates": {"min_sharpe": 2.0},
            "verification": {"enabled": False},
            "logging": {"level": "DEBUG"},
        }

        config_file = tmp_path / "research-kit.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)

        assert config.gates.min_sharpe == 2.0
        assert config.gates.min_consistency == 0.6  # Default preserved
        assert config.verification.enabled is False
        assert len(config.verification.tests) > 0  # Default tests preserved
        assert config.logging.level == "DEBUG"


# =============================================================================
# TEST VALIDATION ERRORS
# =============================================================================


class TestValidationErrors:
    """Test validation error handling."""

    def test_invalid_min_sharpe_negative(self):
        """Test that negative min_sharpe raises error."""
        with pytest.raises(ValueError):
            GatesConfig(min_sharpe=-1.0)

    def test_invalid_consistency_above_1(self):
        """Test that consistency > 1 raises error."""
        with pytest.raises(ValueError):
            GatesConfig(min_consistency=1.5)

    def test_invalid_drawdown_above_1(self):
        """Test that drawdown > 1 raises error."""
        with pytest.raises(ValueError):
            GatesConfig(max_drawdown=1.5)

    def test_invalid_specificity_above_8(self):
        """Test that specificity > 8 raises error."""
        with pytest.raises(ValueError):
            IngestionConfig(min_specificity_score=10)

    def test_invalid_trust_above_100(self):
        """Test that trust > 100 raises error."""
        with pytest.raises(ValueError):
            IngestionConfig(min_trust_score=150)

    def test_invalid_verification_test_name(self):
        """Test that invalid verification test name raises error."""
        with pytest.raises(ValueError, match="Invalid verification test"):
            VerificationConfig(tests=["invalid_test_name"])

    def test_scoring_weights_must_sum_to_100(self):
        """Test that scoring weights must sum to 100."""
        with pytest.raises(ValueError, match="must sum to 100"):
            ScoringConfig(
                economic_rationale_weight=50,
                out_of_sample_weight=50,
                implementation_realism_weight=50,
                source_credibility_weight=50,
                novelty_weight=50,
            )

    def test_valid_scoring_weights_accepted(self):
        """Test that valid scoring weights are accepted."""
        config = ScoringConfig(
            economic_rationale_weight=40,
            out_of_sample_weight=30,
            implementation_realism_weight=15,
            source_credibility_weight=10,
            novelty_weight=5,
        )
        assert config.economic_rationale_weight == 40


# =============================================================================
# TEST CONFIG ACCESS PATTERNS
# =============================================================================


class TestConfigAccess:
    """Test configuration access patterns."""

    def test_gates_access(self):
        """Test accessing gate configuration values."""
        config = get_default_config()

        min_sharpe = config.gates.min_sharpe
        min_consistency = config.gates.min_consistency

        assert isinstance(min_sharpe, float)
        assert isinstance(min_consistency, float)

    def test_ingestion_access(self):
        """Test accessing ingestion configuration values."""
        config = get_default_config()

        min_spec = config.ingestion.min_specificity_score
        min_trust = config.ingestion.min_trust_score

        assert isinstance(min_spec, int)
        assert isinstance(min_trust, int)

    def test_verification_tests_access(self):
        """Test accessing verification tests list."""
        config = get_default_config()

        tests = config.verification.tests

        assert isinstance(tests, list)
        assert all(isinstance(t, str) for t in tests)

    def test_red_flags_access(self):
        """Test accessing red flags lists."""
        config = get_default_config()

        hard = config.red_flags.hard_reject
        soft = config.red_flags.soft_warning

        assert isinstance(hard, list)
        assert isinstance(soft, list)

    def test_config_serialization(self):
        """Test that config can be serialized to dict."""
        config = get_default_config()

        data = config.model_dump()

        assert isinstance(data, dict)
        assert "version" in data
        assert "gates" in data
        assert data["gates"]["min_sharpe"] == 1.0

    def test_config_json_serialization(self):
        """Test that config can be serialized to JSON."""
        config = get_default_config()

        json_str = config.model_dump_json()

        assert isinstance(json_str, str)
        assert "min_sharpe" in json_str


# =============================================================================
# TEST VALIDATE_CONFIG FUNCTION
# =============================================================================


class TestValidateConfig:
    """Test the validate_config function."""

    def test_valid_config_returns_empty_list(self):
        """Test that valid config returns no errors."""
        config = get_default_config()
        errors = validate_config(config)

        assert errors == []

    def test_high_min_sharpe_warning(self):
        """Test warning for unusually high min_sharpe."""
        config = Config(
            gates=GatesConfig(min_sharpe=10.0)
        )
        errors = validate_config(config)

        assert any("min_sharpe" in e and "unusually high" in e for e in errors)

    def test_low_min_trades_warning(self):
        """Test warning for low min_trades."""
        config = Config(
            gates=GatesConfig(min_trades=5)
        )
        errors = validate_config(config)

        assert any("min_trades" in e and "too low" in e for e in errors)

    def test_low_specificity_warning(self):
        """Test warning for low specificity threshold."""
        config = Config(
            ingestion=IngestionConfig(min_specificity_score=2)
        )
        errors = validate_config(config)

        assert any("min_specificity_score" in e for e in errors)

    def test_low_trust_warning(self):
        """Test warning for low trust threshold."""
        config = Config(
            ingestion=IngestionConfig(min_trust_score=20)
        )
        errors = validate_config(config)

        assert any("min_trust_score" in e for e in errors)

    def test_verification_disabled_warning(self):
        """Test warning when verification is disabled."""
        config = Config(
            verification=VerificationConfig(enabled=False)
        )
        errors = validate_config(config)

        assert any("verification.enabled=false" in e for e in errors)

    def test_empty_verification_tests_warning(self):
        """Test warning when verification is enabled but no tests."""
        config = Config(
            verification=VerificationConfig(enabled=True, tests=[])
        )
        errors = validate_config(config)

        assert any("no tests configured" in e for e in errors)

    def test_empty_hard_reject_warning(self):
        """Test warning when hard_reject is empty."""
        config = Config(
            red_flags=RedFlagsConfig(hard_reject=[])
        )
        errors = validate_config(config)

        assert any("hard_reject is empty" in e for e in errors)


# =============================================================================
# TEST ENVIRONMENT VARIABLE SUPPORT
# =============================================================================


class TestEnvironmentVariables:
    """Test environment variable support for API keys."""

    def test_api_key_from_env_var(self, monkeypatch):
        """Test that API key is read from environment variable."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key-123")

        config = APIConfig()

        assert config.anthropic_api_key == "test-api-key-123"

    def test_explicit_api_key_overrides_env(self, monkeypatch):
        """Test that explicit API key takes precedence."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")

        config = APIConfig(anthropic_api_key="explicit-key")

        assert config.anthropic_api_key == "explicit-key"

    def test_api_key_none_when_not_set(self, monkeypatch):
        """Test that API key is None when not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        config = APIConfig()

        assert config.anthropic_api_key is None


# =============================================================================
# TEST FULL YAML CONFIG
# =============================================================================


class TestFullYamlConfig:
    """Test loading a complete YAML configuration file."""

    def test_load_full_example_config(self, tmp_path):
        """Test loading a complete example configuration."""
        config_yaml = """
version: "1.0"

gates:
  min_sharpe: 1.0
  min_consistency: 0.6
  max_drawdown: 0.25
  min_trades: 30

ingestion:
  min_specificity_score: 4
  min_trust_score: 50

verification:
  enabled: true
  tests:
    - look_ahead_bias
    - survivorship_bias
    - position_sizing
    - data_availability
    - parameter_sanity

scoring:
  economic_rationale_weight: 30
  out_of_sample_weight: 25
  implementation_realism_weight: 20
  source_credibility_weight: 15
  novelty_weight: 10

red_flags:
  hard_reject:
    - sharpe_above_3
    - no_losing_periods
    - works_all_conditions
    - author_selling
    - excessive_parameters
    - convenient_start_date
  soft_warning:
    - unknown_rationale
    - no_transaction_costs
    - no_drawdown_mentioned
    - single_market
    - single_regime
    - small_sample
    - high_leverage
    - crowded_factor
    - magic_numbers

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

api:
  anthropic_model: claude-3-5-sonnet-20241022
"""

        config_file = tmp_path / "research-kit.yaml"
        with open(config_file, "w") as f:
            f.write(config_yaml)

        config = load_config(config_file)

        # Verify all sections loaded correctly
        assert config.version == "1.0"
        assert config.gates.min_sharpe == 1.0
        assert config.ingestion.min_trust_score == 50
        assert config.verification.enabled is True
        assert "look_ahead_bias" in config.verification.tests
        assert config.scoring.economic_rationale_weight == 30
        assert "sharpe_above_3" in config.red_flags.hard_reject
        assert "unknown_rationale" in config.red_flags.soft_warning
        assert config.logging.level == "INFO"
        assert config.api.anthropic_model == "claude-3-5-sonnet-20241022"

        # Validate config
        errors = validate_config(config)
        assert errors == []
