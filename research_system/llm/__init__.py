"""
LLM client module for the Research Validation System.

Provides a wrapper around the Anthropic API or Claude CLI with graceful offline fallback.
"""

from research_system.llm.client import LLMClient, LLMResponse, Backend, get_client

__all__ = ["LLMClient", "LLMResponse", "Backend", "get_client"]
