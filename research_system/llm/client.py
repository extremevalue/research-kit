"""
LLM client wrapper for the Research Validation System.

Provides a unified interface for Claude API calls with:
- Automatic model selection (Haiku for extraction, Sonnet for analysis)
- Multiple backends: Anthropic API or Claude CLI
- Graceful offline mode when no backend is available
- Structured error handling
"""

import json
import os
import subprocess
import shutil
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass


class Backend(Enum):
    """Available LLM backends."""
    API = "api"         # Anthropic API (requires ANTHROPIC_API_KEY)
    CLI = "cli"         # Claude Code CLI (requires claude command)
    OFFLINE = "offline" # No backend available


@dataclass
class LLMResponse:
    """Response from LLM call."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    offline: bool = False
    backend: str = "api"  # Track which backend was used for reproducibility


class LLMClient:
    """
    Wrapper for Claude API calls.

    Supports multiple backends:
    - API: Anthropic API (requires ANTHROPIC_API_KEY)
    - CLI: Claude Code CLI (requires claude command in PATH)
    - Offline: Returns prompts for inspection when no backend available
    """

    # Model constants
    MODEL_HAIKU = "claude-3-haiku-20240307"
    MODEL_SONNET = "claude-sonnet-4-20250514"

    # CLI model mappings (Claude CLI uses different model names)
    CLI_MODEL_MAP = {
        MODEL_HAIKU: "haiku",
        MODEL_SONNET: "sonnet",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        backend: Optional[Backend] = None
    ):
        """
        Initialize the LLM client.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
            backend: Which backend to use. If None, auto-detects with priority:
                     1. API (if ANTHROPIC_API_KEY is set)
                     2. CLI (if claude command is available)
                     3. Offline (fallback)
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None
        self._backend = Backend.OFFLINE
        self._cli_path: Optional[str] = None

        if backend is not None:
            # Explicit backend requested
            self._backend = self._init_backend(backend)
        else:
            # Auto-detect: try API first, then CLI
            self._backend = self._auto_detect_backend()

    def _init_backend(self, backend: Backend) -> Backend:
        """Initialize a specific backend, returning actual backend (may be OFFLINE if failed)."""
        if backend == Backend.API:
            if self.api_key:
                try:
                    import anthropic
                    self._client = anthropic.Anthropic(api_key=self.api_key)
                    return Backend.API
                except ImportError:
                    pass
            return Backend.OFFLINE

        elif backend == Backend.CLI:
            self._cli_path = shutil.which("claude")
            if self._cli_path:
                return Backend.CLI
            return Backend.OFFLINE

        return Backend.OFFLINE

    def _auto_detect_backend(self) -> Backend:
        """Auto-detect available backend with priority: API > CLI > Offline."""
        # Try API first
        if self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
                return Backend.API
            except ImportError:
                pass

        # Try CLI
        self._cli_path = shutil.which("claude")
        if self._cli_path:
            return Backend.CLI

        # Fallback to offline
        return Backend.OFFLINE

    @property
    def backend(self) -> Backend:
        """Get the current backend."""
        return self._backend

    @property
    def is_offline(self) -> bool:
        """Check if running in offline mode."""
        return self._backend == Backend.OFFLINE

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

        if self._backend == Backend.API:
            return self._generate_api(user, system, max_tokens, model, temperature)
        elif self._backend == Backend.CLI:
            return self._generate_cli(user, system, max_tokens, model)
        else:
            return self._offline_response(user, system, model)

    def _generate_api(
        self,
        user: str,
        system: Optional[str],
        max_tokens: int,
        model: str,
        temperature: float
    ) -> LLMResponse:
        """Generate using Anthropic API."""
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
                },
                backend="api"
            )

        except Exception as e:
            # Fall back to offline mode on any error
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=model,
                offline=True,
                backend="api"
            )

    def _generate_cli(
        self,
        user: str,
        system: Optional[str],
        max_tokens: int,
        model: str
    ) -> LLMResponse:
        """Generate using Claude Code CLI."""
        try:
            # Build the prompt - combine system and user prompts
            if system:
                full_prompt = f"{system}\n\n---\n\n{user}"
            else:
                full_prompt = user

            # Map model to CLI model name
            cli_model = self.CLI_MODEL_MAP.get(model, "sonnet")

            # Build command
            # Use limited max-turns to prevent excessive tool exploration
            # Prompt instructs model not to use tools anyway
            cmd = [
                self._cli_path,
                "--print",           # Output response only, no interactive mode
                "--model", cli_model,
                "--max-turns", "3",  # Allow a few turns but not unlimited exploration
            ]

            # Run claude CLI with prompt on stdin
            result = subprocess.run(
                cmd,
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )

            if result.returncode != 0:
                return LLMResponse(
                    content=f"CLI Error: {result.stderr}",
                    model=model,
                    offline=True,
                    backend="cli"
                )

            return LLMResponse(
                content=result.stdout.strip(),
                model=model,
                usage=None,  # CLI doesn't provide token counts
                backend="cli"
            )

        except subprocess.TimeoutExpired:
            return LLMResponse(
                content="Error: CLI request timed out after 120 seconds",
                model=model,
                offline=True,
                backend="cli"
            )
        except Exception as e:
            return LLMResponse(
                content=f"CLI Error: {str(e)}",
                model=model,
                offline=True,
                backend="cli"
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
            offline=True,
            backend="offline"
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

        def parse_and_validate(json_str: str) -> Optional[Dict[str, Any]]:
            """Parse JSON and return only if it's a dict."""
            result = json.loads(json_str)
            return result if isinstance(result, dict) else None

        try:
            # Try direct parse first
            return parse_and_validate(text)
        except json.JSONDecodeError:
            pass

        try:
            # Look for ```json block
            if "```json" in text:
                start = text.index("```json") + 7
                end = text.index("```", start)
                return parse_and_validate(text[start:end].strip())
        except (ValueError, json.JSONDecodeError):
            pass

        try:
            # Look for first { to last }
            if "{" in text and "}" in text:
                start = text.index("{")
                end = text.rindex("}") + 1
                return parse_and_validate(text[start:end])
        except (ValueError, json.JSONDecodeError):
            pass

        return None


# Singleton client instance
_client_instance: Optional[LLMClient] = None


def get_client(
    api_key: Optional[str] = None,
    backend: Optional[Backend] = None
) -> LLMClient:
    """
    Get or create the singleton LLM client instance.

    Args:
        api_key: Optional API key (only used on first call)
        backend: Optional backend to use (only used on first call)

    Returns:
        LLMClient instance
    """
    global _client_instance

    if _client_instance is None:
        _client_instance = LLMClient(api_key, backend)

    return _client_instance
