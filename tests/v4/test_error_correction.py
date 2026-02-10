"""Tests for V4 error correction functionality.

This module tests:
1. Error classification (_is_correctable_error)
2. Correction prompt generation
3. Code correction method
4. Retry logic with correction
5. Max attempts limit
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from research_system.codegen.strategy_generator import (
    CodeGenerator,
    CodeCorrectionResult,
)
from research_system.validation.backtest import (
    BacktestExecutor,
    BacktestResult,
    CORRECTABLE_ERROR_PATTERNS,
)


# =============================================================================
# TEST ERROR CLASSIFICATION
# =============================================================================


class TestErrorClassification:
    """Test _is_correctable_error() classification logic."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create a BacktestExecutor for testing."""
        # Create minimal workspace structure
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "validations").mkdir()
        (workspace / "lean.json").write_text("{}")
        return BacktestExecutor(workspace_path=workspace, cleanup_on_start=False)

    def test_attribute_error_is_correctable(self, executor):
        """Test AttributeError is classified as correctable."""
        # Standard Python AttributeError format includes quotes around type
        error = "AttributeError: 'QCAlgorithm' object has no attribute 'SetCash'"
        assert executor._is_correctable_error(error)

    def test_attribute_error_variant_is_correctable(self, executor):
        """Test AttributeError variant without type quotes is correctable."""
        # Some errors may have slightly different format
        error = "AttributeError: type object 'Resolution' has no attribute 'daily'"
        assert executor._is_correctable_error(error)

    def test_name_error_is_correctable(self, executor):
        """Test NameError is classified as correctable."""
        error = "NameError: name 'Resolution' is not defined"
        assert executor._is_correctable_error(error)

    def test_type_error_is_correctable(self, executor):
        """Test TypeError is classified as correctable."""
        error = "TypeError: add_equity() takes 2 positional arguments but 3 were given"
        assert executor._is_correctable_error(error)

    def test_index_error_is_correctable(self, executor):
        """Test IndexError is classified as correctable."""
        error = "IndexError: list index out of range"
        assert executor._is_correctable_error(error)

    def test_key_error_is_correctable(self, executor):
        """Test KeyError is classified as correctable."""
        error = "KeyError: 'SPY'"
        assert executor._is_correctable_error(error)

    def test_resolution_error_is_correctable(self, executor):
        """Test Resolution-related error is classified as correctable."""
        error = "AttributeError: Resolution.daily does not exist"
        assert executor._is_correctable_error(error)

    def test_normalization_error_is_correctable(self, executor):
        """Test DataNormalizationMode error is classified as correctable."""
        error = "Options require DataNormalizationMode.RAW"
        assert executor._is_correctable_error(error)

    def test_syntax_error_is_correctable(self, executor):
        """Test syntax error is classified as correctable."""
        error = "SyntaxError: invalid syntax at line 42"
        assert executor._is_correctable_error(error)

    def test_missing_argument_is_correctable(self, executor):
        """Test missing argument error is correctable."""
        error = "TypeError: __init__() missing 2 required positional arguments"
        assert executor._is_correctable_error(error)

    def test_unexpected_keyword_is_correctable(self, executor):
        """Test unexpected keyword argument error is correctable."""
        error = "TypeError: add_equity() got an unexpected keyword argument 'foo'"
        assert executor._is_correctable_error(error)

    def test_empty_error_is_not_correctable(self, executor):
        """Test empty error is not classified as correctable."""
        assert not executor._is_correctable_error("")
        assert not executor._is_correctable_error(None)

    def test_rate_limit_error_is_not_correctable(self, executor):
        """Test rate limit error is not classified as correctable."""
        error = "No spare nodes available, please try again later"
        assert not executor._is_correctable_error(error)

    def test_generic_error_is_not_correctable(self, executor):
        """Test generic error is not classified as correctable."""
        error = "Something went wrong"
        assert not executor._is_correctable_error(error)


# =============================================================================
# TEST CORRECTION PROMPT GENERATION
# =============================================================================


