"""Tests for tunable parameters schema.

This module tests:
1. TunableParameter validation
2. TunableParameters collection
3. Search space calculations
4. Integration with V4Strategy
"""

import pytest
from pydantic import ValidationError

from research_system.schemas.v4 import (
    ParameterType,
    TunableParameter,
    TunableParameters,
)


# =============================================================================
# TEST TUNABLE PARAMETER VALIDATION
# =============================================================================


class TestTunableParameterValidation:
    """Test TunableParameter model validation."""

    def test_int_parameter_valid(self):
        """Test valid integer parameter."""
        param = TunableParameter(
            type=ParameterType.INT,
            default=10,
            min=5,
            max=30,
            step=5,
        )
        assert param.type == ParameterType.INT
        assert param.default == 10
        assert param.min == 5
        assert param.max == 30
        assert param.step == 5

    def test_float_parameter_valid(self):
        """Test valid float parameter."""
        param = TunableParameter(
            type=ParameterType.FLOAT,
            default=0.5,
            min=0.1,
            max=1.0,
            step=0.1,
        )
        assert param.type == ParameterType.FLOAT
        assert param.default == 0.5

    def test_bool_parameter_valid(self):
        """Test valid boolean parameter."""
        param = TunableParameter(
            type=ParameterType.BOOL,
            default=True,
        )
        assert param.type == ParameterType.BOOL
        assert param.default is True

    def test_choice_parameter_valid(self):
        """Test valid choice parameter."""
        param = TunableParameter(
            type=ParameterType.CHOICE,
            default="sma",
            choices=["sma", "ema", "wma"],
        )
        assert param.type == ParameterType.CHOICE
        assert param.default == "sma"
        assert param.choices == ["sma", "ema", "wma"]

    def test_min_greater_than_max_raises_error(self):
        """Test that min >= max raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TunableParameter(
                type=ParameterType.INT,
                default=10,
                min=30,
                max=5,
            )
        assert "min" in str(exc_info.value).lower()

    def test_min_equal_to_max_raises_error(self):
        """Test that min == max raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TunableParameter(
                type=ParameterType.INT,
                default=10,
                min=10,
                max=10,
            )
        assert "min" in str(exc_info.value).lower()

    def test_negative_step_raises_error(self):
        """Test that negative step raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TunableParameter(
                type=ParameterType.INT,
                default=10,
                min=5,
                max=30,
                step=-5,
            )
        assert "step" in str(exc_info.value).lower()

    def test_zero_step_raises_error(self):
        """Test that zero step raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TunableParameter(
                type=ParameterType.INT,
                default=10,
                min=5,
                max=30,
                step=0,
            )
        assert "step" in str(exc_info.value).lower()

    def test_choice_with_one_option_raises_error(self):
        """Test that choice with single option raises error."""
        with pytest.raises(ValidationError) as exc_info:
            TunableParameter(
                type=ParameterType.CHOICE,
                default="only",
                choices=["only"],
            )
        assert "choice" in str(exc_info.value).lower()

    def test_choice_with_no_options_raises_error(self):
        """Test that choice with no options raises error."""
        with pytest.raises(ValidationError) as exc_info:
            TunableParameter(
                type=ParameterType.CHOICE,
                default="test",
                choices=[],
            )
        assert "choice" in str(exc_info.value).lower()

    def test_parameter_with_description(self):
        """Test parameter with description."""
        param = TunableParameter(
            type=ParameterType.INT,
            default=20,
            description="Fast moving average period",
        )
        assert param.description == "Fast moving average period"


# =============================================================================
# TEST SEARCH SPACE SIZE CALCULATIONS
# =============================================================================


class TestSearchSpaceSize:
    """Test search space size calculations."""

    def test_int_search_space_size(self):
        """Test integer parameter search space size."""
        param = TunableParameter(
            type=ParameterType.INT,
            default=10,
            min=5,
            max=30,
            step=5,
        )
        # Values: 5, 10, 15, 20, 25, 30 = 6 values
        assert param.get_search_space_size() == 6

    def test_float_search_space_size(self):
        """Test float parameter search space size."""
        param = TunableParameter(
            type=ParameterType.FLOAT,
            default=0.5,
            min=0.1,
            max=0.5,
            step=0.1,
        )
        # Values: 0.1, 0.2, 0.3, 0.4, 0.5 = 5 values
        assert param.get_search_space_size() == 5

    def test_bool_search_space_size(self):
        """Test boolean parameter search space size."""
        param = TunableParameter(
            type=ParameterType.BOOL,
            default=True,
        )
        assert param.get_search_space_size() == 2

    def test_choice_search_space_size(self):
        """Test choice parameter search space size."""
        param = TunableParameter(
            type=ParameterType.CHOICE,
            default="sma",
            choices=["sma", "ema", "wma", "dema"],
        )
        assert param.get_search_space_size() == 4

    def test_fixed_parameter_search_space_size(self):
        """Test fixed parameter (no range) search space size."""
        param = TunableParameter(
            type=ParameterType.INT,
            default=10,
            # No min/max/step = fixed value
        )
        assert param.get_search_space_size() == 1


