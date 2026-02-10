"""Tests for non-interactive develop mode."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestNonInteractiveDevelop:
    """Test the non-interactive development workflow."""

    def test_non_interactive_flag_in_parser(self):
        """Verify --non-interactive flag is registered."""
        from research_system.cli.main import create_parser
        parser = create_parser()
        args = parser.parse_args(["develop", "IDEA-001", "--non-interactive"])
        assert args.non_interactive is True

    def test_input_flag_in_parser(self):
        """Verify --input flag is registered."""
        from research_system.cli.main import create_parser
        parser = create_parser()
        args = parser.parse_args(["develop", "IDEA-001", "--input", "data.json"])
        assert args.input == "data.json"

    def test_run_non_interactive_with_input_data(self):
        """Test non-interactive mode completes all steps with provided data."""
        from scripts.develop.workflow import (
            DevelopmentWorkflow, DevelopmentStep, STEP_DEFINITIONS, STEP_ORDER
        )

        # Build complete input data for all 10 steps
        input_data = {}
        for step in STEP_ORDER:
            info = STEP_DEFINITIONS[step]
            input_data[step.value] = {
                output: f"Test value for {output}"
                for output in info['required_outputs']
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = DevelopmentWorkflow(Path(tmpdir), None)
            state = workflow.start("TEST-001", "Test idea for development")

            from research_system.cli.main import _run_non_interactive_develop
            _run_non_interactive_develop(workflow, state, None, input_data)

            # Verify state is complete
            loaded = workflow.load("TEST-001")
            assert loaded.is_complete
            assert len(loaded.completed_steps) == 10

    def test_run_non_interactive_with_placeholders(self):
        """Test non-interactive mode uses placeholders when no input or LLM."""
        from scripts.develop.workflow import DevelopmentWorkflow

        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = DevelopmentWorkflow(Path(tmpdir), None)
            state = workflow.start("TEST-002", "Another test idea")

            from research_system.cli.main import _run_non_interactive_develop
            _run_non_interactive_develop(workflow, state, None)

            # Verify state is complete with placeholder values
            loaded = workflow.load("TEST-002")
            assert loaded.is_complete
            # Check that placeholders are present
            outputs = loaded.step_outputs["hypothesis"]["outputs"]
            assert "TODO:" in outputs["hypothesis_statement"]

    def test_run_non_interactive_from_json_file(self):
        """Test the JSON file input path."""
        from scripts.develop.workflow import (
            DevelopmentWorkflow, STEP_DEFINITIONS, STEP_ORDER
        )

        # Create input JSON file
        input_data = {}
        for step in STEP_ORDER:
            info = STEP_DEFINITIONS[step]
            input_data[step.value] = {
                output: f"JSON file value for {output}"
                for output in info['required_outputs']
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "inputs.json"
            with open(input_file, "w") as f:
                json.dump(input_data, f)

            workflow = DevelopmentWorkflow(Path(tmpdir), None)
            state = workflow.start("TEST-003", "JSON file test idea")

            from research_system.cli.main import _run_non_interactive_develop
            _run_non_interactive_develop(workflow, state, None, input_data)

            loaded = workflow.load("TEST-003")
            assert loaded.is_complete
            outputs = loaded.step_outputs["hypothesis"]["outputs"]
            assert outputs["hypothesis_statement"] == "JSON file value for hypothesis_statement"