class TestCorrectionPrompt:
    """Test correction prompt generation."""

    @pytest.fixture
    def generator(self):
        """Create a CodeGenerator without LLM client."""
        return CodeGenerator(llm_client=None)

    def test_correction_prompt_includes_strategy_name(self, generator):
        """Test prompt includes strategy name."""
        code = "class Test: pass"
        error = "Some error"
        strategy = {"name": "My Test Strategy", "id": "STRAT-001"}

        prompt = generator._build_correction_prompt(code, error, strategy)

        assert "My Test Strategy" in prompt

    def test_correction_prompt_includes_strategy_id(self, generator):
        """Test prompt includes strategy ID."""
        code = "class Test: pass"
        error = "Some error"
        strategy = {"name": "Test", "id": "STRAT-001"}

        prompt = generator._build_correction_prompt(code, error, strategy)

        assert "STRAT-001" in prompt

    def test_correction_prompt_includes_error(self, generator):
        """Test prompt includes the error message."""
        code = "class Test: pass"
        error = "AttributeError: object has no attribute 'foo'"
        strategy = {"name": "Test", "id": "STRAT-001"}

        prompt = generator._build_correction_prompt(code, error, strategy)

        assert error in prompt

    def test_correction_prompt_includes_code(self, generator):
        """Test prompt includes the failed code."""
        code = "class MyAlgorithm(QCAlgorithm):\n    pass"
        error = "Some error"
        strategy = {"name": "Test", "id": "STRAT-001"}

        prompt = generator._build_correction_prompt(code, error, strategy)

        assert code in prompt

    def test_correction_prompt_includes_common_fixes(self, generator):
        """Test prompt includes common fix hints."""
        code = "class Test: pass"
        error = "Some error"
        strategy = {"name": "Test", "id": "STRAT-001"}

        prompt = generator._build_correction_prompt(code, error, strategy)

        assert "Resolution" in prompt
        assert "snake_case" in prompt
        assert "DataNormalizationMode" in prompt


# =============================================================================
# TEST CODE CORRECTION
# =============================================================================


