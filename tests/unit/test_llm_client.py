"""Tests for LLM client."""

import pytest
import json

from research_system.llm.client import LLMClient, LLMResponse


class TestLLMClient:
    """Tests for LLMClient class."""

    def test_offline_mode_without_api_key(self, monkeypatch):
        """Test client runs in offline mode without API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        client = LLMClient()

        assert client.is_offline

    def test_generate_offline(self, monkeypatch):
        """Test generate returns offline response without API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        client = LLMClient()
        response = client.generate("Test prompt")

        assert response.offline
        assert "offline" in response.content.lower()

    def test_generate_haiku_offline(self, monkeypatch):
        """Test generate_haiku uses Haiku model."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        client = LLMClient()
        response = client.generate_haiku("Test prompt")

        assert response.offline
        assert "haiku" in response.model.lower()

    def test_extract_json_direct(self, monkeypatch):
        """Test extract_json with direct JSON."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        client = LLMClient()

        response = LLMResponse(
            content='{"name": "test", "value": 42}',
            model="test"
        )

        result = client.extract_json(response)

        assert result is not None
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_extract_json_code_block(self, monkeypatch):
        """Test extract_json with JSON in code block."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        client = LLMClient()

        response = LLMResponse(
            content='Here is the result:\n```json\n{"name": "test"}\n```\nDone.',
            model="test"
        )

        result = client.extract_json(response)

        assert result is not None
        assert result["name"] == "test"

    def test_extract_json_embedded(self, monkeypatch):
        """Test extract_json with embedded JSON."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        client = LLMClient()

        response = LLMResponse(
            content='The analysis shows {"status": "success", "score": 0.95} which is good.',
            model="test"
        )

        result = client.extract_json(response)

        assert result is not None
        assert result["status"] == "success"

    def test_extract_json_invalid(self, monkeypatch):
        """Test extract_json returns None for invalid JSON."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        client = LLMClient()

        response = LLMResponse(
            content='This is just plain text without JSON.',
            model="test"
        )

        result = client.extract_json(response)

        assert result is None