# =============================================================================
# TEST TUNABLE PARAMETERS COLLECTION
# =============================================================================


class TestTunableParametersCollection:
    """Test TunableParameters collection model."""

    def test_empty_parameters(self):
        """Test empty parameters collection."""
        params = TunableParameters()
        assert params.parameters == {}
        assert params.get_total_search_space_size() == 1
        assert params.get_defaults() == {}

    def test_single_parameter(self):
        """Test single parameter collection."""
        params = TunableParameters(
            parameters={
                "sma_period": TunableParameter(
                    type=ParameterType.INT,
                    default=20,
                    min=10,
                    max=50,
                    step=10,
                ),
            }
        )
        assert len(params.parameters) == 1
        assert params.get_defaults() == {"sma_period": 20}

    def test_multiple_parameters(self):
        """Test multiple parameters collection."""
        params = TunableParameters(
            parameters={
                "sma_fast": TunableParameter(
                    type=ParameterType.INT,
                    default=10,
                    min=5,
                    max=20,
                    step=5,
                ),
                "sma_slow": TunableParameter(
                    type=ParameterType.INT,
                    default=50,
                    min=30,
                    max=100,
                    step=10,
                ),
            }
        )
        assert len(params.parameters) == 2
        assert params.get_defaults() == {"sma_fast": 10, "sma_slow": 50}

    def test_total_search_space_size(self):
        """Test total search space size calculation."""
        params = TunableParameters(
            parameters={
                "sma_fast": TunableParameter(
                    type=ParameterType.INT,
                    default=10,
                    min=5,
                    max=20,
                    step=5,  # 4 values: 5, 10, 15, 20
                ),
                "sma_slow": TunableParameter(
                    type=ParameterType.INT,
                    default=50,
                    min=30,
                    max=50,
                    step=10,  # 3 values: 30, 40, 50
                ),
            }
        )
        # Total combinations: 4 * 3 = 12
        assert params.get_total_search_space_size() == 12

    def test_large_search_space(self):
        """Test large search space calculation."""
        params = TunableParameters(
            parameters={
                "param1": TunableParameter(
                    type=ParameterType.INT,
                    default=50,
                    min=10,
                    max=100,
                    step=1,  # 91 values
                ),
                "param2": TunableParameter(
                    type=ParameterType.INT,
                    default=50,
                    min=10,
                    max=100,
                    step=1,  # 91 values
                ),
            }
        )
        # Total combinations: 91 * 91 = 8281
        assert params.get_total_search_space_size() == 8281


# =============================================================================
# TEST YAML SERIALIZATION
# =============================================================================


class TestYAMLSerialization:
    """Test YAML-style dict serialization."""

    def test_parameter_to_dict(self):
        """Test parameter model_dump for YAML serialization."""
        param = TunableParameter(
            type=ParameterType.INT,
            default=20,
            min=10,
            max=50,
            step=5,
            description="SMA period",
        )
        data = param.model_dump()
        assert data["type"] == "int"
        assert data["default"] == 20
        assert data["min"] == 10
        assert data["max"] == 50
        assert data["step"] == 5
        assert data["description"] == "SMA period"

    def test_parameters_to_dict(self):
        """Test parameters collection model_dump."""
        params = TunableParameters(
            parameters={
                "sma_period": TunableParameter(
                    type=ParameterType.INT,
                    default=20,
                    min=10,
                    max=50,
                    step=5,
                ),
            }
        )
        data = params.model_dump()
        assert "parameters" in data
        assert "sma_period" in data["parameters"]


# =============================================================================
# TEST DICT PARSING (from YAML)
# =============================================================================


class TestDictParsing:
    """Test parsing from dict (as from YAML)."""

    def test_parse_int_parameter(self):
        """Test parsing int parameter from dict."""
        data = {
            "type": "int",
            "default": 20,
            "min": 10,
            "max": 50,
            "step": 5,
        }
        param = TunableParameter(**data)
        assert param.type == ParameterType.INT
        assert param.default == 20

    def test_parse_parameters_collection(self):
        """Test parsing parameters collection from dict."""
        data = {
            "parameters": {
                "sma_fast": {
                    "type": "int",
                    "default": 10,
                    "min": 5,
                    "max": 30,
                    "step": 5,
                },
                "use_ema": {
                    "type": "bool",
                    "default": False,
                },
            }
        }
        params = TunableParameters(**data)
        assert len(params.parameters) == 2
        assert params.parameters["sma_fast"].type == ParameterType.INT
        assert params.parameters["use_ema"].type == ParameterType.BOOL