class TestCodeCorrection:
    """Test correct_code_error() method."""

    def test_correction_without_llm_client_fails(self):
        """Test correction fails without LLM client and no CLI fallback."""
        generator = CodeGenerator(llm_client=None)

        with patch.object(generator, '_claude_cli_available', return_value=False):
            result = generator.correct_code_error(
                original_code="class Test: pass",
                error_message="Some error",
                strategy={"name": "Test", "id": "STRAT-001"},
            )

        assert not result.success
        assert "No LLM client" in result.error

    def test_correction_with_llm_returns_corrected_code(self):
        """Test correction with mocked LLM client."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = """```python
from AlgorithmImports import *

class TestAlgorithm(QCAlgorithm):
    def initialize(self):
        self.set_cash(100000)
```"""
        mock_llm.generate.return_value = mock_response

        generator = CodeGenerator(llm_client=mock_llm)

        result = generator.correct_code_error(
            original_code="class Test: pass",
            error_message="Some error",
            strategy={"name": "Test", "id": "STRAT-001"},
        )

        assert result.success
        assert result.corrected_code is not None
        assert "QCAlgorithm" in result.corrected_code
        mock_llm.generate.assert_called_once()

    def test_correction_applies_post_processing(self):
        """Test that correction applies _fix_qc_api_issues."""
        mock_llm = Mock()
        mock_response = Mock()
        # LLM returns code with PascalCase (needs fixing)
        mock_response.content = """```python
class Test(QCAlgorithm):
    def Initialize(self):
        self.SetCash(100000)
        self.AddEquity("SPY", Resolution.daily)
```"""
        mock_llm.generate.return_value = mock_response

        generator = CodeGenerator(llm_client=mock_llm)

        result = generator.correct_code_error(
            original_code="class Test: pass",
            error_message="Some error",
            strategy={"name": "Test", "id": "STRAT-001"},
        )

        assert result.success
        # Should have snake_case and uppercase Resolution
        assert "set_cash" in result.corrected_code
        assert "add_equity" in result.corrected_code
        assert "Resolution.DAILY" in result.corrected_code

    def test_correction_returns_attempt_number(self):
        """Test that correction returns the attempt number."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "```python\nclass Test: pass\n```"
        mock_llm.generate.return_value = mock_response

        generator = CodeGenerator(llm_client=mock_llm)

        result = generator.correct_code_error(
            original_code="class Test: pass",
            error_message="Some error",
            strategy={"name": "Test", "id": "STRAT-001"},
            attempt=2,
        )

        assert result.attempt == 2

    def test_correction_handles_llm_exception(self):
        """Test that correction handles LLM exceptions gracefully."""
        mock_llm = Mock()
        mock_llm.generate.side_effect = Exception("LLM API error")

        generator = CodeGenerator(llm_client=mock_llm)

        result = generator.correct_code_error(
            original_code="class Test: pass",
            error_message="Some error",
            strategy={"name": "Test", "id": "STRAT-001"},
        )

        assert not result.success
        assert "Correction failed" in result.error

    def test_correction_fails_if_no_code_extracted(self):
        """Test correction fails if LLM doesn't return extractable code."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "I don't know how to fix this."
        mock_llm.generate.return_value = mock_response

        generator = CodeGenerator(llm_client=mock_llm)

        result = generator.correct_code_error(
            original_code="class Test: pass",
            error_message="Some error",
            strategy={"name": "Test", "id": "STRAT-001"},
        )

        assert not result.success
        assert "Could not extract corrected code" in result.error


# =============================================================================
# TEST CodeCorrectionResult DATACLASS
# =============================================================================


class TestCodeCorrectionResult:
    """Test CodeCorrectionResult dataclass."""

    def test_to_dict_success(self):
        """Test to_dict for successful correction."""
        result = CodeCorrectionResult(
            success=True,
            corrected_code="class Test: pass",
            attempt=2,
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["corrected_code"] == "class Test: pass"
        assert d["error"] is None
        assert d["attempt"] == 2

    def test_to_dict_failure(self):
        """Test to_dict for failed correction."""
        result = CodeCorrectionResult(
            success=False,
            error="No LLM client",
            attempt=1,
        )

        d = result.to_dict()

        assert d["success"] is False
        assert d["corrected_code"] is None
        assert d["error"] == "No LLM client"
        assert d["attempt"] == 1


# =============================================================================
# TEST RETRY LOGIC
# =============================================================================


class TestRetryLogic:
    """Test run_single_with_correction retry logic."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create a BacktestExecutor with mock run_single."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "validations").mkdir()
        (workspace / "lean.json").write_text("{}")
        return BacktestExecutor(workspace_path=workspace, cleanup_on_start=False)

    def test_success_on_first_try_returns_immediately(self, executor):
        """Test that success on first try returns without correction."""
        strategy = {"name": "Test", "id": "STRAT-001"}
        mock_generator = Mock()

        # Mock run_single to succeed immediately
        with patch.object(executor, 'run_single') as mock_run:
            mock_run.return_value = BacktestResult(success=True, cagr=0.15, sharpe=1.5)

            result, attempts = executor.run_single_with_correction(
                code="class Test: pass",
                start_date="2020-01-01",
                end_date="2022-12-31",
                strategy_id="STRAT-001",
                strategy=strategy,
                code_generator=mock_generator,
                max_attempts=3,
            )

        assert result.success
        assert attempts == 1
        mock_generator.correct_code_error.assert_not_called()

    def test_correction_attempted_on_correctable_error(self, executor):
        """Test that correction is attempted on correctable error."""
        strategy = {"name": "Test", "id": "STRAT-001"}

        mock_generator = Mock()
        mock_generator.correct_code_error.return_value = CodeCorrectionResult(
            success=True,
            corrected_code="class Fixed: pass",
        )

        call_count = [0]

        def run_single_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return BacktestResult(
                    success=False,
                    error="AttributeError: 'QCAlgorithm' object has no attribute 'foo'"
                )
            return BacktestResult(success=True, cagr=0.15, sharpe=1.5)

        with patch.object(executor, 'run_single', side_effect=run_single_side_effect):
            result, attempts = executor.run_single_with_correction(
                code="class Test: pass",
                start_date="2020-01-01",
                end_date="2022-12-31",
                strategy_id="STRAT-001",
                strategy=strategy,
                code_generator=mock_generator,
                max_attempts=3,
            )

        assert result.success
        assert attempts == 2
        mock_generator.correct_code_error.assert_called_once()

    def test_max_attempts_respected(self, executor):
        """Test that max_attempts limit is respected."""
        strategy = {"name": "Test", "id": "STRAT-001"}

        mock_generator = Mock()
        mock_generator.correct_code_error.return_value = CodeCorrectionResult(
            success=True,
            corrected_code="class StillBroken: pass",
        )

        # Always fail with correctable error
        with patch.object(executor, 'run_single') as mock_run:
            mock_run.return_value = BacktestResult(
                success=False,
                error="AttributeError: 'QCAlgorithm' object has no attribute 'foo'"
            )

            result, attempts = executor.run_single_with_correction(
                code="class Test: pass",
                start_date="2020-01-01",
                end_date="2022-12-31",
                strategy_id="STRAT-001",
                strategy=strategy,
                code_generator=mock_generator,
                max_attempts=3,
            )

        assert not result.success
        assert attempts == 3
        # Correction called twice (after attempt 1 and 2, not after attempt 3)
        assert mock_generator.correct_code_error.call_count == 2

    def test_no_correction_for_non_correctable_error(self, executor):
        """Test that non-correctable errors don't trigger correction."""
        strategy = {"name": "Test", "id": "STRAT-001"}
        mock_generator = Mock()

        with patch.object(executor, 'run_single') as mock_run:
            mock_run.return_value = BacktestResult(
                success=False,
                error="Something completely different happened"
            )

            result, attempts = executor.run_single_with_correction(
                code="class Test: pass",
                start_date="2020-01-01",
                end_date="2022-12-31",
                strategy_id="STRAT-001",
                strategy=strategy,
                code_generator=mock_generator,
                max_attempts=3,
            )

        assert not result.success
        assert attempts == 1
        mock_generator.correct_code_error.assert_not_called()

    def test_no_correction_for_rate_limited(self, executor):
        """Test that rate limited errors don't trigger correction."""
        strategy = {"name": "Test", "id": "STRAT-001"}
        mock_generator = Mock()

        with patch.object(executor, 'run_single') as mock_run:
            mock_run.return_value = BacktestResult(
                success=False,
                error="No spare nodes",
                rate_limited=True,
            )

            result, attempts = executor.run_single_with_correction(
                code="class Test: pass",
                start_date="2020-01-01",
                end_date="2022-12-31",
                strategy_id="STRAT-001",
                strategy=strategy,
                code_generator=mock_generator,
                max_attempts=3,
            )

        assert not result.success
        assert result.rate_limited
        mock_generator.correct_code_error.assert_not_called()

    def test_no_correction_for_engine_crash(self, executor):
        """Test that engine crashes don't trigger correction."""
        strategy = {"name": "Test", "id": "STRAT-001"}
        mock_generator = Mock()

        with patch.object(executor, 'run_single') as mock_run:
            mock_run.return_value = BacktestResult(
                success=False,
                error="PAL_SEHException",
                engine_crash=True,
            )

            result, attempts = executor.run_single_with_correction(
                code="class Test: pass",
                start_date="2020-01-01",
                end_date="2022-12-31",
                strategy_id="STRAT-001",
                strategy=strategy,
                code_generator=mock_generator,
                max_attempts=3,
            )

        assert not result.success
        assert result.engine_crash
        mock_generator.correct_code_error.assert_not_called()

    def test_stops_if_correction_fails(self, executor):
        """Test that we stop retrying if correction itself fails."""
        strategy = {"name": "Test", "id": "STRAT-001"}

        mock_generator = Mock()
        mock_generator.correct_code_error.return_value = CodeCorrectionResult(
            success=False,
            error="Could not extract code",
        )

        with patch.object(executor, 'run_single') as mock_run:
            mock_run.return_value = BacktestResult(
                success=False,
                error="AttributeError: 'QCAlgorithm' object has no attribute 'foo'"
            )

            result, attempts = executor.run_single_with_correction(
                code="class Test: pass",
                start_date="2020-01-01",
                end_date="2022-12-31",
                strategy_id="STRAT-001",
                strategy=strategy,
                code_generator=mock_generator,
                max_attempts=3,
            )

        assert not result.success
        assert attempts == 1
        # Only one correction attempt before stopping
        mock_generator.correct_code_error.assert_called_once()
