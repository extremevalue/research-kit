"""
Research Validation System - Command Line Interface

A systematic framework for validating trading strategies and indicators.

Usage:
    research [--workspace PATH] <command> [<args>]

Commands:
    init        Initialize a new workspace
    ingest      Process files from inbox into catalog
    catalog     Manage catalog entries
    data        Manage data registry
    run         Run the full validation + expert review loop
    validate    Run validation pipeline (step-by-step)
    status      View dashboard and reports
    develop     Develop vague ideas into testable strategies
    combine     Generate and manage combinations
    analyze     Run persona-based analysis
    ideate      Generate strategy ideas using multiple personas
    synthesize  Run cross-strategy synthesis with expert panel
    migrate     Migrate from external sources

Run 'research <command> --help' for more information on a command.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from research_system import __version__
from research_system.core.workspace import (
    get_workspace,
    require_workspace,
    WorkspaceError,
    WORKSPACE_ENV_VAR
)
from research_system.core.catalog import Catalog
from research_system.core.data_registry import DataRegistry

# V4 imports
from research_system.core.v4 import (
    V4Workspace,
    get_v4_workspace,
    V4WorkspaceError,
    load_config,
    get_default_config,
    validate_config,
)


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        prog="research",
        description="Research Validation System - Systematic validation of trading strategies and indicators",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  research init ~/my-workspace          Initialize a new workspace
  research catalog list                  List all catalog entries
  research catalog show IND-002          Show entry details
  research validate start IND-002        Start validation for IND-002
  research validate status IND-002       Check validation status
  research combine generate              Generate combination matrix

Environment:
  RESEARCH_WORKSPACE    Path to workspace (default: ~/.research-workspace)

For more information, visit: https://github.com/your-repo/research-system
        """
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "--workspace", "-w",
        metavar="PATH",
        help=f"Path to workspace (default: ${WORKSPACE_ENV_VAR} or ~/.research-workspace)"
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        metavar="<command>"
    )

    # Add command parsers
    _add_init_parser(subparsers)

    # Legacy commands - disabled to avoid conflicts with new commands
    # _add_ingest_parser(subparsers)
    _add_catalog_parser(subparsers)
    _add_data_parser(subparsers)
    # _add_run_parser(subparsers)  # Conflicts with new 'run'
    # _add_validate_parser(subparsers)  # Conflicts with new 'validate'
    # _add_status_parser(subparsers)  # Conflicts with new 'status'
    _add_develop_parser(subparsers)  # Idea development workflow (R2)
    _add_combine_parser(subparsers)
    _add_analyze_parser(subparsers)
    # _add_ideate_parser(subparsers)  # Conflicts with new 'ideate'
    _add_synthesize_parser(subparsers)  # Cross-strategy synthesis
    _add_migrate_parser(subparsers)

    # Add main commands (formerly V4)
    _add_v4_commands(subparsers)

    # Add update command
    _add_update_parser(subparsers)

    return parser


def _add_update_parser(subparsers):
    """Add update command parser."""
    parser = subparsers.add_parser(
        "update",
        help="Update research-kit to the latest version",
        description="""
Update research-kit to the latest version from GitHub.

Automatically detects installation method and updates accordingly.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check for updates without installing"
    )
    parser.set_defaults(func=cmd_update)


def _add_init_parser(subparsers):
    """Add init command parser."""
    parser = subparsers.add_parser(
        "init",
        help="Initialize a new workspace",
        description="""
Initialize a new research workspace at the specified path.

Workspace structure:
  - inbox/                Files to be ingested
  - strategies/           Strategy documents by status
    - pending/            Newly ingested, awaiting validation
    - validated/          Passed validation
    - invalidated/        Failed validation
    - blocked/            Missing data dependencies
  - validations/          Walk-forward validation results
  - learnings/            Extracted learnings
  - ideas/                Strategy ideas (pre-formalization)
  - archive/              Archived/rejected items
  - logs/                 Daily rotating logs
  - research-kit.yaml     Configuration file
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Path for new workspace (default: ~/.research-workspace)"
    )
    parser.add_argument(
        "--name",
        default="My Research Workspace",
        help="Name for the workspace"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing workspace"
    )
    parser.set_defaults(func=cmd_init)


def _add_ingest_parser(subparsers):
    """Add ingest command parser."""
    parser = subparsers.add_parser(
        "ingest",
        help="Process files from inbox into catalog",
        description="Ingest files from the inbox folder into the catalog."
    )

    ingest_sub = parser.add_subparsers(dest="action", metavar="<action>")

    # ingest list
    list_parser = ingest_sub.add_parser("list", help="List files in inbox")
    list_parser.set_defaults(func=cmd_ingest_list)

    # ingest add
    add_parser = ingest_sub.add_parser("add", help="Add a file to inbox")
    add_parser.add_argument("file", help="File to add")
    add_parser.set_defaults(func=cmd_ingest_add)

    # ingest process
    process_parser = ingest_sub.add_parser("process", help="Process inbox files")
    process_parser.add_argument(
        "--file",
        help="Process specific file (default: all)"
    )
    process_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it"
    )
    process_parser.set_defaults(func=cmd_ingest_process)

    parser.set_defaults(func=lambda args: parser.print_help())


def _add_catalog_parser(subparsers):
    """Add catalog command parser."""
    parser = subparsers.add_parser(
        "catalog",
        help="Manage catalog entries",
        description="Manage the research catalog - list, view, add, and query entries."
    )

    catalog_sub = parser.add_subparsers(dest="action", metavar="<action>")

    # catalog list
    list_parser = catalog_sub.add_parser("list", help="List catalog entries")
    list_parser.add_argument("--type", choices=["indicator", "strategy", "idea", "learning", "tool", "data"],
                             help="Filter by type")
    list_parser.add_argument("--status", choices=["UNTESTED", "IN_PROGRESS", "VALIDATED", "CONDITIONAL", "INVALIDATED", "BLOCKED"],
                             help="Filter by status")
    list_parser.add_argument("--format", choices=["table", "json", "ids"], default="table",
                             help="Output format")
    list_parser.set_defaults(func=cmd_catalog_list)

    # catalog show
    show_parser = catalog_sub.add_parser("show", help="Show entry details")
    show_parser.add_argument("id", help="Entry ID (e.g., IND-002)")
    show_parser.set_defaults(func=cmd_catalog_show)

    # catalog add
    add_parser = catalog_sub.add_parser("add", help="Add a new entry")
    add_parser.add_argument("--type", required=True,
                            choices=["indicator", "strategy", "idea", "learning", "tool", "data"],
                            help="Entry type")
    add_parser.add_argument("--name", required=True, help="Entry name")
    add_parser.add_argument("--source", required=True, nargs="+", help="Source file paths")
    add_parser.add_argument("--summary", help="One-line summary")
    add_parser.add_argument("--hypothesis", help="Testable hypothesis")
    add_parser.add_argument("--tags", nargs="+", help="Tags")
    add_parser.set_defaults(func=cmd_catalog_add)

    # catalog stats
    stats_parser = catalog_sub.add_parser("stats", help="Show catalog statistics")
    stats_parser.set_defaults(func=cmd_catalog_stats)

    # catalog search
    search_parser = catalog_sub.add_parser("search", help="Search entries")
    search_parser.add_argument("query", help="Search query")
    search_parser.set_defaults(func=cmd_catalog_search)

    parser.set_defaults(func=lambda args: parser.print_help())


def _add_data_parser(subparsers):
    """Add data command parser."""
    parser = subparsers.add_parser(
        "data",
        help="Manage data registry",
        description="Manage data sources - list available data, check availability, add sources."
    )

    data_sub = parser.add_subparsers(dest="action", metavar="<action>")

    # data list
    list_parser = data_sub.add_parser("list", help="List data sources")
    list_parser.add_argument("--available", action="store_true", help="Only show available sources")
    list_parser.set_defaults(func=cmd_data_list)

    # data show
    show_parser = data_sub.add_parser("show", help="Show data source details")
    show_parser.add_argument("id", help="Data source ID")
    show_parser.set_defaults(func=cmd_data_show)

    # data check
    check_parser = data_sub.add_parser("check", help="Check data availability")
    check_parser.add_argument("ids", nargs="+", help="Data source IDs to check")
    check_parser.set_defaults(func=cmd_data_check)

    # data add
    add_parser = data_sub.add_parser("add", help="Add a data source")
    add_parser.add_argument("--id", required=True, help="Data source ID")
    add_parser.add_argument("--name", required=True, help="Data source name")
    add_parser.add_argument("--type", required=True, help="Data type")
    add_parser.set_defaults(func=cmd_data_add)

    parser.set_defaults(func=lambda args: parser.print_help())


