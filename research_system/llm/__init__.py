"""
LLM client module for the Research Validation System.

Provides a wrapper around the Anthropic API with graceful offline fallback.
"""

from research_system.llm.client import LLMClient, get_client

__all__ = ["LLMClient", "get_client"]
