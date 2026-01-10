"""CLI commands for code generation.

This module provides Typer-based CLI commands for generating strategy code.

Usage:
    python -m research_system.codegen.cli generate STRAT-001 --output ./output/
    python -m research_system.codegen.cli validate STRAT-001
"""

from pathlib import Path
from typing import Annotated

import typer

from research_system.codegen.engine import CodeGenerationError, TemplateEngine
from research_system.codegen.generator import CodeGenerator
from research_system.schemas.common import (
    PositionSizingMethod,
    RebalanceFrequency,
    SignalType,
    UniverseType,
)
from research_system.schemas.strategy import (
    PositionSizingConfig,
    RebalanceConfig,
    SignalConfig,
    StrategyDefinition,
    StrategyMetadata,
    UniverseConfig,
)

app = typer.Typer(
    name="codegen",
    help="Generate QuantConnect-compatible strategy code from catalog entries.",
    no_args_is_help=True,
)


@app.command("generate")
def generate(
    strategy_id: Annotated[str, typer.Argument(help="Strategy ID (e.g., STRAT-001)")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
    catalog: Annotated[
        Path | None,
        typer.Option("--catalog", "-c", help="Path to catalog directory"),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", "-f", help="Overwrite existing output file"),
    ] = False,
    validate_output: Annotated[
        bool,
        typer.Option("--validate/--no-validate", help="Validate generated code"),
    ] = True,
    stdout: Annotated[
        bool,
        typer.Option("--stdout", help="Print generated code to stdout"),
    ] = False,
):
    """Generate code for a strategy from the catalog.

    Looks up the strategy by ID in the catalog and generates
    QuantConnect-compatible Python code.

    Examples:
        # Generate and save to file
        codegen generate STRAT-001 --output ./output/strategy.py

        # Generate and print to stdout
        codegen generate STRAT-001 --stdout

        # Generate with validation disabled
        codegen generate STRAT-001 --output ./output/strategy.py --no-validate
    """
    try:
        with CodeGenerator(catalog) as generator:
            # Generate the code
            code = generator.generate(strategy_id)

            # Validate if requested
            if validate_output:
                errors = generator._engine.validate_output(code)
                # Filter to critical errors only
                critical_errors = [
                    e
                    for e in errors
                    if "Syntax error" in e
                    or "Missing required import" in e
                    or "Missing QCAlgorithm" in e
                    or "Missing Initialize" in e
                ]
                if critical_errors:
                    typer.secho("Validation errors:", fg=typer.colors.RED)
                    for error in critical_errors:
                        typer.echo(f"  - {error}")
                    raise typer.Exit(1)

                # Show warnings for non-critical issues
                warnings = [e for e in errors if e not in critical_errors]
                if warnings:
                    typer.secho("Warnings:", fg=typer.colors.YELLOW)
                    for warning in warnings:
                        typer.echo(f"  - {warning}")

            # Output the code
            if stdout:
                typer.echo(code)
            elif output:
                if output.exists() and not overwrite:
                    typer.secho(
                        f"Error: File already exists: {output}. Use --overwrite to replace.",
                        fg=typer.colors.RED,
                    )
                    raise typer.Exit(1)

                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(code)
                typer.secho(f"Generated: {output}", fg=typer.colors.GREEN)
            else:
                typer.echo(code)

    except CodeGenerationError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1) from None


@app.command("validate")
def validate(
    strategy_id: Annotated[str, typer.Argument(help="Strategy ID (e.g., STRAT-001)")],
    catalog: Annotated[
        Path | None,
        typer.Option("--catalog", "-c", help="Path to catalog directory"),
    ] = None,
):
    """Validate generated code for a strategy without saving.

    Generates the code and checks for common issues:
    - Python syntax errors
    - Hardcoded dates (SetStartDate/SetEndDate)
    - Missing required imports
    - Missing class structure

    Examples:
        codegen validate STRAT-001
        codegen validate STRAT-001 --catalog ./my-catalog
    """
    try:
        with CodeGenerator(catalog) as generator:
            errors = generator.validate(strategy_id)

            if not errors:
                typer.secho(f"✓ {strategy_id}: All checks passed", fg=typer.colors.GREEN)
                raise typer.Exit(0)

            # Categorize errors
            critical = [
                e
                for e in errors
                if "Syntax error" in e
                or "Missing required import" in e
                or "Missing QCAlgorithm" in e
                or "Missing Initialize" in e
            ]
            warnings = [e for e in errors if e not in critical]

            if critical:
                typer.secho(f"✗ {strategy_id}: Critical errors found", fg=typer.colors.RED)
                for error in critical:
                    typer.echo(f"  ERROR: {error}")

            if warnings:
                typer.secho(f"⚠ {strategy_id}: Warnings", fg=typer.colors.YELLOW)
                for warning in warnings:
                    typer.echo(f"  WARNING: {warning}")

            if critical:
                raise typer.Exit(1)

    except CodeGenerationError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1) from None


