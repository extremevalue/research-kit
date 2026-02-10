"""Backward-compat redirect — use runner instead."""
from research_system.validation.runner import *  # noqa: F401,F403
from research_system.validation.runner import (
    Runner,
    RunResult,
    V4Runner,
    V4RunResult,
)
