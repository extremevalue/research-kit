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
    _add_ingest_parser(subparsers)
    _add_catalog_parser(subparsers)
    _add_data_parser(subparsers)
    _add_run_parser(subparsers)  # The core validation + expert loop
    _add_validate_parser(subparsers)
    _add_status_parser(subparsers)  # Dashboard and reports
    _add_develop_parser(subparsers)  # Idea development workflow (R2)
    _add_combine_parser(subparsers)
    _add_analyze_parser(subparsers)
    _add_ideate_parser(subparsers)  # Multi-persona ideation
    _add_synthesize_parser(subparsers)  # Cross-strategy synthesis
    _add_migrate_parser(subparsers)

    # Add V4 commands
    _add_v4_commands(subparsers)

    return parser


def _add_init_parser(subparsers):
    """Add init command parser."""
    parser = subparsers.add_parser(
        "init",
        help="Initialize a new workspace",
        description="""
Initialize a new research workspace at the specified path.

Standard workspace:
  - inbox/           Files to be ingested
  - reviewed/        Processed files that didn't create entries (purgeable)
  - catalog/entries/ Catalog entry metadata (JSON)
  - catalog/sources/ Original files that created entries
  - data-registry/   Data source definitions
  - validations/     Validation results
  - combinations/    Generated combinations
  - config.json      Workspace configuration

V4 workspace (--v4):
  - inbox/                Files to be ingested
  - strategies/           Strategy documents by status
  - validations/          Walk-forward validation results
  - learnings/            Extracted learnings
  - ideas/                Strategy ideas (pre-formalization)
  - research-kit.yaml     Configuration file
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Path for new workspace (default: ~/.research-workspace or ~/.research-workspace-v4 with --v4)"
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
    parser.add_argument(
        "--v4",
        action="store_true",
        help="Initialize a V4 workspace with the new directory structure"
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
    - init --v4: Initialize V4 workspace
    - v4-ingest: Ingest files from inbox with quality scoring
    - v4-verify: Run verification tests (bias detection)
    - v4-validate: Run walk-forward validation
    - v4-learn: Extract learnings from validation results
    - v4-status: Show workspace status dashboard
    - v4-list: List strategies with filtering
    - v4-show: Show strategy details
    - v4-config: Show/validate configuration
    """
    # v4-ingest command
    parser = subparsers.add_parser(
        "v4-ingest",
        help="Ingest files from inbox into strategies (V4)",
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
        help="Path to V4 workspace (default: RESEARCH_WORKSPACE or ~/.research-workspace-v4)"
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

    # v4-verify command
    parser = subparsers.add_parser(
        "v4-verify",
        help="Run verification tests on a strategy (V4)",
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
        help="Path to V4 workspace"
    )
    parser.set_defaults(func=cmd_v4_verify)

    # v4-validate command
    parser = subparsers.add_parser(
        "v4-validate",
        help="Run walk-forward validation on a strategy (V4)",
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
        help="Path to V4 workspace"
    )
    parser.set_defaults(func=cmd_v4_validate)

    # v4-learn command
    parser = subparsers.add_parser(
        "v4-learn",
        help="Extract learnings from validation results (V4)",
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
        help="Path to V4 workspace"
    )
    parser.set_defaults(func=cmd_v4_learn)

    # v4-status command
    parser = subparsers.add_parser(
        "v4-status",
        help="Show workspace status dashboard (V4)",
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
        help="Path to V4 workspace"
    )
    parser.set_defaults(func=cmd_v4_status)

    # v4-list command
    parser = subparsers.add_parser(
        "v4-list",
        help="List strategies (V4)",
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
        help="Path to V4 workspace"
    )
    parser.set_defaults(func=cmd_v4_list)

    # v4-show command
    parser = subparsers.add_parser(
        "v4-show",
        help="Show strategy details (V4)",
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
        help="Path to V4 workspace"
    )
    parser.set_defaults(func=cmd_v4_show)

    # v4-config command
    parser = subparsers.add_parser(
        "v4-config",
        help="Show/validate V4 configuration",
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
        help="Path to V4 workspace"
    )
    parser.set_defaults(func=cmd_v4_config)


# ============================================================================
# Command Implementations
# ============================================================================

def cmd_init(args):
    """Initialize a new workspace."""
    # Check if V4 mode
    if getattr(args, 'v4', False):
        return cmd_init_v4(args)

    path = Path(args.path) if args.path else None
    workspace = get_workspace(str(path) if path else None)

    if workspace.exists and not args.force:
        print(f"Workspace already exists at {workspace.path}")
        print("Use --force to reinitialize")
        return 1

    workspace.init(name=args.name, force=args.force)
    print(f"Initialized workspace at {workspace.path}")
    print()
    print("Workspace structure:")
    print(f"  {workspace.path}/")
    print(f"  ├── inbox/           # Drop files here to ingest")
    print(f"  ├── reviewed/        # Processed files (purgeable)")
    print(f"  ├── catalog/")
    print(f"  │   ├── entries/     # Catalog entry metadata")
    print(f"  │   └── sources/     # Original source files")
    print(f"  ├── data-registry/   # Data source definitions")
    print(f"  ├── validations/     # Validation results")
    print(f"  ├── combinations/    # Generated combinations")
    print(f"  └── config.json      # Configuration")
    print()
    print("Next steps:")
    print(f"  1. Add files to {workspace.inbox_path}/")
    print("  2. Run 'research ingest process' to create catalog entries")
    print("  3. Run 'research validate start <ID>' to validate an entry")
    return 0


def cmd_init_v4(args):
    """Initialize a new V4 workspace."""
    path = Path(args.path) if args.path else None
    workspace = get_v4_workspace(path)

    if workspace.exists and not args.force:
        print(f"V4 workspace already exists at {workspace.path}")
        print("Use --force to reinitialize")
        return 1

    workspace.init(name=args.name, force=args.force)
    print(f"Initialized V4 workspace at {workspace.path}")
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
    print("  3. Run 'research v4-ingest' to create strategy documents")
    print("  4. Run 'research v4-verify STRAT-001' to run verification tests")
    print("  5. Run 'research v4-validate STRAT-001' to run walk-forward validation")
    return 0


# ============================================================================
# V4 Command Implementations
# ============================================================================


def cmd_v4_ingest(args):
    """Ingest files from inbox into strategies (V4)."""
    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init --v4' to initialize a V4 workspace.")
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
        for file_arg in args.files:
            file_path = Path(file_arg)
            if not file_path.exists():
                # Try relative to inbox
                file_path = workspace.inbox_path / file_arg
            if not file_path.exists():
                print(f"Error: File not found: {file_arg}")
                continue
            result = processor.process_file(file_path, dry_run=dry_run, force=force)
            results.append(result)
    else:
        # Process entire inbox
        summary = processor.process_inbox(dry_run=dry_run, force=force)
        results = summary.results

        if summary.total_files == 0:
            print(f"No files found in inbox: {workspace.inbox_path}")
            print("\nAdd files to the inbox directory and run again.")
            return 0

        print(f"Processing {summary.total_files} file(s) from inbox...\n")

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
        print("=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"Total files:  {summary.total_files}")
        print(f"Processed:    {summary.processed}")
        print(f"  Accepted:   {summary.accepted}")
        print(f"  Queued:     {summary.queued}")
        print(f"  Archived:   {summary.archived}")
        print(f"  Rejected:   {summary.rejected}")
        if summary.errors > 0:
            print(f"  Errors:     {summary.errors}")

    return 0


def cmd_v4_verify(args):
    """Run verification tests on a strategy (V4)."""
    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init --v4' to initialize a V4 workspace.")
        return 1

    print("V4 verify command not implemented yet.")
    print(f"Workspace: {workspace.path}")
    if args.strategy_id:
        print(f"Strategy ID: {args.strategy_id}")
    else:
        print("No strategy ID specified.")
        print("Usage: research v4-verify STRAT-001")
    return 0


def cmd_v4_validate(args):
    """Run walk-forward validation on a strategy (V4)."""
    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init --v4' to initialize a V4 workspace.")
        return 1

    print("V4 validate command not implemented yet.")
    print(f"Workspace: {workspace.path}")
    if args.strategy_id:
        print(f"Strategy ID: {args.strategy_id}")
    else:
        print("No strategy ID specified.")
        print("Usage: research v4-validate STRAT-001")
    return 0


def cmd_v4_learn(args):
    """Extract learnings from validation results (V4)."""
    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init --v4' to initialize a V4 workspace.")
        return 1

    print("V4 learn command not implemented yet.")
    print(f"Workspace: {workspace.path}")
    if args.strategy_id:
        print(f"Strategy ID: {args.strategy_id}")
    else:
        print("No strategy ID specified.")
        print("Usage: research v4-learn STRAT-001")
    return 0


def cmd_v4_status(args):
    """Show workspace status dashboard (V4)."""
    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init --v4' to initialize a V4 workspace.")
        return 1

    status = workspace.status()

    # Header
    print()
    print("=" * 60)
    print("  Research-Kit V4 Workspace Status")
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
        actions.append(f"Run 'research v4-ingest' to process {inbox_count} inbox file(s)")

    pending_count = status['strategies'].get('pending', 0)
    if pending_count > 0:
        actions.append(f"Run 'research v4-list --status pending' to see {pending_count} pending strategy(ies)")

    blocked_count = status['strategies'].get('blocked', 0)
    if blocked_count > 0:
        actions.append(f"Check {blocked_count} blocked strategy(ies) for missing data")

    if not actions:
        if total_strategies == 0:
            actions.append("Add research documents to inbox/ and run 'research v4-ingest'")
        else:
            actions.append("All caught up!")

    for action in actions:
        print(f"  > {action}")

    print()
    return 0


def cmd_v4_list(args):
    """List strategies (V4)."""
    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init --v4' to initialize a V4 workspace.")
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
    """Show strategy details (V4)."""
    import yaml

    workspace = get_v4_workspace(getattr(args, 'v4_workspace', None))

    try:
        workspace.require_initialized()
    except V4WorkspaceError as e:
        print(f"Error: {e}")
        print("Run 'research init --v4' to initialize a V4 workspace.")
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

    # Source
    source = strategy.get('source', {})
    if source:
        print(f"\n--- Source ---")
        if source.get('type'):
            print(f"Type:   {source['type']}")
        if source.get('author'):
            print(f"Author: {source['author']}")
        if source.get('url'):
            print(f"URL:    {source['url']}")
        if source.get('track_record'):
            print(f"Track Record: {source['track_record']}")

    # Hypothesis
    hypothesis = strategy.get('hypothesis', {})
    if hypothesis:
        print(f"\n--- Hypothesis ---")
        if hypothesis.get('thesis'):
            print(f"Thesis: {hypothesis['thesis']}")
        if hypothesis.get('type'):
            print(f"Type:   {hypothesis['type']}")
        if hypothesis.get('testable_prediction'):
            print(f"Testable Prediction: {hypothesis['testable_prediction']}")
        if hypothesis.get('expected_sharpe'):
            exp = hypothesis['expected_sharpe']
            if isinstance(exp, dict):
                print(f"Expected Sharpe: {exp.get('min', '?')} - {exp.get('max', '?')}")
            else:
                print(f"Expected Sharpe: {exp}")

    # Edge
    edge = strategy.get('edge', {})
    if edge:
        print(f"\n--- Edge ---")
        if edge.get('category'):
            print(f"Category: {edge['category']}")
        if edge.get('why_exists'):
            print(f"Why It Exists: {edge['why_exists']}")
        if edge.get('why_persists'):
            print(f"Why It Persists: {edge['why_persists']}")

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

    # Entry
    entry = strategy.get('entry', {})
    if entry:
        print(f"\n--- Entry ---")
        if entry.get('type'):
            print(f"Type: {entry['type']}")
        signals = entry.get('signals', [])
        for i, sig in enumerate(signals[:3], 1):
            if isinstance(sig, dict):
                print(f"Signal {i}: {sig.get('name', 'unnamed')} - {sig.get('condition', '')}")
        if len(signals) > 3:
            print(f"  ... and {len(signals)-3} more signals")

    # Exit
    exit_info = strategy.get('exit', {})
    if exit_info:
        print(f"\n--- Exit ---")
        paths = exit_info.get('paths', [])
        for path in paths[:3]:
            if isinstance(path, dict):
                print(f"- {path.get('name', 'unnamed')}: {path.get('condition', '')}")

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
        print("Run 'research init --v4' to initialize a V4 workspace.")
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
    print("V4 Configuration:")
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


if __name__ == "__main__":
    sys.exit(main())