def _add_run_parser(subparsers):
    """Add run command parser - the core validation + expert loop."""
    parser = subparsers.add_parser(
        "run",
        help="Run the full validation + expert review loop",
        description="""
Run the complete validation and expert review loop for catalog entries.

This is the core command that:
  1. Generates backtest code from hypothesis
  2. Runs IS backtest via lean CLI
  3. Checks gates (alpha, sharpe, drawdown)
  4. Runs OOS backtest (one shot)
  5. Runs expert review (multiple personas)
  6. Marks result (VALIDATED/INVALIDATED)
  7. Adds derived ideas to catalog

Usage:
  research run                    Process all UNTESTED entries
  research run STRAT-309          Process single entry
  research run --continue         Resume interrupted run
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "id",
        nargs="?",
        default=None,
        help="Entry ID to process (omit to process all UNTESTED)"
    )
    parser.add_argument(
        "--continue",
        dest="continue_run",
        action="store_true",
        help="Resume interrupted run"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without running"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local Docker backtest instead of cloud (downloads data from QC)"
    )
    parser.add_argument(
        "--walk-forward",
        action="store_true",
        help="Use walk-forward validation (12 windows from 2008-2024) instead of single IS/OOS"
    )
    parser.set_defaults(func=cmd_run)


def _add_validate_parser(subparsers):
    """Add validate command parser."""
    parser = subparsers.add_parser(
        "validate",
        help="Run validation pipeline",
        description="""
Run the validation pipeline for a catalog entry.

Pipeline stages:
  1. HYPOTHESIS  - Define and lock testable hypothesis
  2. DATA_AUDIT  - Verify data availability and quality
  3. IS_TESTING  - Run in-sample backtest
  4. STATISTICAL - Verify statistical significance
  5. REGIME      - Analyze performance by regime
  6. OOS_TESTING - Run out-of-sample backtest (ONE SHOT)
  7. DETERMINATION - Make final validation decision
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    validate_sub = parser.add_subparsers(dest="action", metavar="<action>")

    # validate start
    start_parser = validate_sub.add_parser("start", help="Start validation for an entry")
    start_parser.add_argument("id", help="Entry ID to validate")
    start_parser.set_defaults(func=cmd_validate_start)

    # validate status
    status_parser = validate_sub.add_parser("status", help="Check validation status")
    status_parser.add_argument("id", help="Entry ID")
    status_parser.set_defaults(func=cmd_validate_status)

    # validate audit
    audit_parser = validate_sub.add_parser("audit", help="Run data audit")
    audit_parser.add_argument("id", help="Entry ID")
    audit_parser.set_defaults(func=cmd_validate_audit)

    # validate run
    run_parser = validate_sub.add_parser("run", help="Run next validation step")
    run_parser.add_argument("id", help="Entry ID")
    run_parser.add_argument("--step", help="Specific step to run")
    run_parser.set_defaults(func=cmd_validate_run)

    # validate list
    list_parser = validate_sub.add_parser("list", help="List validations")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.set_defaults(func=cmd_validate_list)

    # validate hypothesis
    hypo_parser = validate_sub.add_parser("hypothesis", help="Submit hypothesis (locks parameters)")
    hypo_parser.add_argument("id", help="Entry ID")
    hypo_parser.add_argument("--file", required=True, help="Path to hypothesis.json")
    hypo_parser.set_defaults(func=cmd_validate_hypothesis)

    # validate submit-is
    is_parser = validate_sub.add_parser("submit-is", help="Submit in-sample backtest results")
    is_parser.add_argument("id", help="Entry ID")
    is_parser.add_argument("--file", required=True, help="Path to results.json")
    is_parser.add_argument("--baseline", help="Path to baseline results.json (optional)")
    is_parser.set_defaults(func=cmd_validate_submit_is)

    # validate submit-oos
    oos_parser = validate_sub.add_parser("submit-oos", help="Submit OOS results (ONE SHOT - no retries!)")
    oos_parser.add_argument("id", help="Entry ID")
    oos_parser.add_argument("--file", required=True, help="Path to results.json")
    oos_parser.add_argument("--confirm", action="store_true", help="Confirm one-shot OOS submission")
    oos_parser.set_defaults(func=cmd_validate_submit_oos)

    # validate check
    check_parser = validate_sub.add_parser("check", help="Re-check blocked entry for data availability")
    check_parser.add_argument("id", help="Entry ID")
    check_parser.set_defaults(func=cmd_validate_check)

    parser.set_defaults(func=lambda args: parser.print_help())


def _add_status_parser(subparsers):
    """Add status command parser - dashboard and reports."""
    parser = subparsers.add_parser(
        "status",
        help="View dashboard and reports",
        description="""
View strategy status, leaderboard, and pipeline reports.

This command generates markdown reports with links to detailed data:
  - dashboard.md  - Quick stats, top strategies, funnel, blockers
  - leaderboard.md - Full rankings of validated strategies
  - funnel.md - Detailed pipeline status
  - blockers.md - Data gaps and issues

Usage:
  research status              Show quick terminal summary
  research status --refresh    Regenerate all reports
  research status --open       Open dashboard in default viewer
  research status leaderboard  Show leaderboard in terminal
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "report",
        nargs="?",
        choices=["dashboard", "leaderboard", "funnel", "blockers"],
        help="Specific report to show (default: quick summary)"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Regenerate all reports from current data"
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open dashboard.md in default application"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top strategies to show (default: 10)"
    )
    parser.add_argument(
        "--sort",
        choices=["sharpe", "return", "consistency", "drawdown"],
        default="sharpe",
        help="Sort leaderboard by metric (default: sharpe)"
    )

    parser.set_defaults(func=cmd_status)


def _add_develop_parser(subparsers):
    """Add develop command parser - idea development workflow (R2)."""
    parser = subparsers.add_parser(
        "develop",
        help="Develop vague ideas into testable strategies",
        description="""
Develop ideas through a structured 10-step framework.

This command guides you through turning a vague idea into a fully
specified, testable strategy:

  1. Hypothesis       - What are we trying to prove?
  2. Success Criteria - How do we know it works?
  3. Universe         - What assets?
  4. Diversification  - Do they actually diversify?
  5. Structure        - Core+satellite, regime, or rotation?
  6. Signals          - Selection + timing signals
  7. Risk Management  - Position sizing, risk-off, limits
  8. Testing Protocol - Walk-forward methodology
  9. Implementation   - Data sources, schedule
  10. Monitoring      - Decay detection, stop criteria

Usage:
  research develop IDEA-001           Start/continue development
  research develop IDEA-001 --status  Show development progress
  research develop IDEA-001 --back    Go back to previous step
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "id",
        help="Entry ID to develop (e.g., IDEA-001)"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show development progress without advancing"
    )
    parser.add_argument(
        "--back",
        action="store_true",
        help="Go back to previous step"
    )
    parser.add_argument(
        "--classify",
        action="store_true",
        help="Show maturity classification without starting development"
    )
    parser.add_argument(
        "--complete",
        action="store_true",
        help="Mark development complete and generate strategy spec"
    )
    parser.add_argument(
        "--finalize",
        action="store_true",
        help="Create strategy entry from development and optionally run validation"
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="With --finalize: also run walk-forward validation on created strategy"
    )

    parser.set_defaults(func=cmd_develop)


def _add_combine_parser(subparsers):
    """Add combine command parser."""
    parser = subparsers.add_parser(
        "combine",
        help="Generate and manage combinations",
        description="Generate indicator + strategy combinations and prioritize them for testing."
    )

    combine_sub = parser.add_subparsers(dest="action", metavar="<action>")

    # combine generate
    gen_parser = combine_sub.add_parser("generate", help="Generate combination matrix")
    gen_parser.add_argument("--status", nargs="+", default=["VALIDATED", "CONDITIONAL"],
                            help="Include entries with these statuses")
    gen_parser.set_defaults(func=cmd_combine_generate)

    # combine list
    list_parser = combine_sub.add_parser("list", help="List combinations")
    list_parser.add_argument("--top", type=int, help="Show top N by priority")
    list_parser.set_defaults(func=cmd_combine_list)

    # combine prioritize
    prio_parser = combine_sub.add_parser("prioritize", help="Prioritize combinations")
    prio_parser.set_defaults(func=cmd_combine_prioritize)

    # combine next
    next_parser = combine_sub.add_parser("next", help="Get next batch to test")
    next_parser.add_argument("--count", type=int, default=5, help="Number of combinations")
    next_parser.set_defaults(func=cmd_combine_next)

    parser.set_defaults(func=lambda args: parser.print_help())


def _add_analyze_parser(subparsers):
    """Add analyze command parser."""
    parser = subparsers.add_parser(
        "analyze",
        help="Run persona-based analysis",
        description="""
Run multi-persona analysis on validation results.

Personas:
  - momentum-trader  : Trend-following perspective
  - risk-manager     : Risk and drawdown focus
  - quant-researcher : Statistical rigor
  - contrarian       : Challenges consensus
  - report-synthesizer: Integrates all perspectives
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    analyze_sub = parser.add_subparsers(dest="action", metavar="<action>")

    # analyze run
    run_parser = analyze_sub.add_parser("run", help="Run persona analysis")
    run_parser.add_argument("id", help="Entry ID to analyze")
    run_parser.add_argument("--persona", help="Run specific persona only")
    run_parser.set_defaults(func=cmd_analyze_run)

    # analyze show
    show_parser = analyze_sub.add_parser("show", help="Show analysis results")
    show_parser.add_argument("id", help="Entry ID")
    show_parser.set_defaults(func=cmd_analyze_show)

    parser.set_defaults(func=lambda args: parser.print_help())


def _add_ideate_parser(subparsers):
    """Add ideate command parser."""
    parser = subparsers.add_parser(
        "ideate",
        help="Generate strategy ideas using multiple personas",
        description="""
Generate novel strategy ideas using three diverse personas:

Personas:
  - edge-hunter        : Finds timing and micro-structure edges
  - macro-strategist   : Cross-asset, regime-aware themes
  - quant-archaeologist: Rehabilitates failed approaches

Each persona generates 1-2 ideas based on:
  - Available data in the registry
  - Validated and invalidated catalog entries
  - Untested ideas in the pipeline

Output: 3-6 new IDEA entries added to the catalog.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--count",
        type=int,
        default=2,
        help="Target ideas per persona (default: 2)"
    )
    parser.add_argument(
        "--persona",
        choices=["edge-hunter", "macro-strategist", "quant-archaeologist"],
        help="Run only a specific persona"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate ideas but don't add to catalog"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save raw ideation results to file"
    )
    parser.set_defaults(func=cmd_ideate)


def _add_synthesize_parser(subparsers):
    """Add synthesize command parser."""
    parser = subparsers.add_parser(
        "synthesize",
        help="Run cross-strategy synthesis with expert panel",
        description="""
Run multi-persona synthesis on validated strategies to identify:
- Portfolio construction opportunities
- Instrument expansion (options, futures)
- Data enhancement recommendations
- Regime-based combinations
- Creative/unconventional ideas

Personas:
  - portfolio-architect   : Correlation, allocation, portfolio construction
  - instrument-specialist : Options, futures, ETF opportunities
  - data-integrator       : Alternative data enhancement
  - regime-strategist     : Market regime analysis
  - creative-maverick     : Unconventional ideas and combinations
  - synthesis-director    : Integrates all perspectives

Output: Both a detailed report and optional new catalog entries.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--min-sharpe",
        type=float,
        help="Minimum Sharpe ratio filter for strategies"
    )
    parser.add_argument(
        "--max-drawdown",
        type=float,
        help="Maximum drawdown filter (e.g., 0.3 for 30%%)"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=50,
        help="Limit to top N strategies by Sharpe (default: 50)"
    )
    parser.add_argument(
        "--create-entries",
        action="store_true",
        help="Create new catalog entries from recommendations"
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate report without running synthesis (uses cached results)"
    )
    parser.add_argument(
        "--persona",
        choices=["portfolio-architect", "instrument-specialist", "data-integrator",
                 "regime-strategist", "creative-maverick"],
        help="Run only a specific persona"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be analyzed without running"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save raw synthesis results to file"
    )
    parser.set_defaults(func=cmd_synthesize)


def _add_migrate_parser(subparsers):
    """Add migrate command parser."""
    parser = subparsers.add_parser(
        "migrate",
        help="Migrate from external sources",
        description="Migrate data from external sources like MASTER_INDEX.json."
    )

    migrate_sub = parser.add_subparsers(dest="action", metavar="<action>")

    # migrate master-index
    mi_parser = migrate_sub.add_parser("master-index", help="Migrate from MASTER_INDEX.json")
    mi_parser.add_argument("source", help="Path to MASTER_INDEX.json")
    mi_parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated")
    mi_parser.add_argument("--validate-only", action="store_true", help="Only validate, don't migrate")
    mi_parser.set_defaults(func=cmd_migrate_master_index)

    parser.set_defaults(func=lambda args: parser.print_help())


# ============================================================================
# V4 Command Parsers
# ============================================================================


def _add_v4_commands(subparsers):
    """Add V4-related subcommands.

    V4 commands support the new research workflow:
    - init: Initialize workspace
    - ingest: Ingest files from inbox with quality scoring
    - verify: Run verification tests (bias detection)
    - validate: Run walk-forward validation
    - learn: Extract learnings from validation results
    - status: Show workspace status dashboard
    - list: List strategies with filtering
    - show: Show strategy details
    - config: Show/validate configuration
    """
    # ingest command
    parser = subparsers.add_parser(
        "ingest",
        help="Ingest files from inbox into strategies ",
        description="""
Process files from the inbox directory and create strategy documents.
Runs quality scoring (specificity, trust) and red flag detection.

Files are processed from the inbox/ directory. Each file is analyzed
to extract strategy details, scored for quality, and checked for red flags.
Strategies meeting minimum thresholds are created in strategies/pending/.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Specific files to ingest (default: all files in inbox)"
    )
    parser.add_argument(
        "--workspace", "-w",
        dest="v4_workspace",
        metavar="PATH",
        help="Path to workspace (default: RESEARCH_WORKSPACE or ~/.research-workspace)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        dest="dry_run",
        help="Show what would happen without making changes"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip quality checks and create strategies anyway (useful for testing without API key)"
    )
    parser.set_defaults(func=cmd_v4_ingest)

    # verify command
    parser = subparsers.add_parser(
        "verify",
        help="Run verification tests on a strategy ",
        description="""
Run verification tests on a strategy to check for biases and issues.

Tests include:
  - look_ahead_bias: Check for future information leakage
  - survivorship_bias: Check for survivorship bias in data
  - position_sizing: Validate position sizing logic
  - data_availability: Verify all required data is available
  - parameter_sanity: Check parameter values are reasonable
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "strategy_id",
        nargs="?",
        help="Strategy ID to verify (e.g., STRAT-001)"
    )
    parser.add_argument(
        "--workspace", "-w",
        dest="v4_workspace",
        metavar="PATH",
        help="Path to workspace"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show results without saving"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        dest="process_all",
        help="Verify all pending strategies"
    )
    parser.set_defaults(func=cmd_v4_verify)

    # validate command
    parser = subparsers.add_parser(
        "validate",
        help="Run walk-forward validation on a strategy ",
        description="""
Run walk-forward validation (backtesting) on a strategy.
Applies configured gates (Sharpe, consistency, drawdown).

Walk-forward validation uses multiple time windows to test
strategy robustness across different market regimes.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "strategy_id",
        nargs="?",
        help="Strategy ID to validate (e.g., STRAT-001)"
    )
    parser.add_argument(
        "--workspace", "-w",
        dest="v4_workspace",
        metavar="PATH",
        help="Path to workspace"
    )
    parser.add_argument(
        "--results", "-r",
        metavar="FILE",
        help="JSON/YAML file with backtest results (sharpe_ratio, max_drawdown, win_rate)"
    )
    parser.add_argument(
        "--generate-config",
        action="store_true",
        help="Generate backtest configuration file instead of validating"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show results without saving or updating status"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        dest="process_all",
        help="Validate all strategies that have verification results"
    )
    parser.set_defaults(func=cmd_v4_validate)

    # learn command
    parser = subparsers.add_parser(
        "learn",
        help="Extract learnings from validation results ",
        description="""
Extract learnings from validation results for future reference.

Analyzes validation results to identify:
  - What worked and why
  - What failed and why
  - Patterns that could inform future strategies
  - Data gaps that need to be filled
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "strategy_id",
        nargs="?",
        help="Strategy ID to extract learnings from (e.g., STRAT-001)"
    )
    parser.add_argument(
        "--workspace", "-w",
        dest="v4_workspace",
        metavar="PATH",
        help="Path to workspace"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show learnings without saving"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        dest="process_all",
        help="Extract learnings from all strategies with validation results"
    )
    parser.set_defaults(func=cmd_v4_learn)

    # ideate command
    parser = subparsers.add_parser(
        "ideate",
        help="Generate new strategy ideas ",
        description="""
Generate new strategy ideas based on existing strategies and learnings.

Ideas are generated by:
  - Creating variations of existing strategies (timeframe, instrument, etc.)
  - Addressing issues found in validation failures
  - Suggesting generic strategy patterns if no strategies exist
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--workspace", "-w",
        dest="v4_workspace",
        metavar="PATH",
        help="Path to workspace"
    )
    parser.add_argument(
        "--max-ideas", "-n",
        type=int,
        default=5,
        help="Maximum number of ideas to generate (default: 5)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show ideas without saving"
    )
    parser.set_defaults(func=cmd_v4_ideate)

    # run command
    parser = subparsers.add_parser(
        "run",
        help="Run full validation pipeline ",
        description="""
Run the complete validation pipeline for a strategy:

1. Generate QuantConnect Python code (template or LLM)
2. Run walk-forward backtest via LEAN CLI
3. Apply validation gates from config
4. Update status (validated/invalidated)
5. Save results

Examples:
  research run STRAT-001              # Full pipeline for one strategy
  research run --all                  # Batch process all pending
  research run STRAT-001 --local      # Use local Docker instead of cloud
  research run --all --dry-run        # Preview without running
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "strategy_id",
        nargs="?",
        help="Strategy ID to run (e.g., STRAT-001)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all pending strategies"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local Docker backtest instead of QC cloud"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would happen without running backtests"
    )
    parser.add_argument(
        "--force-llm",
        action="store_true",
        help="Force LLM code generation instead of templates"
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip verification check before running"
    )
    parser.add_argument(
        "--windows",
        type=int,
        default=1,
        choices=[1, 2, 5],
        help="Number of walk-forward windows: 1 (fastest), 2 (IS/OOS), or 5 (thorough). Default: 1"
    )
    parser.add_argument(
        "--workspace", "-w",
        dest="v4_workspace",
        metavar="PATH",
        help="Path to workspace"
    )
    parser.set_defaults(func=cmd_v4_run)

    # cleanup command
    parser = subparsers.add_parser(
        "cleanup",
        help="Clean up stuck QC backtests ",
        description="""
Clean up stuck or queued backtests on QuantConnect cloud.

Use this when you see "no spare nodes available" errors. This command
will cancel running/queued backtests that may be blocking resources.

Examples:
  research cleanup                    # Clean backtests older than 5 min
  research cleanup --aggressive       # Clean ALL running backtests
  research cleanup --dry-run          # Show what would be cleaned
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--aggressive",
        action="store_true",
        help="Clean ALL running backtests, not just stuck ones"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without actually cleaning"
    )
    parser.add_argument(
        "--workspace", "-w",
        dest="v4_workspace",
        metavar="PATH",
        help="Path to workspace"
    )
    parser.set_defaults(func=cmd_v4_cleanup)

    # walkforward command
    parser = subparsers.add_parser(
        "walkforward",
        help="Run true walk-forward optimization ",
        description="""
Run true walk-forward optimization for a strategy with tunable parameters.

Walk-forward validation:
1. Optimize parameters on in-sample data (historical)
2. Test optimized params on out-of-sample data (future)
3. Repeat for each period
4. Aggregate out-of-sample results

This simulates live trading where parameters are re-optimized
periodically using only available data.

Examples:
  research walkforward STRAT-001           # Run walk-forward validation
  research walkforward STRAT-001 --json    # Output as JSON
  research walkforward STRAT-001 --params  # Show parameter evolution
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "strategy_id",
        help="Strategy ID to analyze (e.g., STRAT-001)"
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2012,
        help="Start year for walk-forward (default: 2012)"
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2023,
        help="End year for walk-forward (default: 2023)"
    )
    parser.add_argument(
        "--train-years",
        type=int,
        default=3,
        help="Initial training period in years (default: 3)"
    )
    parser.add_argument(
        "--test-years",
        type=int,
        default=1,
        help="Test period in years (default: 1)"
    )
    parser.add_argument(
        "--max-evals",
        type=int,
        default=50,
        help="Max parameter evaluations per period (default: 50)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--params",
        action="store_true",
        help="Show parameter evolution across periods"
    )
    parser.add_argument(
        "--workspace", "-w",
        dest="v4_workspace",
        metavar="PATH",
        help="Path to workspace"
    )
    parser.set_defaults(func=cmd_v4_walkforward)

    # status command
    parser = subparsers.add_parser(
        "status",
        help="Show workspace status dashboard ",
        description="""
Show workspace status: strategy counts by status, recent activity.

Displays a summary of the workspace including:
  - Strategies by status (pending, validated, invalidated, blocked)
  - Ideas count
  - Inbox files waiting to be processed
  - Recent activity
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--workspace", "-w",
        dest="v4_workspace",
        metavar="PATH",
        help="Path to workspace"
    )
    parser.set_defaults(func=cmd_v4_status)

    # list command
    parser = subparsers.add_parser(
        "list",
        help="List strategies ",
        description="""
List strategies, optionally filtered by status.

Statuses:
  - pending: Awaiting validation
  - validated: Passed all validation gates
  - invalidated: Failed validation gates
  - blocked: Missing data or dependencies
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--status",
        choices=["pending", "validated", "invalidated", "blocked"],
        help="Filter by status"
    )
    parser.add_argument(
        "--tags",
        metavar="TAGS",
        help="Filter by tags (comma-separated)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)"
    )
    parser.add_argument(
        "--workspace", "-w",
        dest="v4_workspace",
        metavar="PATH",
        help="Path to workspace"
    )
    parser.set_defaults(func=cmd_v4_list)

    # show command
    parser = subparsers.add_parser(
        "show",
        help="Show strategy details ",
        description="""
Display full details of a strategy document.

Shows all strategy metadata including:
  - Name and description
  - Hypothesis and test parameters
  - Data requirements
  - Validation results (if available)
  - Learnings extracted
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "strategy_id",
        help="Strategy ID to show (e.g., STRAT-001)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "yaml", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--workspace", "-w",
        dest="v4_workspace",
        metavar="PATH",
        help="Path to workspace"
    )
    parser.set_defaults(func=cmd_v4_show)

    # config command
    parser = subparsers.add_parser(
        "config",
        help="Show/validate configuration",
        description="""
Show current configuration, or validate with --validate flag.

Configuration includes:
  - Gate thresholds (Sharpe, consistency, drawdown)
  - Ingestion settings (specificity, trust scores)
  - Verification tests enabled
  - Red flag detection settings
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration and show any warnings"
    )
    parser.add_argument(
        "--workspace", "-w",
        dest="v4_workspace",
        metavar="PATH",
        help="Path to workspace"
    )
    parser.set_defaults(func=cmd_v4_config)


# ============================================================================
# Command Implementations
# ============================================================================

def cmd_init(args):
    """Initialize a new workspace."""
    # Always use workspace format
    return cmd_init_v4(args)


def cmd_init_v4(args):
    """Initialize a new workspace."""
    path = Path(args.path) if args.path else None
    workspace = get_v4_workspace(path)

    if workspace.exists and not args.force:
        print(f"workspace already exists at {workspace.path}")
        print("Use --force to reinitialize")
        return 1

    workspace.init(name=args.name, force=args.force)
    print(f"Initialized workspace at {workspace.path}")
    print()
    print("Workspace structure:")
    print(f"  {workspace.path}/")
    print(f"  ├── inbox/                # Drop files here to ingest")
    print(f"  ├── strategies/")
    print(f"  │   ├── pending/          # Awaiting validation")
    print(f"  │   ├── validated/        # Passed validation gates")
    print(f"  │   ├── invalidated/      # Failed validation gates")
    print(f"  │   └── blocked/          # Missing data/dependencies")
    print(f"  ├── validations/          # Walk-forward validation results")
    print(f"  ├── learnings/            # Extracted learnings")
    print(f"  ├── ideas/                # Strategy ideas")
    print(f"  ├── personas/             # Persona configurations")
    print(f"  ├── archive/              # Archived strategies")
    print(f"  ├── logs/                 # Daily rotating logs")
    print(f"  ├── .state/               # Internal state (counters)")
    print(f"  ├── research-kit.yaml     # Configuration")
    print(f"  └── .env.template         # Environment template")
    print()
    print("Next steps:")
    print(f"  1. Copy .env.template to .env and add your API keys")
    print(f"  2. Add files to {workspace.inbox_path}/")
    print("  3. Run 'research ingest' to create strategy documents")
    print("  4. Run 'research verify STRAT-001' to run verification tests")
    print("  5. Run 'research validate STRAT-001' to run walk-forward validation")
    return 0


# ============================================================================
# V4 Command Implementations
# ============================================================================


def cmd_v4_ingest(args):
    """Ingest files from inbox into strategies ."""
    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init' to initialize a workspace.")
        return 1

    # Import processor and LLM client
    from research_system.ingest.v4_processor import V4IngestProcessor
    from research_system.llm.client import get_client as get_llm_client
    from research_system.schemas.v4 import IngestionDecision

    # Get configuration and LLM client
    config = workspace.config
    try:
        llm_client = get_llm_client()
    except Exception:
        llm_client = None

    # Initialize processor
    processor = V4IngestProcessor(workspace, config, llm_client)

    # Check options
    dry_run = getattr(args, 'dry_run', False)
    force = getattr(args, 'force', False)

    if dry_run:
        print("=== DRY RUN MODE ===")
        print("No files will be saved or moved.\n")

    if force:
        print("=== FORCE MODE ===")
        print("Quality checks bypassed - all files will create strategies.\n")

    # Process specific files or entire inbox
    if args.files:
        # Process specific files
        results = []
        total_files = len(args.files)
        print(f"Processing {total_files} file(s)...\n")
        for i, file_arg in enumerate(args.files, 1):
            file_path = Path(file_arg)
            if not file_path.exists():
                # Try relative to inbox
                file_path = workspace.inbox_path / file_arg
            if not file_path.exists():
                print(f"[{i}/{total_files}] Error: File not found: {file_arg}")
                continue
            print(f"[{i}/{total_files}] Processing: {file_path.name}...", flush=True)
            result = processor.process_file(file_path, dry_run=dry_run, force=force)
            results.append(result)
    else:
        # Process entire inbox - first count files
        inbox_files = [
            f for f in workspace.inbox_path.rglob("*")
            if f.is_file() and not f.name.startswith('.') and f.name != '.gitkeep'
        ]
        total_files = len(inbox_files)

        if total_files == 0:
            print(f"No files found in inbox: {workspace.inbox_path}")
            print("\nAdd files to the inbox directory and run again.")
            return 0

        print(f"Found {total_files} file(s) in inbox. Processing...\n")

        # Process with progress output
        results = []
        for i, file_path in enumerate(sorted(inbox_files), 1):
            print(f"[{i}/{total_files}] Processing: {file_path.name}...", flush=True)
            result = processor.process_file(file_path, dry_run=dry_run, force=force)
            results.append(result)

        print()  # Blank line after progress

    # Display results
    for result in results:
        print(f"Processing: {result.filename}")

        if result.error and not result.decision:
            print(f"  Error: {result.error}")
            print()
            continue

        if result.strategy_name:
            print(f"  Extracted: \"{result.strategy_name}\"")

        if result.quality:
            spec_score = result.quality.specificity.score
            trust_total = result.quality.trust_score.total
            print(f"  Quality: specificity={spec_score}/8, trust={trust_total}/100")

            # Show red flags if any
            if result.quality.red_flags:
                hard_flags = [rf for rf in result.quality.red_flags if rf.severity.value == "hard"]
                soft_flags = [rf for rf in result.quality.red_flags if rf.severity.value == "soft"]
                if hard_flags:
                    print(f"  Red flags (HARD): {', '.join(rf.flag for rf in hard_flags)}")
                if soft_flags:
                    print(f"  Red flags (soft): {', '.join(rf.flag for rf in soft_flags)}")

        if result.decision:
            decision_str = result.decision.value.upper()
            print(f"  Decision: {decision_str}")

        if result.success and result.strategy_id:
            print(f"  Strategy ID: {result.strategy_id}")
            if result.saved_path:
                print(f"  Saved: {result.saved_path}")
        elif result.error:
            print(f"  Reason: {result.error}")

        print()

    # Summary
    if not args.files:
        # Compute summary from results
        accepted = sum(1 for r in results if r.decision == IngestionDecision.ACCEPT)
        queued = sum(1 for r in results if r.decision == IngestionDecision.QUEUE)
        archived = sum(1 for r in results if r.decision == IngestionDecision.ARCHIVE)
        rejected = sum(1 for r in results if r.decision == IngestionDecision.REJECT)
        errors = sum(1 for r in results if r.error and not r.decision)
        processed = accepted + queued + archived + rejected

        print("=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"Total files:  {total_files}")
        print(f"Processed:    {processed}")
        print(f"  Accepted:   {accepted}")
        print(f"  Queued:     {queued}")
        print(f"  Archived:   {archived}")
        print(f"  Rejected:   {rejected}")
        if errors > 0:
            print(f"  Errors:     {errors}")

    return 0


def _cmd_v4_verify_all(workspace, args):
    """Verify all pending strategies."""
    from research_system.validation import V4Verifier, VerificationStatus

    dry_run = getattr(args, 'dry_run', False)

    # Get all pending strategies
    strategies = workspace.list_strategies(status='pending')
    if not strategies:
        print("No pending strategies to verify.")
        return 0

    print(f"\nVerifying {len(strategies)} pending strategy(ies)...")
    print("=" * 50)

    verifier = V4Verifier(workspace)
    results = {'passed': 0, 'warnings': 0, 'failed': 0}

    for i, strat_info in enumerate(strategies, 1):
        strategy_id = strat_info['id']
        strategy = workspace.get_strategy(strategy_id)
        if not strategy:
            print(f"[{i}/{len(strategies)}] {strategy_id}: ERROR - Could not load")
            continue

        result = verifier.verify(strategy)

        if result.overall_status == VerificationStatus.PASS:
            status_str = "PASS"
            results['passed'] += 1
        elif result.overall_status == VerificationStatus.WARN:
            status_str = f"WARN ({result.warnings} warnings)"
            results['warnings'] += 1
        else:
            status_str = f"FAIL ({result.failed} failures)"
            results['failed'] += 1

        print(f"[{i}/{len(strategies)}] {strategy_id}: {status_str}")

        if not dry_run:
            verifier.save_result(result)

    # Summary
    print("\n" + "=" * 50)
    print("BATCH VERIFICATION COMPLETE")
    print("=" * 50)
    print(f"  Total:    {len(strategies)}")
    print(f"  Passed:   {results['passed']}")
    print(f"  Warnings: {results['warnings']}")
    print(f"  Failed:   {results['failed']}")

    if dry_run:
        print("\n[DRY RUN] Results not saved")
    else:
        print(f"\nResults saved to: {workspace.validations_path}")

    return 0


def _cmd_v4_validate_all(workspace, args):
    """Validate all strategies that have verification results."""
    from research_system.validation import V4Verifier, V4Validator, VerificationStatus, GateStatus

    dry_run = getattr(args, 'dry_run', False)
    results_file = getattr(args, 'results', None)

    # Load backtest results if provided (shared across all strategies)
    backtest_results = None
    if results_file:
        import json
        import yaml
        results_path = Path(results_file)
        if results_path.exists():
            with open(results_path) as f:
                if results_path.suffix == '.json':
                    backtest_results = json.load(f)
                else:
                    backtest_results = yaml.safe_load(f)
            print(f"Using backtest results from: {results_file}")
        else:
            print(f"Warning: Results file not found: {results_file}")

    # Find strategies with verification results
    validations_path = workspace.validations_path
    if not validations_path.exists():
        print("No verification results found. Run 'research verify --all' first.")
        return 0

    # Get unique strategy IDs from verification files
    verify_files = list(validations_path.glob("*_verify_*.yaml"))
    strategy_ids = set()
    for f in verify_files:
        # Extract STRAT-XXX from filename like STRAT-001_verify_20260124_143945.yaml
        parts = f.stem.split('_verify_')
        if parts:
            strategy_ids.add(parts[0])

    if not strategy_ids:
        print("No verified strategies found. Run 'research verify --all' first.")
        return 0

    print(f"\nValidating {len(strategy_ids)} verified strategy(ies)...")
    print("=" * 50)

    verifier = V4Verifier(workspace)
    validator = V4Validator(workspace, verifier)
    results = {'passed': 0, 'failed': 0, 'skipped': 0}

    for i, strategy_id in enumerate(sorted(strategy_ids), 1):
        strategy = workspace.get_strategy(strategy_id)
        if not strategy:
            print(f"[{i}/{len(strategy_ids)}] {strategy_id}: SKIP - Not found")
            results['skipped'] += 1
            continue

        result = validator.validate(strategy, backtest_results)

        if backtest_results:
            if result.overall_passed:
                status_str = "PASSED"
                results['passed'] += 1
            else:
                failed_gates = [g.gate.value for g in result.gates if g.status == GateStatus.FAIL]
                status_str = f"FAILED ({', '.join(failed_gates)})"
                results['failed'] += 1

            print(f"[{i}/{len(strategy_ids)}] {strategy_id}: {status_str}")

            if not dry_run:
                validator.save_result(result)
                validator.update_strategy_status(strategy_id, result.overall_passed)
        else:
            print(f"[{i}/{len(strategy_ids)}] {strategy_id}: PENDING (no backtest results)")
            results['skipped'] += 1

    # Summary
    print("\n" + "=" * 50)
    print("BATCH VALIDATION COMPLETE")
    print("=" * 50)
    print(f"  Total:   {len(strategy_ids)}")
    print(f"  Passed:  {results['passed']}")
    print(f"  Failed:  {results['failed']}")
    print(f"  Skipped: {results['skipped']}")

    if not backtest_results:
        print("\nNote: No backtest results provided. Use --results <file> to apply gates.")
    elif dry_run:
        print("\n[DRY RUN] Results not saved, statuses not updated")

    return 0


def _cmd_v4_learn_all(workspace, args):
    """Extract learnings from all strategies with validation results."""
    from research_system.validation import V4Learner

    dry_run = getattr(args, 'dry_run', False)

    # Find strategies with validation results
    validations_path = workspace.validations_path
    if not validations_path.exists():
        print("No validation results found. Run 'research validate --all' first.")
        return 0

    # Get unique strategy IDs from validation files
    all_files = list(validations_path.glob("STRAT-*_*.yaml"))
    strategy_ids = set()
    for f in all_files:
        # Extract STRAT-XXX from filename
        parts = f.stem.split('_')
        if parts and parts[0].startswith('STRAT-'):
            strategy_ids.add(parts[0])

    if not strategy_ids:
        print("No validated strategies found.")
        return 0

    print(f"\nExtracting learnings from {len(strategy_ids)} strategy(ies)...")
    print("=" * 50)

    learner = V4Learner(workspace)
    results = {'extracted': 0, 'skipped': 0}

    for i, strategy_id in enumerate(sorted(strategy_ids), 1):
        strategy = workspace.get_strategy(strategy_id)
        if not strategy:
            print(f"[{i}/{len(strategy_ids)}] {strategy_id}: SKIP - Not found")
            results['skipped'] += 1
            continue

        verification_results, validation_results = learner.load_results(strategy_id)

        if not verification_results and not validation_results:
            print(f"[{i}/{len(strategy_ids)}] {strategy_id}: SKIP - No results")
            results['skipped'] += 1
            continue

        doc = learner.extract_learnings(strategy, verification_results, validation_results)
        learning_count = len(doc.learnings)

        print(f"[{i}/{len(strategy_ids)}] {strategy_id}: {learning_count} learning(s)")
        results['extracted'] += 1

        if not dry_run:
            learner.save_learnings(doc)

    # Summary
    print("\n" + "=" * 50)
    print("BATCH LEARNING EXTRACTION COMPLETE")
    print("=" * 50)
    print(f"  Total:     {len(strategy_ids)}")
    print(f"  Extracted: {results['extracted']}")
    print(f"  Skipped:   {results['skipped']}")

    if dry_run:
        print("\n[DRY RUN] Learnings not saved")
    else:
        print(f"\nLearnings saved to: {workspace.learnings_path}")

    return 0


def cmd_v4_verify(args):
    """Run verification tests on a strategy ."""
    from research_system.validation import V4Verifier, VerificationStatus

    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init' to initialize a workspace.")
        return 1

    process_all = getattr(args, 'process_all', False)
    strategy_id = args.strategy_id

    # Handle --all flag
    if process_all:
        return _cmd_v4_verify_all(workspace, args)

    if not strategy_id:
        print("Error: Strategy ID required")
        print("Usage: research verify STRAT-001")
        print("       research verify --all")
        return 1

    # Load strategy
    strategy = workspace.get_strategy(strategy_id)
    if strategy is None:
        print(f"Error: Strategy '{strategy_id}' not found")
        return 1

    dry_run = getattr(args, 'dry_run', False)

    # Run verification
    print(f"\nVerifying strategy: {strategy_id}")
    print("=" * 50)

    verifier = V4Verifier(workspace)
    result = verifier.verify(strategy)

    # Display results
    for test in result.tests:
        if test.status == VerificationStatus.PASS:
            status_icon = "[PASS]"
        elif test.status == VerificationStatus.FAIL:
            status_icon = "[FAIL]"
        elif test.status == VerificationStatus.WARN:
            status_icon = "[WARN]"
        else:
            status_icon = "[SKIP]"

        print(f"{status_icon} {test.name}: {test.message}")
        if test.details:
            for key, value in test.details.items():
                if isinstance(value, list):
                    for item in value:
                        print(f"         - {item}")
                else:
                    print(f"         {key}: {value}")

    # Summary
    print("\n" + "=" * 50)
    print(f"OVERALL: {result.overall_status.value.upper()}")
    print(f"  Passed:   {result.passed}/{len(result.tests)}")
    print(f"  Warnings: {result.warnings}")
    print(f"  Failed:   {result.failed}")

    # Save result
    if not dry_run:
        saved_path = verifier.save_result(result)
        print(f"\nResult saved to: {saved_path}")
    else:
        print("\n[DRY RUN] Result not saved")

    return 0 if result.overall_status != VerificationStatus.FAIL else 1


def cmd_v4_validate(args):
    """Run walk-forward validation on a strategy ."""
    import json
    import yaml
    from research_system.validation import (
        V4Verifier,
        V4Validator,
        VerificationStatus,
        GateStatus,
    )

    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init' to initialize a workspace.")
        return 1

    process_all = getattr(args, 'process_all', False)
    strategy_id = args.strategy_id

    # Handle --all flag
    if process_all:
        return _cmd_v4_validate_all(workspace, args)

    if not strategy_id:
        print("Error: Strategy ID required")
        print("Usage: research validate STRAT-001")
        print("       research validate --all --results backtest.json")
        return 1

    # Load strategy
    strategy = workspace.get_strategy(strategy_id)
    if strategy is None:
        print(f"Error: Strategy '{strategy_id}' not found")
        return 1

    dry_run = getattr(args, 'dry_run', False)
    results_file = getattr(args, 'results', None)
    generate_config = getattr(args, 'generate_config', False)

    print(f"\nValidating strategy: {strategy_id}")
    print("=" * 50)

    # Step 1: Run verification first
    print("\n[Step 1] Running verification...")
    verifier = V4Verifier(workspace)
    verify_result = verifier.verify(strategy)

    if verify_result.overall_status == VerificationStatus.FAIL:
        print(f"  FAILED - Strategy has {verify_result.failed} verification failures")
        print("  Run 'research verify' to see details")
        print("\n  Validation cannot proceed until verification passes.")
        return 1
    elif verify_result.overall_status == VerificationStatus.WARN:
        print(f"  PASSED with {verify_result.warnings} warning(s)")
    else:
        print("  PASSED")

    # Step 2: Initialize validator
    validator = V4Validator(workspace, verifier)

    # Step 3: Generate backtest config if requested
    if generate_config:
        print("\n[Step 2] Generating backtest configuration...")
        config = validator.generate_backtest_config(strategy)
        config_path = workspace.path / "validations" / f"{strategy_id}_backtest_config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"  Config saved to: {config_path}")
        print("\n  Next steps:")
        print("  1. Run backtest using this configuration")
        print("  2. Save results to a JSON file with: sharpe_ratio, max_drawdown, win_rate")
        print(f"  3. Re-run: research validate {strategy_id} --results <results.json>")
        return 0

    # Step 4: Load backtest results if provided
    backtest_results = None
    if results_file:
        print(f"\n[Step 2] Loading backtest results from {results_file}...")
        results_path = Path(results_file)
        if not results_path.exists():
            print(f"  Error: Results file not found: {results_file}")
            return 1

        with open(results_path) as f:
            if results_path.suffix == '.json':
                backtest_results = json.load(f)
            else:
                backtest_results = yaml.safe_load(f)

        print(f"  Loaded metrics: {list(backtest_results.keys())}")
    else:
        print("\n[Step 2] No backtest results provided")
        print("  Use --generate-config to create backtest configuration")
        print("  Use --results <file> to apply validation gates to results")

    # Step 5: Run validation
    print("\n[Step 3] Applying validation gates...")
    result = validator.validate(strategy, backtest_results)

    gates = validator.get_gates()
    print(f"  Configured gates:")
    for gate, threshold in gates.items():
        if gate.value == "max_drawdown":
            print(f"    - {gate.value}: ≤ {threshold:.1%}")
        else:
            print(f"    - {gate.value}: ≥ {threshold}")

    if result.gates:
        print("\n  Gate results:")
        for gate_result in result.gates:
            if gate_result.status == GateStatus.PASS:
                icon = "[PASS]"
            elif gate_result.status == GateStatus.FAIL:
                icon = "[FAIL]"
            else:
                icon = "[SKIP]"
            print(f"    {icon} {gate_result.message}")

    # Step 6: Summary
    print("\n" + "=" * 50)
    if backtest_results:
        if result.overall_passed:
            print("VALIDATION: PASSED")
            print("  Strategy meets all validation gates")
        else:
            failed = [g for g in result.gates if g.status == GateStatus.FAIL]
            print("VALIDATION: FAILED")
            print(f"  Strategy failed {len(failed)} gate(s)")
    else:
        print("VALIDATION: PENDING")
        print("  No backtest results to validate")

    # Step 7: Save result and update status
    if not dry_run and backtest_results:
        saved_path = validator.save_result(result)
        print(f"\nResult saved to: {saved_path}")

        new_path = validator.update_strategy_status(strategy_id, result.overall_passed)
        if new_path:
            print(f"Strategy moved to: {new_path}")
    elif dry_run:
        print("\n[DRY RUN] Results not saved, status not updated")

    return 0 if result.overall_passed or not backtest_results else 1


def cmd_v4_learn(args):
    """Extract learnings from validation results ."""
    from research_system.validation import V4Learner

    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init' to initialize a workspace.")
        return 1

    process_all = getattr(args, 'process_all', False)
    strategy_id = args.strategy_id

    # Handle --all flag
    if process_all:
        return _cmd_v4_learn_all(workspace, args)

    if not strategy_id:
        print("Error: Strategy ID required")
        print("Usage: research learn STRAT-001")
        print("       research learn --all")
        return 1

    # Load strategy
    strategy = workspace.get_strategy(strategy_id)
    if strategy is None:
        print(f"Error: Strategy '{strategy_id}' not found")
        return 1

    dry_run = getattr(args, 'dry_run', False)

    print(f"\nExtracting learnings for: {strategy_id}")
    print("=" * 50)

    # Initialize learner and load results
    learner = V4Learner(workspace)
    verification_results, validation_results = learner.load_results(strategy_id)

    print(f"\nFound {len(verification_results)} verification result(s)")
    print(f"Found {len(validation_results)} validation result(s)")

    if not verification_results and not validation_results:
        print("\nNo validation results found for this strategy.")
        print("Run 'research verify' and 'research validate' first.")
        return 0

    # Extract learnings
    doc = learner.extract_learnings(strategy, verification_results, validation_results)

    # Display learnings
    print("\n" + "-" * 50)
    print("LEARNINGS")
    print("-" * 50)

    # Group by category
    categories = {}
    for learning in doc.learnings:
        cat = learning.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(learning)

    for category, learnings in categories.items():
        print(f"\n[{category.upper()}]")
        for l in learnings:
            if l.type == "success":
                icon = "+"
            elif l.type == "warning":
                icon = "!"
            elif l.type == "failure":
                icon = "X"
            else:
                icon = "-"

            print(f"  {icon} {l.insight}")
            if l.recommendation:
                print(f"    > Recommendation: {l.recommendation}")

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(doc.summary)

    # Save learnings
    if not dry_run:
        saved_path = learner.save_learnings(doc)
        print(f"\nLearnings saved to: {saved_path}")
    else:
        print("\n[DRY RUN] Learnings not saved")

    return 0


def cmd_v4_ideate(args):
    """Generate new strategy ideas ."""
    from research_system.validation import V4Ideator, V4Learner

    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init' to initialize a workspace.")
        return 1

    dry_run = getattr(args, 'dry_run', False)
    max_ideas = getattr(args, 'max_ideas', 5)

    print("\nGenerating strategy ideas...")
    print("=" * 50)

    # Load existing strategies
    strategies = workspace.list_strategies()
    print(f"\nFound {len(strategies)} existing strategy(ies)")

    # Load learnings
    learner = V4Learner(workspace)
    learnings = []
    learnings_path = workspace.path / "learnings"
    if learnings_path.exists():
        import yaml
        for filepath in learnings_path.glob("*.yaml"):
            with open(filepath) as f:
                doc = yaml.safe_load(f)
                if doc:
                    learnings.append(doc)
    print(f"Found {len(learnings)} learnings document(s)")

    # Generate ideas
    ideator = V4Ideator(workspace)
    ideas = ideator.generate_ideas(
        strategies=strategies,
        learnings=learnings,
        max_ideas=max_ideas,
    )

    if not ideas:
        print("\nNo ideas generated.")
        return 0

    # Display ideas
    print(f"\nGenerated {len(ideas)} idea(s):")
    print("-" * 50)

    for idea in ideas:
        print(f"\n{idea.id}: {idea.name}")
        print(f"  Description: {idea.description}")
        if idea.based_on:
            print(f"  Based on: {idea.based_on}")
        if idea.variation_type:
            print(f"  Type: {idea.variation_type}")
        print(f"  Hypothesis: {idea.hypothesis}")
        print(f"  Suggested changes:")
        for change in idea.suggested_changes[:3]:
            print(f"    - {change}")

    # Save ideas
    if not dry_run:
        saved_paths = ideator.save_ideas(ideas)
        print(f"\n{len(saved_paths)} idea(s) saved to: {workspace.path / 'ideas'}")
    else:
        print("\n[DRY RUN] Ideas not saved")

    return 0


def cmd_v4_run(args):
    """Run full validation pipeline ."""
    from research_system.validation.v4_runner import V4Runner

    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init' to initialize a workspace.")
        return 1

    strategy_id = getattr(args, 'strategy_id', None)
    run_all = getattr(args, 'all', False)
    use_local = getattr(args, 'local', False)
    dry_run = getattr(args, 'dry_run', False)
    force_llm = getattr(args, 'force_llm', False)
    skip_verify = getattr(args, 'skip_verify', False)
    num_windows = getattr(args, 'windows', 1)

    if not strategy_id and not run_all:
        print("Error: Strategy ID required or use --all")
        print("Usage: research run STRAT-001")
        print("       research run --all")
        return 1

    # Initialize LLM client for code generation fallback
    llm_client = None
    try:
        from research_system.llm.client import LLMClient, Backend
        llm_client = LLMClient()
        if llm_client.is_offline:
            print("Note: Running in offline mode. LLM code generation will not be available.")
        elif llm_client.backend == Backend.CLI:
            print("Using Claude CLI backend for code generation.")
        elif llm_client.backend == Backend.API:
            print("Using Anthropic API backend for code generation.")
    except Exception as e:
        print(f"Note: LLM client not available ({e}). Using templates only.")

    # Initialize runner
    runner = V4Runner(
        workspace=workspace,
        llm_client=llm_client,
        use_local=use_local,
        num_windows=num_windows,
    )

    print("\n" + "=" * 60)
    print("  Validation Pipeline")
    print("=" * 60)
    print(f"\nBacktest mode: {'Local Docker' if use_local else 'QC Cloud'}")
    print(f"Walk-forward windows: {num_windows}")
    if dry_run:
        print("[DRY RUN] No backtests will be executed")
    print()

    if run_all:
        results = runner.run_all(dry_run=dry_run, force_llm=force_llm, skip_verify=skip_verify)
        if not results:
            return 0

        # Return non-zero if any failed
        failed_count = sum(1 for r in results if not r.success)
        return 1 if failed_count > 0 else 0
    else:
        result = runner.run(strategy_id, dry_run=dry_run, force_llm=force_llm, skip_verify=skip_verify)

        if not result.success:
            print(f"\nPipeline failed: {result.error}")
            return 1

        print(f"\nPipeline completed: {result.determination}")
        return 0


def cmd_v4_cleanup(args):
    """Clean up stuck QC backtests ."""
    from research_system.validation.backtest import BacktestExecutor

    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init' to initialize a workspace.")
        return 1

    aggressive = getattr(args, 'aggressive', False)
    dry_run = getattr(args, 'dry_run', False)

    print("\n" + "=" * 60)
    print("  QC Backtest Cleanup")
    print("=" * 60)

    # Create executor (with cleanup disabled - we'll do it manually)
    executor = BacktestExecutor(
        workspace_path=workspace.path,
        use_local=False,
        cleanup_on_start=False,
    )

    if dry_run:
        print("\n[DRY RUN] Would clean up backtests")
        # Just check credentials
        creds = executor._get_qc_credentials()
        if not creds:
            print("  Error: No QC credentials found at ~/.lean/credentials")
            return 1
        print("  QC credentials found")
        print(f"  Mode: {'Aggressive (all running)' if aggressive else 'Standard (stuck only)'}")
        return 0

    print()
    if aggressive:
        print("Aggressive cleanup: Cancelling ALL running backtests...")
        cleaned = executor._cleanup_all_running_backtests(min_age_seconds=10)
    else:
        print("Standard cleanup: Cancelling stuck backtests (>5 min old)...")
        cleaned = executor._cleanup_all_stuck_backtests(max_age_seconds=300, max_projects=50)

    if cleaned > 0:
        print(f"\nCleaned up {cleaned} backtest(s)")
        print("Nodes should be available shortly. Wait 10-30 seconds before retrying.")
    else:
        print("\nNo backtests to clean up")
        print("If you're still seeing 'no spare nodes', check the QC dashboard directly.")

    return 0


def cmd_v4_walkforward(args):
    """Run true walk-forward optimization ."""
    from research_system.optimization import (
        WalkForwardConfig,
        WalkForwardRunner,
        format_terminal_summary,
        format_json_output,
        format_parameter_evolution,
    )
    from research_system.validation.backtest import BacktestExecutor
    from research_system.codegen.v4_generator import V4CodeGenerator

    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init' to initialize a workspace.")
        return 1

    strategy_id = args.strategy_id

    # Load strategy
    strategy = workspace.get_strategy(strategy_id)
    if not strategy:
        print(f"Error: Strategy '{strategy_id}' not found")
        return 1

    # Check for tunable parameters
    if not strategy.get("tunable_parameters"):
        print(f"Error: Strategy '{strategy_id}' has no tunable parameters defined")
        print("\nTo use walk-forward optimization, add tunable_parameters to the strategy:")
        print("  tunable_parameters:")
        print("    parameters:")
        print("      period:")
        print("        type: int")
        print("        default: 20")
        print("        min: 10")
        print("        max: 50")
        print("        step: 5")
        return 1

    # Create config from CLI args
    config = WalkForwardConfig(
        start_year=args.start_year,
        end_year=args.end_year,
        initial_train_years=args.train_years,
        test_years=args.test_years,
        max_evaluations=args.max_evals,
    )

    # Get periods preview
    periods = config.get_periods()

    if not args.json:
        print("\n" + "=" * 60)
        print("  Walk-Forward Optimization")
        print("=" * 60)
        print(f"\nStrategy: {strategy_id} - {strategy.get('name', 'Unknown')}")
        print(f"Periods:  {len(periods)}")
        print(f"Config:   {config.start_year}-{config.end_year}, {config.initial_train_years}yr train, {config.test_years}yr test")
        print(f"Max evals: {config.max_evaluations} per period")
        print()

    # Create executor and code generator
    backtest_executor = BacktestExecutor(
        workspace_path=workspace.path,
        use_local=False,
    )
    code_generator = V4CodeGenerator()

    # Create runner
    runner = WalkForwardRunner(
        backtest_executor=backtest_executor,
        code_generator=code_generator,
    )

    # Run walk-forward
    if not args.json:
        print("Running walk-forward optimization...")
        print("(This may take a while - each period runs optimization + OOS test)")
        print()

    result = runner.run(strategy, config)

    # Output results
    if args.json:
        print(format_json_output(result))
    elif args.params:
        print(format_terminal_summary(result))
        print()
        print(format_parameter_evolution(result))
    else:
        print(format_terminal_summary(result))

    return 0 if result.success else 1


def cmd_v4_status(args):
    """Show workspace status dashboard ."""
    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init' to initialize a workspace.")
        return 1

    status = workspace.status()

    # Header
    print()
    print("=" * 60)
    print("  Research-Kit Workspace Status")
    print("=" * 60)

    # Workspace info
    print(f"\nWorkspace: {status['path']}")

    # Strategy counts
    print("\n--- Strategies ---")
    total_strategies = sum(status['strategies'].values())
    if total_strategies == 0:
        print("  No strategies yet")
    else:
        for s, count in sorted(status['strategies'].items()):
            indicator = "*" if count > 0 else " "
            print(f"  {indicator} {s:<12}: {count:>3}")
        print(f"    {'Total':<12}: {total_strategies:>3}")

    # Other counts
    print(f"\n--- Other Items ---")
    print(f"  Ideas:       {status['ideas']:>3}")
    print(f"  Validations: {status['validations']:>3}")

    # Inbox
    print(f"\n--- Inbox ---")
    inbox_count = status['inbox_files']
    if inbox_count == 0:
        print("  Inbox is empty")
    else:
        print(f"  {inbox_count} file(s) ready to ingest")

    # ID counters
    print(f"\n--- Next IDs ---")
    counters = status.get('counters', {})
    next_strat = counters.get('strategy', 0) + 1
    next_idea = counters.get('idea', 0) + 1
    print(f"  Next strategy: STRAT-{next_strat:03d}")
    print(f"  Next idea:     IDEA-{next_idea:03d}")

    # Recent strategies
    recent = workspace.list_strategies()[:5]
    if recent:
        print(f"\n--- Recent Strategies ---")
        for s in recent:
            created = ""
            if s['created']:
                if hasattr(s['created'], 'strftime'):
                    created = s['created'].strftime('%Y-%m-%d')
                else:
                    created = str(s['created'])[:10]
            print(f"  {s['id']:<10} {s['name'][:30]:<30} {s['status']:<12} {created}")

    # Actions / Next steps
    print(f"\n--- Suggested Actions ---")
    actions = []

    if inbox_count > 0:
        actions.append(f"Run 'research ingest' to process {inbox_count} inbox file(s)")

    pending_count = status['strategies'].get('pending', 0)
    if pending_count > 0:
        actions.append(f"Run 'research list --status pending' to see {pending_count} pending strategy(ies)")

    blocked_count = status['strategies'].get('blocked', 0)
    if blocked_count > 0:
        actions.append(f"Check {blocked_count} blocked strategy(ies) for missing data")

    if not actions:
        if total_strategies == 0:
            actions.append("Add research documents to inbox/ and run 'research ingest'")
        else:
            actions.append("All caught up!")

    for action in actions:
        print(f"  > {action}")

    print()
    return 0


def cmd_v4_list(args):
    """List strategies ."""
    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init' to initialize a workspace.")
        return 1

    # Get filter options
    status = getattr(args, 'status', None)
    tags = getattr(args, 'tags', None)
    output_format = getattr(args, 'format', 'table')

    # Parse tags if provided
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(',')]

    # Get strategies
    strategies = workspace.list_strategies(status=status, tags=tag_list)

    if not strategies:
        if status:
            print(f"No strategies with status '{status}'")
        else:
            print("No strategies in workspace")
        return 0

    # Output based on format
    if output_format == 'json':
        import json
        # Convert datetime to string for JSON
        for s in strategies:
            if s['created'] and hasattr(s['created'], 'isoformat'):
                s['created'] = s['created'].isoformat()
        print(json.dumps(strategies, indent=2))
    else:
        # Table format
        print(f"\n{'ID':<12} {'Name':<35} {'Status':<12} {'Created':<20}")
        print("-" * 80)
        for s in strategies:
            name = s['name'][:33] + '..' if len(s['name']) > 35 else s['name']
            created = ''
            if s['created']:
                if hasattr(s['created'], 'strftime'):
                    created = s['created'].strftime('%Y-%m-%d %H:%M')
                else:
                    created = str(s['created'])[:16]
            print(f"{s['id']:<12} {name:<35} {s['status']:<12} {created:<20}")

        print("-" * 80)
        print(f"Total: {len(strategies)} strategies")

        # Show status summary
        status_counts = {}
        for s in strategies:
            st = s['status']
            status_counts[st] = status_counts.get(st, 0) + 1
        summary = ', '.join(f"{k}: {v}" for k, v in sorted(status_counts.items()))
        print(f"By status: {summary}")

    return 0


def cmd_v4_show(args):
    """Show strategy details ."""
    import yaml

    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init' to initialize a workspace.")
        return 1

    strategy_id = args.strategy_id
    output_format = getattr(args, 'format', 'text')

    # Get strategy
    strategy = workspace.get_strategy(strategy_id)

    if strategy is None:
        print(f"Error: Strategy '{strategy_id}' not found")
        print(f"Searched in: {workspace.strategies_path}")
        return 1

    # Output based on format
    if output_format == 'yaml':
        # Remove internal fields
        strategy.pop('_file', None)
        strategy.pop('_status', None)
        print(yaml.dump(strategy, default_flow_style=False, sort_keys=False))
    elif output_format == 'json':
        import json
        # Remove internal fields
        strategy.pop('_file', None)
        status = strategy.pop('_status', None)
        # Convert datetime to string
        if 'created' in strategy and hasattr(strategy['created'], 'isoformat'):
            strategy['created'] = strategy['created'].isoformat()
        print(json.dumps(strategy, indent=2))
    else:
        # Human-readable text format
        _print_strategy_details(strategy)

    return 0


def _print_strategy_details(strategy: dict) -> None:
    """Print strategy in human-readable format."""
    status = strategy.get('_status', 'unknown')
    filepath = strategy.get('_file', '')

    # Header
    print("\n" + "=" * 60)
    print(f"Strategy: {strategy.get('id', 'Unknown')}")
    print("=" * 60)

    # Basic info
    print(f"\nName:    {strategy.get('name', 'Unnamed')}")
    print(f"Status:  {status}")
    if strategy.get('created'):
        created = strategy['created']
        if hasattr(created, 'strftime'):
            created = created.strftime('%Y-%m-%d %H:%M:%S')
        print(f"Created: {created}")

    # Source (supports both simple and V4 schema formats)
    source = strategy.get('source', {})
    if source:
        print(f"\n--- Source ---")
        # Simple format: source.type, source.author
        if source.get('type'):
            print(f"Type:      {source['type']}")
        if source.get('author'):
            print(f"Author:    {source['author']}")
        # V4 format: source.reference, source.credibility
        if source.get('reference'):
            print(f"Reference: {source['reference']}")
        if source.get('url'):
            print(f"URL:       {source['url']}")
        if source.get('track_record'):
            print(f"Track Record: {source['track_record']}")
        # V4 credibility info (nested)
        cred = source.get('credibility', {})
        if cred:
            if cred.get('type') and not source.get('type'):
                print(f"Type:      {cred['type']}")
            if cred.get('author') and not source.get('author'):
                print(f"Author:    {cred['author']}")
            if cred.get('track_record') and not source.get('track_record'):
                print(f"Track Record: {cred['track_record']}")
        # Show excerpt if available
        if source.get('excerpt'):
            excerpt = source['excerpt']
            if len(excerpt) > 200:
                excerpt = excerpt[:200] + "..."
            print(f"Excerpt:   {excerpt}")

    # Hypothesis (supports both simple and V4 schema formats)
    hypothesis = strategy.get('hypothesis', {})
    if hypothesis:
        print(f"\n--- Hypothesis ---")
        # Simple format: thesis, type, testable_prediction
        if hypothesis.get('thesis'):
            print(f"Thesis: {hypothesis['thesis']}")
        if hypothesis.get('type'):
            print(f"Type:   {hypothesis['type']}")
        if hypothesis.get('testable_prediction'):
            print(f"Testable: {hypothesis['testable_prediction']}")
        if hypothesis.get('expected_sharpe'):
            exp = hypothesis['expected_sharpe']
            if isinstance(exp, dict):
                print(f"Expected Sharpe: {exp.get('min', '?')} - {exp.get('max', '?')}")
            else:
                print(f"Expected Sharpe: {exp}")
        # V4 format: summary, detail
        if hypothesis.get('summary') and not hypothesis.get('thesis'):
            print(f"Summary: {hypothesis['summary']}")
        if hypothesis.get('detail'):
            detail = hypothesis['detail']
            if len(detail) > 300:
                detail = detail[:300] + "..."
            print(f"Detail:  {detail}")

    # Edge (can be top-level or nested under hypothesis)
    edge = hypothesis.get('edge', {}) or strategy.get('edge', {})
    if edge:
        print(f"\n--- Edge ---")
        if edge.get('mechanism'):
            print(f"Mechanism:    {edge['mechanism']}")
        if edge.get('category'):
            print(f"Category:     {edge['category']}")
        if edge.get('why_exists'):
            print(f"Why Exists:   {edge['why_exists']}")
        if edge.get('counterparty'):
            print(f"Counterparty: {edge['counterparty']}")
        if edge.get('why_persists'):
            print(f"Why Persists: {edge['why_persists']}")

    # Universe
    universe = strategy.get('universe', {})
    if universe:
        print(f"\n--- Universe ---")
        if universe.get('type'):
            print(f"Type: {universe['type']}")
        if universe.get('symbols'):
            symbols = universe['symbols']
            if isinstance(symbols, list):
                if len(symbols) <= 5:
                    print(f"Symbols: {', '.join(symbols)}")
                else:
                    print(f"Symbols: {', '.join(symbols[:5])} ... (+{len(symbols)-5} more)")

    # Entry (supports both simple and V4 schema formats)
    entry = strategy.get('entry', {})
    if entry:
        print(f"\n--- Entry ---")
        if entry.get('type'):
            print(f"Type: {entry['type']}")
        # Simple format: signals array
        signals = entry.get('signals', [])
        for i, sig in enumerate(signals[:3], 1):
            if isinstance(sig, dict):
                print(f"Signal {i}: {sig.get('name', 'unnamed')} - {sig.get('condition', '')}")
        if len(signals) > 3:
            print(f"  ... and {len(signals)-3} more signals")
        # V4 format: technical config
        tech = entry.get('technical', {})
        if tech and not signals:
            if tech.get('indicator'):
                print(f"Indicator: {tech['indicator']}")
            if tech.get('condition'):
                print(f"Condition: {tech['condition']}")
        # Fundamental config
        fund = entry.get('fundamental', {})
        if fund:
            if fund.get('metric'):
                print(f"Metric: {fund['metric']}")

    # Position (V4 schema)
    position = strategy.get('position', {})
    if position:
        print(f"\n--- Position ---")
        if position.get('type'):
            print(f"Type: {position['type']}")
        legs = position.get('legs', [])
        for leg in legs[:3]:
            if isinstance(leg, dict):
                name = leg.get('name', 'unnamed')
                direction = leg.get('direction', '')
                asset_type = leg.get('asset_type', '')
                print(f"  - {name}: {direction} {asset_type}")
        sizing = position.get('sizing', {})
        if sizing and sizing.get('method'):
            print(f"Sizing: {sizing['method']}")

    # Exit (V4 schema: paths, priority)
    exit_info = strategy.get('exit', {})
    if exit_info:
        print(f"\n--- Exit ---")
        if exit_info.get('priority'):
            print(f"Priority: {exit_info['priority']}")
        paths = exit_info.get('paths', [])
        for path in paths[:3]:
            if isinstance(path, dict):
                name = path.get('name', 'unnamed')
                exit_type = path.get('type', '')
                condition = path.get('condition_description', path.get('condition', ''))
                print(f"  - {name} ({exit_type}): {condition}")

    # Data requirements
    data_reqs = strategy.get('data_requirements', {})
    if data_reqs:
        print(f"\n--- Data Requirements ---")
        primary = data_reqs.get('primary', [])
        if primary:
            print(f"Primary: {', '.join(str(d) for d in primary[:5])}")
        derived = data_reqs.get('derived', [])
        if derived:
            print(f"Derived: {', '.join(str(d) for d in derived[:5])}")

    # Tags
    tags = strategy.get('tags', {})
    if tags:
        print(f"\n--- Tags ---")
        if isinstance(tags, dict) and tags.get('custom'):
            print(f"Custom: {', '.join(tags['custom'])}")
        elif isinstance(tags, list):
            print(f"Tags: {', '.join(tags)}")

    # File location
    print(f"\n--- Location ---")
    print(f"File: {filepath}")
    print()


def cmd_v4_config(args):
    """Show/validate V4 configuration."""
    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init' to initialize a workspace.")
        return 1

    config = workspace.config

    if args.validate:
        print("Validating configuration...")
        errors = validate_config(config)
        if errors:
            print()
            print("Configuration warnings:")
            for err in errors:
                print(f"  - {err}")
            return 1
        else:
            print("Configuration is valid.")
            return 0

    # Show configuration
    print("Configuration:")
    print(f"  Version: {config.version}")
    print()
    print("Gates (validation thresholds):")
    print(f"  min_sharpe: {config.gates.min_sharpe}")
    print(f"  min_consistency: {config.gates.min_consistency}")
    print(f"  max_drawdown: {config.gates.max_drawdown}")
    print(f"  min_trades: {config.gates.min_trades}")
    print()
    print("Ingestion (quality thresholds):")
    print(f"  min_specificity_score: {config.ingestion.min_specificity_score}")
    print(f"  min_trust_score: {config.ingestion.min_trust_score}")
    print()
    print("Verification:")
    print(f"  enabled: {config.verification.enabled}")
    print(f"  tests: {', '.join(config.verification.tests)}")
    print()
    print(f"Configuration file: {workspace.path / 'research-kit.yaml'}")
    return 0


def cmd_ingest_list(args):
    """List inbox files."""
    ws = require_workspace(args.workspace)
    inbox = ws.inbox_path

    files = [f for f in inbox.rglob("*") if f.is_file()]
    if not files:
        print("Inbox is empty")
        return 0

    print(f"Files in inbox ({len(files)}):")
    for f in sorted(files):
        rel_path = f.relative_to(inbox)
        size = f.stat().st_size
        print(f"  {str(rel_path):<40} {size:>10,} bytes")
    return 0


def cmd_ingest_add(args):
    """Add file to inbox."""
    ws = require_workspace(args.workspace)
    source = Path(args.file)

    if not source.exists():
        print(f"Error: File not found: {source}")
        return 1

    import shutil
    dest = ws.inbox_path / source.name
    shutil.copy2(source, dest)
    print(f"Added {source.name} to inbox")
    return 0


def cmd_ingest_process(args):
    """Process inbox files."""
    ws = require_workspace(args.workspace)

    # Initialize LLM client
    llm_client = None
    try:
        from research_system.llm.client import LLMClient, Backend
        llm_client = LLMClient()
        if llm_client.is_offline:
            print("Note: Running in offline mode (no ANTHROPIC_API_KEY or claude CLI). Extraction will be limited.")
        elif llm_client.backend == Backend.CLI:
            print("Using Claude CLI backend.")
        elif llm_client.backend == Backend.API:
            print("Using Anthropic API backend.")
    except Exception as e:
        print(f"Warning: Could not initialize LLM client: {e}")
        print("Running in offline mode.")

    from research_system.ingest.processor import IngestProcessor

    processor = IngestProcessor(ws, llm_client)

    if args.file:
        # Process specific file
        file_path = ws.inbox_path / args.file
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            return 1

        print(f"Processing: {args.file}")
        result = processor.process_file(file_path, dry_run=args.dry_run)

        if result.success:
            status_info = f" (BLOCKED: {', '.join(result.blocked_data)})" if result.blocked_data else ""
            print(f"  -> {result.entry_id}: {result.entry_type}{status_info}")
        elif result.skipped_reason:
            print(f"  -> SKIPPED: {result.skipped_reason}")
        else:
            print(f"  -> ERROR: {result.error}")

        return 0 if result.success else 1

    else:
        # Process all files (recursive)
        inbox_files = list(ws.inbox_path.rglob("*"))
        inbox_files = [f for f in inbox_files if f.is_file() and not f.name.startswith(".")]

        if not inbox_files:
            print("Inbox is empty")
            return 0

        mode = "[DRY-RUN] " if args.dry_run else ""
        print(f"{mode}Processing inbox ({len(inbox_files)} files)...")
        print()

        summary = processor.process_all(dry_run=args.dry_run)

        for i, result in enumerate(summary.results, 1):
            # Show relative path if different from filename (i.e., file is in subdirectory)
            display_name = result.relative_path if result.relative_path else result.filename
            if result.success:
                status_info = f" ({result.status})"
                if result.blocked_data:
                    status_info = f" (BLOCKED: {', '.join(result.blocked_data)})"
                print(f"  [{i}/{summary.total_files}] {display_name}")
                print(f"      -> {result.entry_id}{status_info}")
            elif result.skipped_reason:
                print(f"  [{i}/{summary.total_files}] {display_name}")
                print(f"      -> SKIPPED: {result.skipped_reason}")
            else:
                print(f"  [{i}/{summary.total_files}] {display_name}")
                print(f"      -> ERROR: {result.error}")

        print()
        print(f"Complete: {summary.processed} entries created, {summary.skipped} skipped, {summary.duplicates} duplicates, {summary.errors} errors")
        if summary.blocked > 0:
            print(f"  ({summary.blocked} entries BLOCKED due to missing data)")

        return 0


def cmd_catalog_list(args):
    """List catalog entries."""
    ws = require_workspace(args.workspace)
    catalog = Catalog(ws.catalog_path)

    # Build query
    query = catalog.query()
    if args.type:
        query = query.by_type(args.type)
    if args.status:
        query = query.by_status(args.status)

    entries = query.execute()

    if not entries:
        print("No matching entries")
        return 0

    if args.format == "json":
        print(json.dumps(entries, indent=2))
    elif args.format == "ids":
        for e in entries:
            print(e["id"])
    else:  # table
        print(f"{'ID':<12} {'Type':<12} {'Status':<12} {'Name'}")
        print("-" * 60)
        for e in entries:
            print(f"{e['id']:<12} {e['type']:<12} {e['status']:<12} {e['name']}")
        print()
        print(f"Total: {len(entries)} entries")

    return 0


def cmd_catalog_show(args):
    """Show entry details."""
    ws = require_workspace(args.workspace)
    catalog = Catalog(ws.catalog_path)

    entry = catalog.get(args.id)
    if not entry:
        print(f"Entry not found: {args.id}")
        return 1

    print(json.dumps(entry.to_dict(), indent=2))
    return 0


def cmd_catalog_add(args):
    """Add a new catalog entry."""
    ws = require_workspace(args.workspace)
    catalog = Catalog(ws.catalog_path)

    try:
        entry = catalog.add(
            entry_type=args.type,
            name=args.name,
            source_files=args.source,
            summary=args.summary,
            hypothesis=args.hypothesis,
            tags=args.tags
        )
        print(f"Created entry: {entry.id}")
        print(json.dumps(entry.to_dict(), indent=2))
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1


def cmd_catalog_stats(args):
    """Show catalog statistics."""
    ws = require_workspace(args.workspace)
    catalog = Catalog(ws.catalog_path)

    stats = catalog.stats()

    print(f"Catalog Statistics")
    print(f"=" * 40)
    print(f"Total entries: {stats.total_entries}")
    print(f"Generated at: {stats.generated_at}")
    print()
    print("By type:")
    for t, count in sorted(stats.by_type.items()):
        print(f"  {t}: {count}")
    print()
    print("By status:")
    for s, count in sorted(stats.by_status.items()):
        print(f"  {s}: {count}")

    return 0


def cmd_catalog_search(args):
    """Search catalog entries."""
    ws = require_workspace(args.workspace)
    catalog = Catalog(ws.catalog_path)

    results = catalog.search(args.query)

    if not results:
        print("No matching entries")
        return 0

    print(f"{'ID':<12} {'Type':<12} {'Status':<12} {'Name'}")
    print("-" * 60)
    for e in results:
        print(f"{e['id']:<12} {e['type']:<12} {e['status']:<12} {e['name']}")
    print()
    print(f"Found: {len(results)} entries")

    return 0


def cmd_data_list(args):
    """List data sources."""
    ws = require_workspace(args.workspace)
    registry = DataRegistry(ws.data_registry_path)

    sources = registry.list(available_only=args.available if hasattr(args, 'available') else False)

    if not sources:
        print("No data sources configured")
        return 0

    print(f"{'ID':<25} {'Name':<30} {'Available'}")
    print("-" * 70)
    for source in sources:
        available = "Yes" if source.is_available() else "No"
        print(f"{source.id:<25} {source.name[:29]:<30} {available}")

    print()
    print(f"Total: {len(sources)} data sources")
    return 0


def cmd_data_show(args):
    """Show data source details."""
    ws = require_workspace(args.workspace)
    registry = DataRegistry(ws.data_registry_path)

    source = registry.get(args.id)
    if not source:
        print(f"Data source not found: {args.id}")
        return 1

    print(json.dumps(source.to_dict(), indent=2))

    # Show best source
    best = source.best_source()
    print()
    if best.available:
        print(f"Best available source: {best.source_tier}")
        if best.path:
            print(f"  Path: {best.path}")
        if best.key:
            print(f"  Key: {best.key}")
    else:
        print("No available sources")

    return 0


def cmd_data_check(args):
    """Check data availability."""
    ws = require_workspace(args.workspace)
    registry = DataRegistry(ws.data_registry_path)

    results = registry.check_availability(args.ids)

    print(f"{'Data Source':<25} {'Available':<10} {'Source'}")
    print("-" * 60)

    all_available = True
    for source_id, availability in results.items():
        if availability.available:
            status = "Yes"
            source = availability.source_tier or "unknown"
        else:
            status = "No"
            source = availability.notes or "not found"
            all_available = False
        print(f"{source_id:<25} {status:<10} {source}")

    print()
    if all_available:
        print("All data sources available")
    else:
        print("Some data sources unavailable")
        return 1

    return 0


def cmd_data_add(args):
    """Add a data source."""
    ws = require_workspace(args.workspace)
    registry = DataRegistry(ws.data_registry_path)

    try:
        source = registry.add(
            source_id=args.id,
            name=args.name,
            data_type=args.type
        )
        print(f"Added data source: {source.id}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1


def cmd_validate_start(args):
    """Start validation for an entry."""
    ws = require_workspace(args.workspace)
    catalog = Catalog(ws.catalog_path)

    # Verify entry exists
    entry = catalog.get(args.id)
    if not entry:
        print(f"Error: Entry not found: {args.id}")
        return 1

    # Check if entry is blocked
    if entry.status == "BLOCKED":
        print(f"Error: Entry {args.id} is BLOCKED. Resolve data requirements first.")
        print(f"Use 'research validate check {args.id}' to re-check data availability.")
        return 1

    # Import and initialize orchestrator
    from scripts.validate.orchestrator import ValidationOrchestrator

    val_dir = ws.validations_path / args.id
    orchestrator = ValidationOrchestrator(args.id, validation_dir=val_dir)

    if orchestrator.start():
        print(f"Validation started for {args.id}")
        print(f"Current state: {orchestrator.current_state.value}")
        print()
        print("Next step:")
        print(f"  research validate hypothesis {args.id} --file hypothesis.json")

        # Update catalog status
        catalog.update_status(args.id, "IN_PROGRESS", validation_ref=str(val_dir))
    else:
        print(f"Validation already in progress for {args.id}")
        print(f"Current state: {orchestrator.current_state.value}")

    return 0


def cmd_validate_status(args):
    """Check validation status."""
    ws = require_workspace(args.workspace)
    val_dir = ws.validation_path(args.id)
    metadata_file = val_dir / "metadata.json"

    if not metadata_file.exists():
        print(f"No validation found for {args.id}")
        return 1

    import json
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)

    print(f"Validation Status: {args.id}")
    print(f"=" * 40)
    print(f"Current state: {metadata.get('current_state', 'unknown')}")
    print(f"Created: {metadata.get('created_at', 'unknown')}")
    print(f"Updated: {metadata.get('updated_at', 'unknown')}")

    if metadata.get("determination"):
        print(f"Determination: {metadata['determination']}")

    return 0


def cmd_validate_audit(args):
    """Run data audit."""
    ws = require_workspace(args.workspace)

    from scripts.validate.orchestrator import ValidationOrchestrator, ValidationState, ValidationGateError

    val_dir = ws.validations_path / args.id
    if not val_dir.exists():
        print(f"Error: No validation found for {args.id}")
        print(f"Start validation with: research validate start {args.id}")
        return 1

    orchestrator = ValidationOrchestrator(args.id, validation_dir=val_dir)

    if orchestrator.current_state != ValidationState.HYPOTHESIS:
        print(f"Error: Cannot run audit from state: {orchestrator.current_state.value}")
        print("Data audit runs after hypothesis is submitted.")
        return 1

    print(f"Running data audit for {args.id}...")

    try:
        orchestrator.run_data_audit()
        print("Data audit: PASSED")
        print()
        print("Next step:")
        print(f"  Submit IS backtest results with: research validate submit-is {args.id} --file results.json")
        return 0
    except ValidationGateError as e:
        print(f"Data audit: FAILED")
        print(f"  {e}")
        return 1


def cmd_validate_run(args):
    """Run next validation step."""
    ws = require_workspace(args.workspace)

    from scripts.validate.orchestrator import ValidationOrchestrator, ValidationState, ValidationGateError

    val_dir = ws.validations_path / args.id
    if not val_dir.exists():
        print(f"Error: No validation found for {args.id}")
        print(f"Start validation with: research validate start {args.id}")
        return 1

    orchestrator = ValidationOrchestrator(args.id, validation_dir=val_dir)
    state = orchestrator.current_state

    print(f"Current state: {state.value}")
    print()

    try:
        if state == ValidationState.INITIALIZED:
            print("Validation not started. Use:")
            print(f"  research validate start {args.id}")

        elif state == ValidationState.HYPOTHESIS:
            print("Hypothesis stage. Submit hypothesis with:")
            print(f"  research validate hypothesis {args.id} --file hypothesis.json")

        elif state == ValidationState.DATA_AUDIT:
            print("Error: Submit IS results first:")
            print(f"  research validate submit-is {args.id} --file results.json")

        elif state == ValidationState.IS_TESTING:
            print("Running statistical analysis...")
            orchestrator.run_statistical_analysis()
            print("Statistical analysis: PASSED")
            print()
            print("Next: Regime analysis will run automatically.")
            # Run regime analysis
            orchestrator.run_regime_analysis()
            print("Regime analysis: COMPLETE")
            print()
            print("Next step (ONE SHOT - no retries!):")
            print(f"  research validate submit-oos {args.id} --file results.json --confirm")

        elif state == ValidationState.STATISTICAL:
            print("Running regime analysis...")
            orchestrator.run_regime_analysis()
            print("Regime analysis: COMPLETE")
            print()
            print("Next step (ONE SHOT - no retries!):")
            print(f"  research validate submit-oos {args.id} --file results.json --confirm")

        elif state == ValidationState.REGIME:
            print("Ready for OOS testing (ONE SHOT - no retries!):")
            print(f"  research validate submit-oos {args.id} --file results.json --confirm")

        elif state == ValidationState.OOS_TESTING:
            print("Making final determination...")
            result = orchestrator.make_determination()
            print()
            print(f"DETERMINATION: {result.value}")
            print(f"Reason: {orchestrator.metadata.determination_reason}")

            # Update catalog
            catalog = Catalog(ws.catalog_path)
            catalog.update_status(args.id, result.value)

        elif state == ValidationState.COMPLETED:
            print(f"Validation complete: {orchestrator.metadata.determination}")

        elif state == ValidationState.FAILED:
            print("Validation failed. Review results and consider:")
            print("  - Revising the hypothesis")
            print("  - Starting a new validation with different parameters")

        elif state == ValidationState.BLOCKED:
            print("Validation blocked. Check data availability:")
            print(f"  research validate check {args.id}")

        return 0

    except ValidationGateError as e:
        print(f"Validation gate failed: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_validate_list(args):
    """List validations."""
    ws = require_workspace(args.workspace)

    if not ws.validations_path.exists():
        print("No validations")
        return 0

    validations = [d for d in ws.validations_path.iterdir() if d.is_dir()]

    if not validations:
        print("No validations")
        return 0

    print(f"{'ID':<15} {'State':<15} {'Determination'}")
    print("-" * 50)

    for val_dir in sorted(validations):
        metadata_file = val_dir / "metadata.json"
        if metadata_file.exists():
            import json
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            state = metadata.get("current_state", "unknown")
            determination = metadata.get("determination", "-")
        else:
            state = "unknown"
            determination = "-"

        print(f"{val_dir.name:<15} {state:<15} {determination}")

    return 0


def cmd_validate_hypothesis(args):
    """Submit hypothesis for validation."""
    ws = require_workspace(args.workspace)

    from scripts.validate.orchestrator import ValidationOrchestrator, ValidationState, ValidationGateError

    # Load hypothesis file
    hypothesis_file = Path(args.file)
    if not hypothesis_file.exists():
        print(f"Error: File not found: {hypothesis_file}")
        return 1

    try:
        with open(hypothesis_file, 'r') as f:
            hypothesis = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {hypothesis_file}: {e}")
        return 1

    val_dir = ws.validations_path / args.id
    if not val_dir.exists():
        print(f"Error: No validation found for {args.id}")
        print(f"Start validation with: research validate start {args.id}")
        return 1

    orchestrator = ValidationOrchestrator(args.id, validation_dir=val_dir)

    try:
        orchestrator.submit_hypothesis(hypothesis)
        print(f"Hypothesis submitted for {args.id}")
        print("Parameters are now LOCKED.")
        print()
        print("Next step:")
        print(f"  research validate audit {args.id}")
        return 0
    except ValidationGateError as e:
        print(f"Error: {e}")
        return 1


def cmd_validate_submit_is(args):
    """Submit in-sample backtest results."""
    ws = require_workspace(args.workspace)

    from scripts.validate.orchestrator import ValidationOrchestrator, ValidationState, ValidationGateError

    # Load results file
    results_file = Path(args.file)
    if not results_file.exists():
        print(f"Error: File not found: {results_file}")
        return 1

    try:
        with open(results_file, 'r') as f:
            results = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {results_file}: {e}")
        return 1

    # Load baseline if provided
    baseline = None
    if args.baseline:
        baseline_file = Path(args.baseline)
        if not baseline_file.exists():
            print(f"Error: Baseline file not found: {baseline_file}")
            return 1
        try:
            with open(baseline_file, 'r') as f:
                baseline = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {baseline_file}: {e}")
            return 1

    val_dir = ws.validations_path / args.id
    if not val_dir.exists():
        print(f"Error: No validation found for {args.id}")
        return 1

    orchestrator = ValidationOrchestrator(args.id, validation_dir=val_dir)

    if orchestrator.current_state != ValidationState.DATA_AUDIT:
        print(f"Error: Cannot submit IS results from state: {orchestrator.current_state.value}")
        return 1

    print(f"Submitting IS results for {args.id}...")

    if orchestrator.submit_is_results(results, baseline):
        print("IS testing: PASSED")
        alpha = results.get("alpha", 0) or results.get("annual_alpha", 0)
        sharpe = results.get("sharpe_ratio", 0) or results.get("sharpe", 0)
        print(f"  Alpha: {alpha:.2%}, Sharpe: {sharpe:.2f}")
        print()
        print("Next step:")
        print(f"  research validate run {args.id}")
        return 0
    else:
        print("IS testing: FAILED (did not meet minimum thresholds)")
        return 1


def cmd_validate_submit_oos(args):
    """Submit out-of-sample results (ONE SHOT)."""
    ws = require_workspace(args.workspace)

    from scripts.validate.orchestrator import ValidationOrchestrator, ValidationState, ValidationGateError

    if not args.confirm:
        print("WARNING: OOS testing is ONE SHOT - no retries allowed!")
        print()
        print("This is your only chance to submit OOS results.")
        print("Once submitted, the determination will be made and cannot be changed.")
        print()
        print("To confirm, add --confirm flag:")
        print(f"  research validate submit-oos {args.id} --file {args.file} --confirm")
        return 1

    # Load results file
    results_file = Path(args.file)
    if not results_file.exists():
        print(f"Error: File not found: {results_file}")
        return 1

    try:
        with open(results_file, 'r') as f:
            results = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {results_file}: {e}")
        return 1

    val_dir = ws.validations_path / args.id
    if not val_dir.exists():
        print(f"Error: No validation found for {args.id}")
        return 1

    orchestrator = ValidationOrchestrator(args.id, validation_dir=val_dir)

    if orchestrator.current_state != ValidationState.REGIME:
        print(f"Error: Cannot submit OOS results from state: {orchestrator.current_state.value}")
        return 1

    print(f"Submitting OOS results for {args.id}...")
    print("(ONE SHOT - no retries)")
    print()

    try:
        orchestrator.submit_oos_results(results)
        print("OOS results submitted.")
        print()
        print("Making final determination...")
        result = orchestrator.make_determination()
        print()
        print(f"DETERMINATION: {result.value}")
        print(f"Reason: {orchestrator.metadata.determination_reason}")

        # Update catalog
        catalog = Catalog(ws.catalog_path)
        catalog.update_status(args.id, result.value)

        return 0
    except ValidationGateError as e:
        print(f"Error: {e}")
        return 1


def cmd_validate_check(args):
    """Re-check blocked entry for data availability."""
    ws = require_workspace(args.workspace)
    catalog = Catalog(ws.catalog_path)
    registry = DataRegistry(ws.data_registry_path)

    entry = catalog.get(args.id)
    if not entry:
        print(f"Error: Entry not found: {args.id}")
        return 1

    if entry.status != "BLOCKED":
        print(f"Entry {args.id} is not BLOCKED (status: {entry.status})")
        return 0

    # Get data requirements from entry
    data_reqs = entry.data.get("data_requirements", [])

    if not data_reqs:
        print(f"No data requirements found for {args.id}")
        print("Updating status to UNTESTED...")
        catalog.update_status(args.id, "UNTESTED")
        return 0

    print(f"Checking data requirements for {args.id}...")
    print()

    missing = []
    for req in data_reqs:
        # registry.get() now handles both explicit entries and QC Native patterns
        source = registry.get(req)
        if source is not None and source.is_available():
            tier = source.best_source().source_tier
            auto = " (auto-recognized)" if source.is_auto_recognized else ""
            print(f"  {req}: available ({tier}){auto}")
        else:
            missing.append(req)
            print(f"  {req}: NOT AVAILABLE")

    print()

    if missing:
        print(f"Still missing: {', '.join(missing)}")
        print("Entry remains BLOCKED.")
        return 1
    else:
        print("All data requirements satisfied!")
        print("Updating status: BLOCKED -> UNTESTED")
        catalog.update_status(args.id, "UNTESTED")
        return 0


def cmd_status(args):
    """View dashboard and reports."""
    import subprocess
    from scripts.status.generate_reports import (
        scan_strategies,
        refresh_all_reports,
    )

    ws = require_workspace(args.workspace)

    # Refresh reports if requested
    if args.refresh:
        print("Refreshing all reports...")
        files = refresh_all_reports(ws.path)
        print()
        print("Generated reports:")
        for name, path in files.items():
            print(f"  {name}: {path}")
        print()
        print(f"Dashboard: {ws.path / 'reports' / 'dashboard.md'}")
        return 0

    # Open dashboard if requested
    if args.open:
        dashboard = ws.path / "reports" / "dashboard.md"
        if not dashboard.exists():
            print("Dashboard not found. Run 'research status --refresh' first.")
            return 1
        # Use 'open' on macOS, 'xdg-open' on Linux
        import platform
        if platform.system() == "Darwin":
            subprocess.run(["open", str(dashboard)])
        else:
            subprocess.run(["xdg-open", str(dashboard)])
        print(f"Opened: {dashboard}")
        return 0

    # Show quick terminal summary or specific report
    strategies = scan_strategies(ws.path)

    if not strategies:
        print("No strategies found.")
        print("Run some validations first, then use 'research status --refresh'.")
        return 0

    validated = [s for s in strategies if s["status"] == "VALIDATED"]
    invalidated = [s for s in strategies if s["status"] == "INVALIDATED"]
    pending = [s for s in strategies if s["status"] not in ["VALIDATED", "INVALIDATED"]]

    if args.report == "leaderboard":
        # Show full leaderboard
        print("=" * 70)
        print("STRATEGY LEADERBOARD")
        print("=" * 70)
        print()

        if not validated:
            print("No validated strategies yet.")
            return 0

        # Sort
        sort_key = {
            "sharpe": lambda x: x.get("sharpe") or 0,
            "return": lambda x: x.get("median_return") or 0,
            "consistency": lambda x: x.get("consistency") or 0,
            "drawdown": lambda x: -(x.get("max_drawdown") or 1),
        }.get(args.sort, lambda x: x.get("sharpe") or 0)

        sorted_strats = sorted(validated, key=sort_key, reverse=True)

        print(f"{'Rank':<5} {'Entry':<12} {'Type':<18} {'Sharpe':>8} {'Return':>10} {'Cons':>8} {'MaxDD':>8}")
        print("-" * 70)

        for i, s in enumerate(sorted_strats[:args.top], 1):
            sharpe = f"{s.get('sharpe', 0):.2f}" if s.get('sharpe') else "-"
            ret = f"{s.get('median_return', 0)*100:.1f}%" if s.get('median_return') else "-"
            cons = f"{s.get('consistency', 0)*100:.0f}%" if s.get('consistency') else "-"
            dd = f"{s.get('max_drawdown', 0)*100:.1f}%" if s.get('max_drawdown') else "-"
            print(f"{i:<5} {s['entry_id']:<12} {s['strategy_type']:<18} {sharpe:>8} {ret:>10} {cons:>8} {dd:>8}")

        print()
        print(f"Showing top {min(args.top, len(sorted_strats))} of {len(validated)} validated strategies")
        print("Run 'research status --refresh' to generate full markdown reports.")
        return 0

    # Default: quick summary
    print("=" * 50)
    print("RESEARCH KIT STATUS")
    print("=" * 50)
    print()
    print(f"Total Strategies:  {len(strategies)}")
    print(f"  Validated:       {len(validated)} ({len(validated)*100//len(strategies) if strategies else 0}%)")
    print(f"  Invalidated:     {len(invalidated)} ({len(invalidated)*100//len(strategies) if strategies else 0}%)")
    print(f"  Pending:         {len(pending)}")
    print()

    if validated:
        print("Top 5 by Sharpe:")
        sorted_by_sharpe = sorted(validated, key=lambda x: x.get("sharpe") or 0, reverse=True)
        for i, s in enumerate(sorted_by_sharpe[:5], 1):
            sharpe = f"{s.get('sharpe', 0):.2f}" if s.get('sharpe') else "?"
            print(f"  {i}. {s['entry_id']} ({s['strategy_type']}): Sharpe {sharpe}")
        print()

    reports_dir = ws.path / "reports"
    if (reports_dir / "dashboard.md").exists():
        print(f"Reports: {reports_dir}/dashboard.md")
    else:
        print("Run 'research status --refresh' to generate full reports.")

    return 0


def cmd_develop(args):
    """Develop ideas through 10-step framework."""
    from scripts.develop.classifier import classify_idea, MaturityLevel
    from scripts.develop.workflow import (
        DevelopmentWorkflow, DevelopmentStep, STEP_DEFINITIONS, STEP_ORDER
    )

    ws = require_workspace(args.workspace)
    catalog = Catalog(ws.catalog_path)

    # Get the entry
    entry = catalog.get(args.id)
    if not entry:
        print(f"Error: Entry not found: {args.id}")
        return 1

    # Get the idea text
    idea_text = entry.hypothesis or entry.summary or ""
    if not idea_text:
        print(f"Error: Entry has no hypothesis or summary to develop")
        return 1

    # Initialize LLM client
    llm_client = None
    try:
        from research_system.llm.client import LLMClient
        llm_client = LLMClient()
    except Exception:
        pass

    # Classify-only mode
    if args.classify:
        print(f"Classifying: {args.id}")
        print(f"Idea: {idea_text[:200]}...")
        print()

        maturity = classify_idea(idea_text, llm_client)

        print(f"Maturity Level: {maturity.level.value.upper()}")
        print(f"Score: {maturity.score:.0%}")
        print()

        if maturity.missing:
            print("Missing elements:")
            for m in maturity.missing:
                print(f"  - {m}")
            print()

        if maturity.steps_needed:
            print("Development steps needed:")
            for s in maturity.steps_needed:
                print(f"  - {s}")

        return 0

    # Initialize workflow
    workflow = DevelopmentWorkflow(ws.path, llm_client)

    # Load or start development
    state = workflow.load(args.id)
    if not state:
        # Check maturity first
        maturity = classify_idea(idea_text, llm_client)
        if maturity.level == MaturityLevel.FULL:
            print(f"Note: {args.id} appears to be fully specified (maturity: FULL)")
            print("You can run validation directly with: research run {args.id} --walk-forward")
            print()
            print("Start development anyway? This will help document the strategy formally.")
            response = input("Continue? [y/N]: ").strip().lower()
            if response != 'y':
                return 0

        state = workflow.start(args.id, idea_text)
        print(f"Started development for {args.id}")
        print()

    # Status-only mode
    if args.status:
        _show_development_status(state)
        return 0

    # Go back mode
    if args.back:
        if state.current_step == STEP_ORDER[0]:
            print("Already at first step.")
            return 0

        current_idx = STEP_ORDER.index(state.current_step)
        prev_step = STEP_ORDER[current_idx - 1]
        state = workflow.go_back(state, prev_step)
        print(f"Went back to: {prev_step.value}")
        print()

    # Complete mode
    if args.complete:
        if not state.is_complete:
            print(f"Development not complete. Current step: {state.current_step.value}")
            print(f"Completed: {len(state.completed_steps)}/10 steps")
            return 1

        spec = workflow.generate_strategy_spec(state)
        print("Generated strategy specification:")
        print(json.dumps(spec, indent=2))
        return 0

    # Finalize mode - create strategy and optionally run validation
    if args.finalize:
        if not state.is_complete:
            print(f"Development not complete. Current step: {state.current_step.value}")
            print(f"Completed: {len(state.completed_steps)}/10 steps")
            print("Complete all steps before finalizing.")
            return 1

        # Create strategy entry
        print("Creating strategy entry from development...")
        strategy_id = workflow.create_strategy_entry(state, catalog)
        print(f"Created: {strategy_id}")
        print()

        # Optionally run validation
        if args.run:
            print(f"Running walk-forward validation for {strategy_id}...")
            print()
            # Import and run the pipeline
            from scripts.validate.full_pipeline import FullPipelineRunner
            runner = FullPipelineRunner(ws, llm_client, use_walk_forward=True)
            result = runner.run(strategy_id)

            if result.determination == "VALIDATED":
                print(f"\n{strategy_id}: VALIDATED")
            else:
                print(f"\n{strategy_id}: {result.determination}")
                if result.error:
                    print(f"Error: {result.error}")
        else:
            print(f"To validate: research run {strategy_id} --walk-forward")

        return 0

    # Interactive development
    _run_interactive_step(workflow, state, llm_client)
    return 0


def _show_development_status(state):
    """Show development progress."""
    from scripts.develop.workflow import STEP_ORDER, STEP_DEFINITIONS

    print(f"Development Status: {state.entry_id}")
    print("=" * 50)
    print()
    print(f"Original idea: {state.original_idea[:100]}...")
    print()
    print(f"Progress: {len(state.completed_steps)}/10 steps")
    print()

    for i, step in enumerate(STEP_ORDER, 1):
        info = STEP_DEFINITIONS[step]
        if step.value in state.completed_steps:
            status = "[x]"
        elif step == state.current_step:
            status = "[>]"
        else:
            status = "[ ]"
        print(f"  {status} {i}. {info['name']}")

    print()
    if state.is_complete:
        print("Development complete! Run with --complete to generate strategy spec.")
    else:
        info = STEP_DEFINITIONS[state.current_step]
        print(f"Current step: {info['name']}")
        print(f"Question: {info['question']}")


def _run_interactive_step(workflow, state, llm_client):
    """Run interactive development for current step."""
    from scripts.develop.workflow import STEP_DEFINITIONS

    step = state.current_step
    info = STEP_DEFINITIONS[step]

    print(f"Step {list(STEP_DEFINITIONS.keys()).index(step) + 1}: {info['name']}")
    print("=" * 50)
    print()
    print(f"Question: {info['question']}")
    print()
    print(info['description'])
    print()
    print("Guidance:")
    print(info['guidance'])
    print()

    # Show required outputs
    print(f"Required outputs: {', '.join(info['required_outputs'])}")
    print()

    # Collect outputs interactively
    outputs = {}
    for output_name in info['required_outputs']:
        print(f"\n{output_name}:")
        print("  (Enter your response, or 'suggest' for LLM suggestion)")
        print("  (End with a blank line)")
        print()

        lines = []
        while True:
            line = input("  > ").strip()
            if not line:
                break
            if line.lower() == 'suggest' and llm_client:
                suggestion = _get_llm_suggestion(
                    llm_client, state.original_idea, step, output_name, info
                )
                print(f"\n  Suggestion: {suggestion}")
                print("  (Accept with blank line, or type your own)")
                continue
            lines.append(line)

        if lines:
            outputs[output_name] = "\n".join(lines)
        else:
            print(f"  Warning: {output_name} is required")

    # Check if all required outputs provided
    missing = [r for r in info['required_outputs'] if r not in outputs]
    if missing:
        print(f"\nMissing required outputs: {missing}")
        print("Step not completed. Run again to continue.")
        return

    # Notes
    print("\nAny additional notes? (optional, blank to skip)")
    notes = input("  > ").strip()

    # Complete the step
    state = workflow.complete_step(state, step, outputs, notes)
    print(f"\n✓ Completed: {info['name']}")

    if state.is_complete:
        print("\n🎉 All steps complete!")
        print("Run 'research develop {state.entry_id} --complete' to generate strategy spec.")
    else:
        next_info = STEP_DEFINITIONS[state.current_step]
        print(f"\nNext step: {next_info['name']}")
        print("Run 'research develop {state.entry_id}' to continue.")


def _get_llm_suggestion(llm_client, original_idea, step, output_name, step_info):
    """Get LLM suggestion for a step output."""
    prompt = f"""You are helping develop a trading strategy. The original idea is:

"{original_idea}"

We're on step: {step_info['name']}
Question: {step_info['question']}

Provide a concise suggestion for: {output_name}

{step_info['guidance']}

Be specific and actionable. Keep it to 2-3 sentences."""

    try:
        return llm_client.generate(prompt, max_tokens=300)
    except Exception as e:
        return f"(Could not generate suggestion: {e})"


def cmd_combine_generate(args):
    """Generate combination matrix."""
    print("Generating combinations...")
    print("Combine generate not yet fully implemented")
    return 0


def cmd_combine_list(args):
    """List combinations."""
    print("Combine list not yet fully implemented")
    return 0


def cmd_combine_prioritize(args):
    """Prioritize combinations."""
    print("Prioritizing combinations...")
    return 0


def cmd_combine_next(args):
    """Get next batch to test."""
    print(f"Getting next {args.count} combinations to test...")
    return 0


def cmd_analyze_run(args):
    """Run persona analysis."""
    ws = require_workspace(args.workspace)

    # Check validation exists
    val_dir = ws.validations_path / args.id
    if not val_dir.exists():
        print(f"Error: No validation found for {args.id}")
        print(f"Complete validation first with: research validate start {args.id}")
        return 1

    # Load validation results
    validation_results = _load_validation_results(val_dir)

    if not validation_results:
        print(f"Error: No validation results found for {args.id}")
        return 1

    # Initialize LLM client
    llm_client = None
    try:
        from research_system.llm.client import LLMClient, Backend
        llm_client = LLMClient()
        if llm_client.is_offline:
            print("Note: Running in offline mode (no ANTHROPIC_API_KEY or claude CLI)")
            print("Persona analysis will return prompts only.")
            print()
        elif llm_client.backend == Backend.CLI:
            print("Using Claude CLI backend.")
        elif llm_client.backend == Backend.API:
            print("Using Anthropic API backend.")
    except Exception as e:
        print(f"Warning: Could not initialize LLM client: {e}")
        print("Running in offline mode.")

    from agents.runner import PersonaRunner, run_persona_analysis, save_analysis_result

    if args.persona:
        # Run single persona
        print(f"Running {args.persona} analysis for {args.id}...")
        runner = PersonaRunner(llm_client)
        response = runner.run_persona(args.persona, validation_results)

        if response.error:
            print(f"Error: {response.error}")
            return 1

        print()
        if response.structured_response:
            print(json.dumps(response.structured_response, indent=2))
        else:
            print("Raw response:")
            print(response.raw_response)

    else:
        # Run full multi-persona analysis
        print(f"Running multi-persona analysis for {args.id}...")
        print("Personas: momentum-trader, risk-manager, quant-researcher, contrarian, report-synthesizer")
        print()

        result = run_persona_analysis(args.id, validation_results, llm_client)

        # Save results
        save_analysis_result(result, val_dir)

        # Print summary
        print("Persona Analysis Complete")
        print("=" * 50)
        for persona, response in result.responses.items():
            status = "OK" if response.structured_response else "Parse Error" if response.raw_response else "Error"
            error_info = f" - {response.error}" if response.error else ""
            print(f"  {persona}: {status}{error_info}")

        print()
        if result.consensus_points:
            print("Consensus Points:")
            for point in result.consensus_points[:5]:
                print(f"  - {point}")

        if result.disagreements:
            print()
            print("Disagreements:")
            for point in result.disagreements[:3]:
                print(f"  - {point}")

        if result.final_recommendation:
            print()
            print(f"Final Recommendation: {result.final_recommendation}")

        print()
        print(f"Full results saved to: {val_dir / 'persona_analysis.json'}")

    return 0


def _load_validation_results(val_dir: Path) -> dict:
    """Load validation results from a validation directory."""
    results = {}

    # Load metadata
    metadata_file = val_dir / "metadata.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        results["component_id"] = metadata.get("component_id")
        results["determination"] = metadata.get("determination")
        results["sanity_flags"] = metadata.get("sanity_flags", [])

    # Load hypothesis
    hypothesis_file = val_dir / "hypothesis.json"
    if hypothesis_file.exists():
        with open(hypothesis_file, 'r') as f:
            hypothesis = json.load(f)
        results["hypothesis"] = hypothesis.get("statement")
        results["test_type"] = hypothesis.get("test_role", "standalone")

    # Load IS results
    is_results_file = val_dir / "is_test" / "results.json"
    if is_results_file.exists():
        with open(is_results_file, 'r') as f:
            is_data = json.load(f)
        backtest = is_data.get("backtest_results", {})
        results["sharpe_ratio"] = backtest.get("sharpe_ratio", backtest.get("sharpe", 0))
        results["alpha"] = backtest.get("alpha", backtest.get("annual_alpha", 0))
        results["cagr"] = backtest.get("cagr", 0)
        results["max_drawdown"] = backtest.get("max_drawdown", 0)
        results["total_trades"] = backtest.get("total_trades", 0)
        results["win_rate"] = backtest.get("win_rate", 0)

        baseline = is_data.get("baseline_results", {})
        if baseline:
            results["baseline_sharpe"] = baseline.get("sharpe_ratio", baseline.get("sharpe", 0))
            results["sharpe_improvement"] = results["sharpe_ratio"] - results["baseline_sharpe"]

    # Load statistical analysis
    stat_file = val_dir / "statistical_analysis.json"
    if stat_file.exists():
        with open(stat_file, 'r') as f:
            stat_data = json.load(f)
        results["p_value"] = stat_data.get("summary", {}).get("lowest_p_value", 1.0)
        results["is_significant"] = stat_data.get("any_significant", False)

    # Load regime analysis
    regime_file = val_dir / "regime_analysis.json"
    if regime_file.exists():
        with open(regime_file, 'r') as f:
            regime_data = json.load(f)
        results["regime_results"] = regime_data.get("regime_results", [])
        results["consistent_across_regimes"] = regime_data.get("consistent_across_regimes", True)

    # Load OOS results
    oos_results_file = val_dir / "oos_test" / "results.json"
    if oos_results_file.exists():
        with open(oos_results_file, 'r') as f:
            oos_data = json.load(f)
        oos = oos_data.get("oos_results", {})
        results["oos_alpha"] = oos.get("alpha", oos.get("annual_alpha", 0))
        results["oos_sharpe"] = oos.get("sharpe_ratio", oos.get("sharpe", 0))

    return results


def cmd_analyze_show(args):
    """Show analysis results."""
    ws = require_workspace(args.workspace)

    val_dir = ws.validations_path / args.id
    analysis_file = val_dir / "persona_analysis.json"

    if not analysis_file.exists():
        print(f"No analysis results found for {args.id}")
        print(f"Run analysis with: research analyze run {args.id}")
        return 1

    with open(analysis_file, 'r') as f:
        analysis = json.load(f)

    print(f"Persona Analysis Results: {args.id}")
    print("=" * 60)
    print(f"Timestamp: {analysis.get('timestamp', 'unknown')}")
    print()

    # Show each persona's response
    for persona, response in analysis.get("responses", {}).items():
        print(f"--- {persona} ---")
        if response.get("structured_response"):
            sr = response["structured_response"]
            verdict = sr.get("verdict", sr.get("overall_assessment", "N/A"))
            print(f"  Verdict: {verdict}")
            observations = sr.get("key_observations", [])[:3]
            if observations:
                print("  Key observations:")
                for obs in observations:
                    print(f"    - {obs}")
        elif response.get("error"):
            print(f"  Error: {response['error']}")
        print()

    # Show synthesis
    if analysis.get("consensus_points"):
        print("Consensus Points:")
        for point in analysis["consensus_points"]:
            print(f"  - {point}")
        print()

    if analysis.get("disagreements"):
        print("Disagreements:")
        for point in analysis["disagreements"]:
            print(f"  - {point}")
        print()

    if analysis.get("final_recommendation"):
        print(f"Final Recommendation: {analysis['final_recommendation']}")

    return 0


def cmd_ideate(args):
    """Generate strategy ideas using multiple personas."""
    ws = require_workspace(args.workspace)

    # Initialize LLM client
    llm_client = None
    try:
        from research_system.llm.client import LLMClient, Backend
        llm_client = LLMClient()
        if llm_client.is_offline:
            print("Note: Running in offline mode (no ANTHROPIC_API_KEY or claude CLI)")
            print("Ideation will return prompts only, no actual ideas generated.")
            print()
        elif llm_client.backend == Backend.CLI:
            print("Using Claude CLI backend.")
        elif llm_client.backend == Backend.API:
            print("Using Anthropic API backend.")
    except Exception as e:
        print(f"Warning: Could not initialize LLM client: {e}")
        print("Running in offline mode.")

    from agents.ideation import IdeationRunner, save_ideation_result

    runner = IdeationRunner(ws, llm_client)

    if args.persona:
        # Run single persona
        print(f"Running ideation with {args.persona}...")
        print()

        ideas, meta = runner.run_persona(args.persona)

        if not ideas:
            print("No ideas generated.")
            if meta.get("error"):
                print(f"Error: {meta['error']}")
            return 1

        print(f"Generated {len(ideas)} ideas:")
        print()

        for i, idea in enumerate(ideas, 1):
            print(f"[{i}] {idea.name}")
            print(f"    Thesis: {idea.thesis[:100]}...")
            print(f"    Hypothesis: {idea.hypothesis[:100]}...")
            print(f"    Data: {', '.join(idea.data_requirements[:3])}")
            print(f"    Confidence: {idea.confidence}")
            print()

        if not args.dry_run:
            # Create a result to add to catalog
            from agents.ideation import IdeationResult
            result = IdeationResult(ideas=ideas, personas_run=[args.persona])
            created_ids = runner.add_ideas_to_catalog(result)
            print(f"Added {len(created_ids)} ideas to catalog: {', '.join(created_ids)}")

    else:
        # Run all personas
        print("Running multi-persona ideation...")
        print("Personas: edge-hunter, macro-strategist, quant-archaeologist")
        print()

        result = runner.run(count=args.count)

        if not result.ideas:
            print("No ideas generated.")
            if result.errors:
                print("Errors:")
                for err in result.errors:
                    print(f"  - {err}")
            return 1

        print(f"Generated {len(result.ideas)} ideas from {len(result.personas_run)} personas:")
        print()

        # Group by persona
        by_persona = {}
        for idea in result.ideas:
            if idea.persona not in by_persona:
                by_persona[idea.persona] = []
            by_persona[idea.persona].append(idea)

        for persona, ideas in by_persona.items():
            print(f"--- {persona} ({len(ideas)} ideas) ---")
            for idea in ideas:
                print(f"  * {idea.name}")
                print(f"    {idea.thesis[:80]}...")
                print(f"    Confidence: {idea.confidence}")
            print()

        # Show data gaps and suggestions
        if result.data_gaps:
            print("Data Gaps Identified:")
            for gap in result.data_gaps[:5]:
                print(f"  - {gap}")
            print()

        if result.research_suggestions:
            print("Research Suggestions:")
            for suggestion in result.research_suggestions[:5]:
                print(f"  - {suggestion}")
            print()

        # Save results if requested
        if args.save:
            output_dir = ws.path / "ideation"
            output_file = save_ideation_result(result, output_dir)
            print(f"Saved results to: {output_file}")

        # Add to catalog unless dry-run
        if not args.dry_run:
            created_ids = runner.add_ideas_to_catalog(result)
            print(f"Added {len(created_ids)} ideas to catalog:")
            for entry_id in created_ids:
                print(f"  - {entry_id}")
        else:
            print("[DRY-RUN] Ideas not added to catalog")

    return 0


def cmd_synthesize(args):
    """Run cross-strategy synthesis with expert panel."""
    ws = require_workspace(args.workspace)

    # Initialize LLM client
    llm_client = None
    try:
        from research_system.llm.client import LLMClient, Backend
        llm_client = LLMClient()
        if llm_client.is_offline:
            print("Note: Running in offline mode (no ANTHROPIC_API_KEY or claude CLI)")
            print("Synthesis will return prompts only, no actual analysis.")
            print()
        elif llm_client.backend == Backend.CLI:
            print("Using Claude CLI backend.")
        elif llm_client.backend == Backend.API:
            print("Using Anthropic API backend.")
    except Exception as e:
        print(f"Warning: Could not initialize LLM client: {e}")
        print("Running in offline mode.")

    from agents.synthesis import (
        SynthesisRunner,
        ContextAggregator,
        save_synthesis_result,
        generate_synthesis_report
    )

    runner = SynthesisRunner(ws, llm_client)

    # Dry run - just show what would be analyzed
    if args.dry_run:
        aggregator = ContextAggregator(ws)
        context = aggregator.aggregate(
            min_sharpe=args.min_sharpe,
            max_drawdown=args.max_drawdown,
            top_n=args.top
        )

        print(f"[DRY-RUN] Would analyze {context.summary_stats['total_validated']} entries:")
        print(f"  Strategies: {context.summary_stats['strategies']}")
        print(f"  Ideas: {context.summary_stats['ideas']}")
        print(f"  Indicators: {context.summary_stats['indicators']}")
        print(f"  Avg Sharpe: {context.summary_stats['avg_sharpe']:.2f}")
        print()
        print("Top entries by Sharpe:")
        all_entries = context.validated_strategies + context.validated_ideas
        for entry in sorted(all_entries, key=lambda x: x.sharpe or 0, reverse=True)[:10]:
            print(f"  {entry.id}: {entry.name[:40]} (Sharpe={entry.sharpe:.2f})")
        return 0

    # Single persona mode
    if args.persona:
        print(f"Running synthesis with {args.persona}...")
        print()

        aggregator = ContextAggregator(ws)
        context = aggregator.aggregate(
            min_sharpe=args.min_sharpe,
            max_drawdown=args.max_drawdown,
            top_n=args.top
        )

        response = runner.run_persona(args.persona, context)

        if response.error:
            print(f"Error: {response.error}")
            return 1

        print(f"Response from {args.persona}:")
        print()
        if response.structured_response:
            print(json.dumps(response.structured_response, indent=2))
        else:
            print("Raw response:")
            print(response.raw_response[:2000])

        return 0

    # Full synthesis
    print("Running multi-persona synthesis...")
    print("Personas: portfolio-architect, instrument-specialist, data-integrator,")
    print("          regime-strategist, creative-maverick, synthesis-director")
    print()

    result = runner.run(
        min_sharpe=args.min_sharpe,
        max_drawdown=args.max_drawdown,
        top_n=args.top
    )

    if result.errors:
        print("Errors encountered:")
        for err in result.errors:
            print(f"  - {err}")
        print()

    # Summary
    print("=" * 60)
    print("SYNTHESIS COMPLETE")
    print("=" * 60)
    print(f"Entries analyzed: {result.context_summary.get('total_validated', 0)}")
    print(f"  Strategies: {result.context_summary.get('strategies', 0)}")
    print(f"  Ideas: {result.context_summary.get('ideas', 0)}")
    print()

    # Show persona status
    print("Persona Analysis:")
    for persona, response in result.responses.items():
        status = "OK" if response.structured_response else "Parse Error" if response.raw_response else "Error"
        print(f"  {persona}: {status}")
    print()

    # Show consensus
    if result.consensus_points:
        print("Consensus Points:")
        for point in result.consensus_points[:5]:
            print(f"  - {point}")
        print()

    # Show opportunities
    if result.prioritized_opportunities:
        print(f"Top Opportunities ({len(result.prioritized_opportunities)} found):")
        for i, opp in enumerate(result.prioritized_opportunities[:5], 1):
            name = opp.get('name', 'Opportunity')
            benefit = opp.get('expected_benefit', 'N/A')
            complexity = opp.get('implementation_complexity', 'N/A')
            print(f"  {i}. {name}")
            print(f"     Benefit: {benefit}, Complexity: {complexity}")
        print()

    # Show recommended entries
    if result.recommended_entries:
        print(f"Recommended New Entries ({len(result.recommended_entries)}):")
        for entry in result.recommended_entries[:5]:
            print(f"  - {entry.get('name', 'Entry')} ({entry.get('type', 'idea')})")
        print()

    # Save results
    output_dir = ws.path / "synthesis"
    if args.save:
        output_file = save_synthesis_result(result, output_dir)
        print(f"Raw results saved to: {output_file}")

    # Generate report
    report_file = generate_synthesis_report(result, output_dir)
    print(f"Report saved to: {report_file}")

    # Create catalog entries if requested
    if args.create_entries and result.recommended_entries:
        print()
        print("Creating catalog entries...")
        created_ids = runner.create_catalog_entries(result)
        print(f"Created {len(created_ids)} entries:")
        for entry_id in created_ids:
            print(f"  - {entry_id}")

    return 0


def cmd_migrate_master_index(args):
    """Migrate from MASTER_INDEX.json."""
    source = Path(args.source)
    if not source.exists():
        print(f"Error: File not found: {source}")
        return 1

    mode = "dry-run" if args.dry_run else "validate-only" if args.validate_only else "full"
    print(f"Migrating from {source}")
    print(f"Mode: {mode}")
    print("Migration not yet fully implemented")
    return 0


# ============================================================================
# Run Command - The Core Validation + Expert Loop
# ============================================================================

def cmd_run(args):
    """Run the full validation + expert review loop."""
    ws = require_workspace(args.workspace)
    catalog = Catalog(ws.catalog_path)

    # Get entries to process
    if args.id:
        # Single entry
        entry = catalog.get(args.id)
        if not entry:
            print(f"Error: Entry not found: {args.id}")
            return 1
        entries = [entry]
    else:
        # All UNTESTED entries
        entries = catalog.query().by_status("UNTESTED").execute()
        if not entries:
            print("No UNTESTED entries to process.")
            print("Run 'research catalog list' to see all entries.")
            return 0

    if args.dry_run:
        print(f"[DRY-RUN] Would process {len(entries)} entries:")
        for entry in entries:
            # entries from query are dicts, from get() are CatalogEntry objects
            if isinstance(entry, dict):
                print(f"  {entry['id']}: {entry['name']}")
            else:
                print(f"  {entry.id}: {entry.name}")
        return 0

    # Initialize LLM client for code generation and expert review
    llm_client = None
    try:
        from research_system.llm.client import LLMClient
        llm_client = LLMClient()
        if llm_client.is_offline:
            print("Warning: Running in offline mode. Code generation and expert review will be limited.")
    except Exception as e:
        print(f"Warning: Could not initialize LLM client: {e}")

    # Import the full pipeline runner
    try:
        from scripts.validate.full_pipeline import FullPipelineRunner
    except ImportError:
        print("Error: Full pipeline runner not yet implemented.")
        print("This will run the complete validation + expert loop.")
        print()
        print(f"Would process {len(entries)} entries:")
        for entry in entries:
            print(f"  {entry.id}: {entry.name} ({entry.status})")
        return 1

    # Run the pipeline
    use_local = getattr(args, 'local', False)
    use_walk_forward = getattr(args, 'walk_forward', False)

    if use_walk_forward:
        print("Using walk-forward validation (12 windows from 2008-2024)")
        print()

    runner = FullPipelineRunner(ws, llm_client, use_local=use_local, use_walk_forward=use_walk_forward)

    results = {
        "validated": 0,
        "invalidated": 0,
        "failed": 0,
        "derived_ideas": 0
    }

    print(f"Processing {len(entries)} entries...")
    print("=" * 60)
    print()

    for i, entry in enumerate(entries, 1):
        # Handle both dict (from query) and CatalogEntry (from get)
        entry_id = entry['id'] if isinstance(entry, dict) else entry.id
        entry_name = entry['name'] if isinstance(entry, dict) else entry.name

        print(f"[{i}/{len(entries)}] {entry_id}: {entry_name}")
        print("-" * 60)

        try:
            result = runner.run(entry_id)

            if result.determination == "VALIDATED":
                results["validated"] += 1
                print(f"  → VALIDATED")
            elif result.determination == "CONDITIONAL":
                results["validated"] += 1
                print(f"  → CONDITIONAL")
            elif result.determination == "INVALIDATED":
                results["invalidated"] += 1
                print(f"  → INVALIDATED")
            else:
                results["failed"] += 1
                print(f"  → {result.determination}")
                if result.error:
                    print(f"     Error: {result.error}")

            if result.derived_ideas:
                results["derived_ideas"] += len(result.derived_ideas)
                print(f"  → Added {len(result.derived_ideas)} derived ideas")

        except Exception as e:
            results["failed"] += 1
            print(f"  → ERROR: {e}")

        print()

    # Summary
    print("=" * 60)
    print("Summary:")
    print(f"  VALIDATED:    {results['validated']}")
    print(f"  INVALIDATED:  {results['invalidated']}")
    print(f"  FAILED:       {results['failed']}")
    print(f"  DERIVED:      {results['derived_ideas']} new ideas")
    print()

    return 0


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        if hasattr(args, 'func'):
            return args.func(args)
        else:
            parser.print_help()
            return 0
    except WorkspaceError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except V4WorkspaceError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_update(args):
    """Update research-kit to the latest version."""
    import subprocess
    import importlib.metadata

    check_only = getattr(args, 'check', False)

    # Get current version
    try:
        current_version = importlib.metadata.version("research-kit")
    except importlib.metadata.PackageNotFoundError:
        current_version = "unknown"

    print(f"Current version: {current_version}")

    # Find how the package was installed
    try:
        # Get package location
        import research_system
        pkg_path = Path(research_system.__file__).parent.parent

        # Check if it's an editable install (source directory with .git)
        git_dir = pkg_path / ".git"
        is_editable = git_dir.exists()

        if is_editable:
            print(f"Installation: editable (source at {pkg_path})")

            if check_only:
                # Just fetch and check
                result = subprocess.run(
                    ["git", "fetch"],
                    cwd=pkg_path,
                    capture_output=True,
                    text=True
                )
                result = subprocess.run(
                    ["git", "log", "HEAD..origin/main", "--oneline"],
                    cwd=pkg_path,
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip():
                    print(f"\nUpdates available:")
                    print(result.stdout)
                else:
                    print("\nAlready up to date.")
                return 0

            # Pull latest
            print("\nPulling latest changes...")
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=pkg_path,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
                return 1
            print(result.stdout)

            # Reinstall
            print("Reinstalling...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", "."],
                cwd=pkg_path,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
                return 1

        else:
            # Installed via pip from git or PyPI
            print("Installation: pip package")

            if check_only:
                print("\nRun 'research update' to update to latest version.")
                return 0

            print("\nUpdating via pip...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade",
                 "git+https://github.com/extremevalue/research-kit.git"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
                return 1

        # Get new version
        # Need to reload to get new version
        importlib.invalidate_caches()
        try:
            # Re-import to get new version
            result = subprocess.run(
                [sys.executable, "-c",
                 "import importlib.metadata; print(importlib.metadata.version('research-kit'))"],
                capture_output=True,
                text=True
            )
            new_version = result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            new_version = "unknown"

        print(f"\nUpdated: {current_version} -> {new_version}")
        print("Restart your terminal or run 'hash -r' to use the new version.")
        return 0

    except Exception as e:
        print(f"Error during update: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