@app.command("demo")
def demo(
    strategy_type: Annotated[
        str,
        typer.Argument(help="Strategy type (momentum_rotation, mean_reversion, etc.)"),
    ] = "momentum_rotation",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
):
    """Generate demo code for a strategy type without needing catalog.

    Useful for testing template output or seeing example code structure.

    Examples:
        codegen demo momentum_rotation
        codegen demo mean_reversion --output ./demo.py
    """
    # Create a demo strategy definition
    demo_strategies = {
        "momentum_rotation": StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(
                id="DEMO-MOMENTUM",
                name="Demo Momentum Rotation",
                description="Demo strategy showing momentum rotation template",
                tags=["demo", "momentum"],
            ),
            strategy_type="momentum_rotation",
            universe=UniverseConfig(
                type=UniverseType.FIXED,
                symbols=["SPY", "TLT", "GLD", "VNQ"],
                defensive_symbols=["SHY", "BIL"],
            ),
            signal=SignalConfig(
                type=SignalType.RELATIVE_MOMENTUM,
                lookback_days=126,
                selection_n=2,
            ),
            position_sizing=PositionSizingConfig(
                method=PositionSizingMethod.EQUAL_WEIGHT, leverage=1.0
            ),
            rebalance=RebalanceConfig(frequency=RebalanceFrequency.MONTHLY),
        ),
        "mean_reversion": StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(
                id="DEMO-MEANREV",
                name="Demo Mean Reversion",
                description="Demo strategy showing mean reversion template",
                tags=["demo", "mean_reversion"],
            ),
            strategy_type="mean_reversion",
            universe=UniverseConfig(type=UniverseType.FIXED, symbols=["SPY"]),
            signal=SignalConfig(
                type=SignalType.MEAN_REVERSION,
                lookback_days=20,
                threshold=-2.0,
            ),
            position_sizing=PositionSizingConfig(method=PositionSizingMethod.EQUAL_WEIGHT),
            rebalance=RebalanceConfig(frequency=RebalanceFrequency.DAILY),
        ),
        "trend_following": StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(
                id="DEMO-TREND",
                name="Demo Trend Following",
                description="Demo strategy showing trend following template",
                tags=["demo", "trend"],
            ),
            strategy_type="trend_following",
            universe=UniverseConfig(
                type=UniverseType.FIXED,
                symbols=["SPY", "QQQ", "IWM"],
                defensive_symbols=["TLT"],
            ),
            signal=SignalConfig(
                type=SignalType.TREND_FOLLOWING,
                lookback_days=200,
                threshold=0.0,
            ),
            position_sizing=PositionSizingConfig(method=PositionSizingMethod.EQUAL_WEIGHT),
            rebalance=RebalanceConfig(frequency=RebalanceFrequency.WEEKLY),
        ),
        "dual_momentum": StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(
                id="DEMO-DUALMOM",
                name="Demo Dual Momentum",
                description="Demo strategy showing dual momentum template",
                tags=["demo", "momentum"],
            ),
            strategy_type="dual_momentum",
            universe=UniverseConfig(
                type=UniverseType.FIXED,
                symbols=["SPY", "EFA", "EEM"],
                defensive_symbols=["AGG"],
            ),
            signal=SignalConfig(
                type=SignalType.ABSOLUTE_MOMENTUM,
                lookback_days=252,
                selection_n=1,
                threshold=0.0,
            ),
            position_sizing=PositionSizingConfig(method=PositionSizingMethod.EQUAL_WEIGHT),
            rebalance=RebalanceConfig(frequency=RebalanceFrequency.MONTHLY),
        ),
        "breakout": StrategyDefinition(
            tier=1,
            metadata=StrategyMetadata(
                id="DEMO-BREAKOUT",
                name="Demo Breakout",
                description="Demo strategy showing breakout template",
                tags=["demo", "breakout"],
            ),
            strategy_type="breakout",
            universe=UniverseConfig(type=UniverseType.FIXED, symbols=["SPY"]),
            signal=SignalConfig(
                type=SignalType.BREAKOUT,
                lookback_days=20,
                threshold=0.05,  # 5% trailing stop
            ),
            position_sizing=PositionSizingConfig(method=PositionSizingMethod.EQUAL_WEIGHT),
            rebalance=RebalanceConfig(frequency=RebalanceFrequency.DAILY),
        ),
    }

    if strategy_type not in demo_strategies:
        typer.secho(
            f"Unknown strategy type: {strategy_type}. "
            f"Available: {', '.join(demo_strategies.keys())}",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    strategy = demo_strategies[strategy_type]
    engine = TemplateEngine()

    try:
        code = engine.render(strategy)

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(code)
            typer.secho(f"Generated demo: {output}", fg=typer.colors.GREEN)
        else:
            typer.echo(code)

    except CodeGenerationError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1) from None


@app.command("list-templates")
def list_templates():
    """List available strategy templates.

    Shows all supported strategy types and their corresponding templates.
    """
    from research_system.codegen.templates import (
        SIGNAL_TO_TEMPLATE,
        STRATEGY_TYPE_TO_TEMPLATE,
    )

    typer.secho("Strategy Type Templates:", fg=typer.colors.CYAN, bold=True)
    for strategy_type, template in sorted(STRATEGY_TYPE_TO_TEMPLATE.items()):
        typer.echo(f"  {strategy_type:20} -> {template}")

    typer.echo()
    typer.secho("Signal Type Templates:", fg=typer.colors.CYAN, bold=True)
    for signal_type, template in sorted(SIGNAL_TO_TEMPLATE.items()):
        typer.echo(f"  {signal_type:20} -> {template}")


def main():
    """Entry point for the codegen CLI."""
    app()


if __name__ == "__main__":
    main()
