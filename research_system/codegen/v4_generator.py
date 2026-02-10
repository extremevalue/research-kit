"""Backward-compat redirect — use strategy_generator instead."""
from research_system.codegen.strategy_generator import *  # noqa: F401,F403
from research_system.codegen.strategy_generator import (
    CodeGenResult,
    CodeCorrectionResult,
    CodeGenerator,
    generate_code,
    V4CodeGenResult,
    V4CodeCorrectionResult,
    V4CodeGenerator,
    generate_v4_code,
)
