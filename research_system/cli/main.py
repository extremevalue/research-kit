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
    validate    Run validation pipeline
    combine     Generate and manage combinations
    analyze     Run persona-based analysis
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
    _add_combine_parser(subparsers)
    _add_analyze_parser(subparsers)
    _add_migrate_parser(subparsers)

    return parser


def _add_init_parser(subparsers):
    """Add init command parser."""
    parser = subparsers.add_parser(
        "init",
        help="Initialize a new workspace",
        description="""
Initialize a new research workspace at the specified path.

The workspace will contain:
  - inbox/         Files to be ingested
  - archive/       Ingested source files
  - catalog/       Research entries (indicators, strategies, etc.)
  - data-registry/ Data source definitions
  - validations/   Validation results
  - combinations/  Generated combinations
  - config.json    Workspace configuration
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
# Command Implementations
# ============================================================================

def cmd_init(args):
    """Initialize a new workspace."""
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
    print(f"  ├── inbox/          # Drop files here to ingest")
    print(f"  ├── archive/        # Ingested source files")
    print(f"  ├── catalog/        # Research entries")
    print(f"  ├── data-registry/  # Data source definitions")
    print(f"  ├── validations/    # Validation results")
    print(f"  ├── combinations/   # Generated combinations")
    print(f"  └── config.json     # Configuration")
    print()
    print("Next steps:")
    print(f"  1. Add files to {workspace.inbox_path}/")
    print("  2. Run 'research ingest process' to create catalog entries")
    print("  3. Run 'research validate start <ID>' to validate an entry")
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
    catalog = Catalog(ws)

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
        entries = catalog.list(status="UNTESTED")
        if not entries:
            print("No UNTESTED entries to process.")
            print("Run 'research catalog list' to see all entries.")
            return 0

    if args.dry_run:
        print(f"[DRY-RUN] Would process {len(entries)} entries:")
        for entry in entries:
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
    runner = FullPipelineRunner(ws, llm_client)

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
        print(f"[{i}/{len(entries)}] {entry.id}: {entry.name}")
        print("-" * 60)

        try:
            result = runner.run(entry.id)

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
    except KeyboardInterrupt:
        print("\nCancelled")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
