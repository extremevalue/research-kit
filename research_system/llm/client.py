"""
LLM client wrapper for the Research Validation System.

Provides a unified interface for Claude API calls with:
- Automatic model selection (Haiku for extraction, Sonnet for analysis)
- Graceful offline mode when API is unavailable
- Structured error handling
"""

import json
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from LLM call."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    offline: bool = False


class LLMClient:
    """
    Wrapper for Claude API calls.

    Supports both online mode (real API calls) and offline mode (returns prompts for inspection).
    """

    # Model constants
    MODEL_HAIKU = "claude-3-haiku-20240307"
    MODEL_SONNET = "claude-sonnet-4-20250514"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LLM client.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None
        self._offline = False

        if self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                self._offline = True
        else:
            self._offline = True

    @property
    def is_offline(self) -> bool:
        """Check if running in offline mode."""
        return self._offline or self._client is None

    def generate(
        self,
        user: str,
        system: Optional[str] = None,
        max_tokens: int = 4000,
        model: Optional[str] = None,
        temperature: float = 0.0
    ) -> LLMResponse:
        """
        Generate a response from Claude.

        Args:
            user: User message content
            system: Optional system prompt
            max_tokens: Maximum tokens in response
            model: Model to use (defaults to Sonnet)
            temperature: Sampling temperature (0.0 for deterministic)

        Returns:
            LLMResponse with content and metadata
        """
        model = model or self.MODEL_SONNET

        if self.is_offline:
            return self._offline_response(user, system, model)

        try:
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": user}]
            }

            if system:
                kwargs["system"] = system

            response = self._client.messages.create(**kwargs)

            return LLMResponse(
                content=response.content[0].text,
                model=response.model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            )

        except Exception as e:
            # Fall back to offline mode on any error
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=model,
                offline=True
            )

    def generate_haiku(
        self,
        user: str,
        system: Optional[str] = None,
        max_tokens: int = 1024
    ) -> LLMResponse:
        """
        Generate using Haiku for fast, cheap extraction tasks.

        Args:
            user: User message content
            system: Optional system prompt
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse with content and metadata
        """
        return self.generate(
            user=user,
            system=system,
            max_tokens=max_tokens,
            model=self.MODEL_HAIKU,
            temperature=0.0
        )

    def generate_sonnet(
        self,
        user: str,
        system: Optional[str] = None,
        max_tokens: int = 4000
    ) -> LLMResponse:
        """
        Generate using Sonnet for complex analysis tasks.

        Args:
            user: User message content
            system: Optional system prompt
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse with content and metadata
        """
        return self.generate(
            user=user,
            system=system,
            max_tokens=max_tokens,
            model=self.MODEL_SONNET,
            temperature=0.0
        )

    def _offline_response(
        self,
        user: str,
        system: Optional[str],
        model: str
    ) -> LLMResponse:
        """Generate offline response for inspection."""
        return LLMResponse(
            content=json.dumps({
                "mode": "offline",
                "message": "LLM client is in offline mode. No API calls made.",
                "system_prompt_length": len(system) if system else 0,
                "user_prompt_length": len(user),
                "model_requested": model
            }, indent=2),
            model=model,
            offline=True
        )

    def extract_json(self, response: LLMResponse) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from an LLM response.

        Handles common formats:
        - Raw JSON
        - JSON in ```json code blocks
        - JSON embedded in text

        Args:
            response: LLM response to parse

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        text = response.content

        try:
            # Try direct parse first
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        try:
            # Look for ```json block
            if "```json" in text:
                start = text.index("```json") + 7
                end = text.index("```", start)
                return json.loads(text[start:end].strip())
        except (ValueError, json.JSONDecodeError):
            pass

        try:
            # Look for first { to last }
            if "{" in text and "}" in text:
                start = text.index("{")
                end = text.rindex("}") + 1
                return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            pass

        return None


# Singleton client instance
_client_instance: Optional[LLMClient] = None


def get_client(api_key: Optional[str] = None) -> LLMClient:
    """
    Get or create the singleton LLM client instance.

    Args:
        api_key: Optional API key (only used on first call)

    Returns:
        LLMClient instance
    """
    global _client_instance

    if _client_instance is None:
        _client_instance = LLMClient(api_key)

    return _client_instance
