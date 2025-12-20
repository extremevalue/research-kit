---
name: research-workflow
description: Research Validation System workflow - CLI is the only interface
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
---

# Research Validation System Skill

You are assisting with the Research Validation System, a CLI tool for validating trading strategies and indicators with statistical rigor.

## Critical Rules

1. **CLI is the only interface** - All changes go through the `research` CLI. You do NOT have Write/Edit tools.
2. **Deterministic decisions** - LLM extracts metadata; code makes test decisions. Never judge if a p-value is "good enough."
3. **Gates cannot be skipped** - The 7-stage validation pipeline must be followed in order.
4. **OOS is one shot** - Out-of-sample testing happens exactly once. No retries. No parameter adjustments after.
5. **Parameters lock before testing** - All parameters are locked at HYPOTHESIS stage.
6. **Fail loudly** - Report errors clearly. Never silently continue.

## Validation Pipeline (7 Mandatory Stages)

```
HYPOTHESIS -> DATA_AUDIT -> IS_TESTING -> STATISTICAL -> REGIME -> OOS_TESTING -> DETERMINATION
```

Each stage must pass before proceeding. No shortcuts.

## Available Commands

### Workspace
```bash
research init [path]                    # Initialize workspace
research init --name "My Research"      # With custom name
research --workspace PATH <command>     # Use specific workspace
```

### Ingestion
```bash
research ingest list                    # List inbox files
research ingest add <file>              # Add file to inbox
research ingest process                 # Process all inbox files
research ingest process --dry-run       # Preview what would be created
research ingest process --file <name>   # Process specific file
```

### Catalog
```bash
research catalog list                   # List all entries
research catalog list --type indicator  # Filter by type
research catalog list --status BLOCKED  # Filter by status
research catalog show <id>              # Show entry details
research catalog add --type <t> --name <n> --source <files>  # Add entry
research catalog stats                  # Show statistics
research catalog search <query>         # Search entries
```

### Data Registry
```bash
research data list                      # List data sources
research data list --available          # Only available sources
research data show <id>                 # Show source details
research data check <ids...>            # Check availability
research data add --id <id> --name <n> --type <t>  # Add source
```

### Validation
```bash
research validate start <id>            # Start validation pipeline
research validate status <id>           # Check current stage
research validate hypothesis <id> --file hypothesis.json  # Submit hypothesis
research validate audit <id>            # Run data audit
research validate run <id>              # Run next stage
research validate submit-is <id> --file results.json     # Submit IS results
research validate submit-oos <id> --file results.json --confirm  # Submit OOS (ONE SHOT!)
research validate list                  # List all validations
```

### Combinations
```bash
research combine generate               # Generate indicator+strategy combinations
research combine list                   # List combinations
research combine list --top 10          # Top 10 by priority
research combine prioritize             # Recalculate priorities
research combine next --count 5         # Get next batch to test
```

### Analysis
```bash
research analyze run <id>               # Run full multi-persona analysis
research analyze run <id> --persona contrarian  # Run specific persona
research analyze show <id>              # Show analysis results
```

### Migration
```bash
research migrate master-index <path>    # Migrate from MASTER_INDEX.json
research migrate master-index <path> --dry-run  # Preview migration
```

## Entry Types
- `indicator` - Technical indicators (IND-XXX)
- `strategy` - Trading strategies (STRAT-XXX)
- `idea` - Research ideas to explore (IDEA-XXX)
- `learning` - Learnings from failed tests (LEARN-XXX)
- `tool` - Utility tools (TOOL-XXX)
- `data` - Data sources (DATA-XXX)

## Status Values
- `UNTESTED` - Ready for validation
- `BLOCKED` - Missing data requirements
- `IN_PROGRESS` - Validation started
- `VALIDATED` - Passed all tests, works broadly
- `CONDITIONAL` - Passed with caveats (regime-specific)
- `INVALIDATED` - Failed testing

## Statistical Thresholds
| Metric | Threshold |
|--------|-----------|
| p-value | < 0.01 |
| p-value (Bonferroni) | < 0.01/N |
| Alpha | > 1% annualized |
| Sharpe improvement | > 0.10 |

## Data Hierarchy (in order of preference)
1. QC Native (QuantConnect built-in)
2. QC Object Store (uploaded to QC)
3. Internal Purchased (paid data - never delete)
4. Internal Curated (validated free data)
5. Internal Experimental (unverified)

## Personas (for analysis)
- **momentum-trader** - Trend-following perspective
- **risk-manager** - Risk and drawdown focus
- **quant-researcher** - Statistical rigor
- **contrarian** - Challenges consensus
- **report-synthesizer** - Integrates all perspectives

## Workflow Example

```bash
# 1. Initialize workspace
research init ~/my-research

# 2. Add files to inbox and process
research ingest add paper.pdf
research ingest process

# 3. Check what was created
research catalog list

# 4. Start validation
research validate start IND-001

# 5. Submit hypothesis (locks parameters)
research validate hypothesis IND-001 --file hypothesis.json

# 6. Run through pipeline
research validate run IND-001  # DATA_AUDIT
research validate run IND-001  # IS_TESTING (submit results)
research validate run IND-001  # STATISTICAL
research validate run IND-001  # REGIME
research validate run IND-001  # OOS_TESTING (ONE SHOT!)
research validate run IND-001  # DETERMINATION

# 7. Run persona analysis
research analyze run IND-001

# 8. Check final status
research catalog show IND-001
```

## Important Reminders

- **BLOCKED is a parking lot, not a dead end** - Entries wait for data. One data source can unlock many entries.
- **Nothing thrown away** - Failed tests generate learnings. Learnings spawn new ideas.
- **Reproducibility** - Every validation must be reproducible by someone else.
- **Lineage tracking** - When ideas spawn from analysis, track parent-child relationships.
