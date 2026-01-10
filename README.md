# Research Validation System

A systematic framework for validating trading strategies and indicators with proper statistical rigor, mandatory quality gates, and multi-perspective analysis.

> **V2 Development Status**: See [docs/V2-STATUS.md](docs/V2-STATUS.md) for current progress on the v2 rebuild (schemas, code generation, walk-forward validation).

## What This Tool Does

This tool helps you:

1. **Organize research** - Catalog trading indicators, strategies, and ideas in a structured format
2. **Validate hypotheses** - Test if trading signals actually work using QuantConnect backtesting
3. **Ensure statistical rigor** - Apply proper significance testing (p-values, Bonferroni correction)
4. **Avoid common mistakes** - Mandatory checks for look-ahead bias, survivorship bias, overfitting
5. **Get diverse perspectives** - AI personas (momentum trader, risk manager, etc.) analyze results

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [Lean CLI](https://www.lean.io/docs/lean-cli/installation) (optional) - credentials auto-detected for QC integration

## Quick Start

### 1. Install

**Recommended: Install with uv**

```bash
# Install persistently (available in PATH)
uv tool install research-kit --from git+https://github.com/your-repo/research-kit.git

# Or run once without installing
uvx --from git+https://github.com/your-repo/research-kit.git research --help
```

**Alternative: Install with pip**

```bash
pip install git+https://github.com/your-repo/research-kit.git
```

**Development install**

```bash
git clone https://github.com/your-repo/research-kit.git
cd research-kit
pip install -e ".[dev]"
```

### Upgrade

```bash
# With uv
uv tool install research-kit --force --from git+https://github.com/your-repo/research-kit.git

# With pip
pip install --upgrade git+https://github.com/your-repo/research-kit.git
```

### 2. Initialize a Workspace

Your workspace is where YOUR data lives - completely separate from the tool itself.

```bash
# Create a new workspace
research init ~/my-research

# Or let it use the default location (~/.research-workspace)
research init
```

This creates:
```
~/my-research/
├── inbox/              # Drop files here to process
├── reviewed/           # Processed files that didn't create entries (purgeable)
├── catalog/
│   ├── entries/        # Catalog entry metadata (JSON)
│   └── sources/        # Original files that created entries
├── data-registry/      # Your data source definitions
├── validations/        # Test results
├── combinations/       # Generated combinations
└── config.json         # Your settings
```

### 3. Ingest Research Materials

Drop files into your `inbox/` folder, then process them:

```bash
# Copy research files to inbox
cp ~/Downloads/strategy_paper.pdf ~/my-research/inbox/
cp -r ~/research/papers/ ~/my-research/inbox/

# Process all files in inbox
research ingest process

# Or preview what would happen
research ingest process --dry-run

# List inbox contents
research ingest list
```

**What happens during ingest:**
1. Each file is hashed (detects duplicates)
2. LLM extracts metadata (type, name, summary, data requirements)
3. Catalog entry is created
4. File moves to `catalog/sources/` (if entry created) or `reviewed/` (if skipped)

### 4. Work with Your Catalog

```bash
# See what's in your catalog
research catalog list

# See catalog statistics
research catalog stats

# Search entries
research catalog search "momentum"

# Show entry details
research catalog show IND-002
```

### 5. Validate Entries

```bash
# Start validating an entry
research validate start IND-002

# Check validation status
research validate status IND-002

# Generate indicator+strategy combinations
research combine generate
```

## Commands Reference

### `research init [path]`

Initialize a new workspace.

```bash
research init ~/my-workspace             # Specific location
research init                            # Default: ~/.research-workspace
research init --name "Trading Research"  # Custom name
research init --force                    # Overwrite existing
```

### `research ingest <action>`

Process inbox files into catalog entries.

```bash
research ingest list                     # List inbox contents
research ingest process                  # Process all inbox files
research ingest process --dry-run        # Preview without changes
research ingest process --file paper.pdf # Process specific file
```

**Features:**
- Recursive scanning of inbox subdirectories
- Content hashing to detect duplicates
- Preserves subdirectory structure in destination
- Automatic categorization (indicator, strategy, idea, etc.)

**File destinations:**
- **catalog/sources/** - Files that created catalog entries
- **reviewed/** - Processed but skipped files (purgeable)

### `research catalog <action>`

Manage your research catalog.

```bash
research catalog list                    # List all entries
research catalog list --type indicator   # Filter by type
research catalog list --status VALIDATED # Filter by status
research catalog show IND-002            # Show entry details
research catalog stats                   # Show statistics
research catalog search "momentum"       # Search entries
```

**Entry types:** `indicator`, `strategy`, `idea`, `learning`, `tool`, `data`

**Entry statuses:** `UNTESTED`, `IN_PROGRESS`, `VALIDATED`, `CONDITIONAL`, `INVALIDATED`, `BLOCKED`

### `research validate <action>`

Run the validation pipeline.

```bash
research validate start IND-002          # Start validation
research validate status IND-002         # Check status
research validate audit IND-002          # Run data audit
research validate run IND-002            # Run next step
research validate list                   # List all validations
```

**Validation Pipeline Stages:**
1. **HYPOTHESIS** - Define and lock your testable hypothesis
2. **DATA_AUDIT** - Verify data availability and quality (MANDATORY)
3. **IS_TESTING** - Run in-sample backtest (15+ years)
4. **STATISTICAL** - Verify statistical significance
5. **REGIME** - Analyze performance by market regime
6. **OOS_TESTING** - Run out-of-sample backtest (ONE SHOT - no retries!)
7. **DETERMINATION** - Make final decision (VALIDATED/CONDITIONAL/INVALIDATED)

### `research data <action>`

Manage data sources.

```bash
research data list                       # List all data sources
research data show mcclellan_oscillator  # Show source details
research data check spy_prices breadth   # Check availability
```

### `research combine <action>`

Generate and prioritize indicator + strategy combinations.

```bash
research combine generate                # Generate all combinations
research combine list --top 10           # Show top 10 by priority
research combine prioritize              # Recalculate priorities
research combine next --count 5          # Get next 5 to test
```

### `research ideate`

Generate new strategy ideas using AI personas.

```bash
research ideate                          # Run all 3 personas
research ideate --count 2                # Generate 2 ideas per persona
research ideate --add-to-catalog         # Auto-add generated ideas to catalog
```

**Personas:**
- **edge-hunter** - Finds micro-structure and timing edges
- **macro-strategist** - Cross-asset, regime-aware themes
- **quant-archaeologist** - Rehabilitates failed approaches with modern techniques

Ideas are generated based on your catalog's validated/invalidated entries and available data sources.

### `research analyze <action>`

Run multi-persona analysis on validation results.

```bash
research analyze run IND-002             # Full analysis
research analyze run IND-002 --persona contrarian  # Specific persona
research analyze show IND-002            # Show results
```

**Personas:**
- **momentum-trader** - Trend-following perspective
- **risk-manager** - Risk and drawdown focus
- **quant-researcher** - Statistical rigor
- **mad-genius** - Unconventional, creative insights
- **contrarian** - Challenges consensus
- **report-synthesizer** - Integrates all perspectives

### `research synthesize`

Run cross-strategy synthesis with an expert panel. Analyzes all validated strategies to identify portfolio construction opportunities, instrument expansion, and creative combinations.

```bash
research synthesize                      # Full synthesis with all personas
research synthesize --dry-run            # Preview what would be analyzed
research synthesize --persona creative-maverick  # Run single persona
research synthesize --create-entries     # Create catalog entries from recommendations
research synthesize --top 25             # Limit to top 25 by Sharpe
research synthesize --min-sharpe 0.5     # Filter by minimum Sharpe
```

**Personas:**
- **portfolio-architect** - Correlation, allocation, portfolio construction
- **instrument-specialist** - Options, futures, ETF opportunities
- **data-integrator** - Alternative data enhancement
- **regime-strategist** - Market regime analysis
- **creative-maverick** - Unconventional ideas and combinations
- **synthesis-director** - Integrates all perspectives

**Output:**
- Markdown report saved to `synthesis/` directory
- Optional: New catalog entries created from recommendations

### `research migrate <action>`

Import from external sources.

```bash
research migrate master-index /path/to/MASTER_INDEX.json
research migrate master-index /path/to/MASTER_INDEX.json --dry-run
```

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Research Validation Pipeline                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────┐    ┌─────────┐    ┌──────────┐    ┌─────────────┐               │
│  │ SOURCES │───▶│  INBOX  │───▶│  INGEST  │───▶│   CATALOG   │               │
│  │ Papers  │    │ Drop    │    │ Extract  │    │ IND-001     │               │
│  │ Ideas   │    │ files   │    │ metadata │    │ STRAT-002   │               │
│  │ Data    │    │ here    │    │ via LLM  │    │ IDEA-003    │               │
│  └─────────┘    └─────────┘    └──────────┘    └──────┬──────┘               │
│                                                       │                       │
│       ┌─────────────────────────────────────────────┬─┴───────┐               │
│       ▼                                             ▼         ▼               │
│  ┌─────────┐                                  ┌──────────┐  ┌───────┐         │
│  │ IDEATE  │                                  │ COMBINE  │  │VALIDATE│        │
│  │ 3 AI    │                                  │ Generate │  │Pipeline│        │
│  │ personas│──────────────────────────────────▶│ IND+STRAT│──▶│ 7 gates│        │
│  └─────────┘                                  └──────────┘  └───┬───┘         │
│                                                                 │              │
│           ┌─────────────────────────────────────────────────────┘              │
│           ▼                                                                    │
│      ┌──────────────────────────────────────────────────────────┐             │
│      │  DETERMINATION:  VALIDATED  |  CONDITIONAL  |  INVALIDATED │            │
│      └──────────────────────────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### Workspace vs Application

The **application** (this tool) and your **workspace** (your data) are completely separate:

- **Application**: Install once, upgrade anytime. Your data is untouched.
- **Workspace**: Your catalog, validations, data registry. Back this up.

This means you can:
- Reinstall the tool without losing your work
- Give the tool to 100 people - each creates their own workspace
- Upgrade to a new version without touching your data
- Back up just your workspace directory

### The Validation Pipeline

Every validation follows the same rigorous process:

```
HYPOTHESIS → DATA_AUDIT → IS_TESTING → STATISTICAL → REGIME → OOS → DETERMINATION
     │            │           │            │          │       │
     │            │           │            │          │       └─▶ VALIDATED
     │            │           │            │          │           CONDITIONAL
     │            │           │            │          │           INVALIDATED
     │            │           │            │          │
     │            │           │            │          └─▶ (skip if IS fails)
     │            │           │            │
     │            │           │            └─▶ FAIL if p > 0.01/N (Bonferroni)
     │            │           │
     │            │           └─▶ FAIL if alpha < 1% or Sharpe improvement < 0.10
     │            │
     │            └─▶ FAIL if lookahead bias, wrong columns, insufficient data
     │
     └─▶ REJECT if not falsifiable, no clear hypothesis
```

**Key rules:**
- Each gate must pass before proceeding
- Parameters are locked before testing begins
- **OOS is ONE SHOT** - no retries, no adjustments after seeing results
- This prevents p-hacking and curve fitting

### Data Resolution

When a strategy requires data (e.g., `vix_index`, `spy_prices`), the system resolves it through multiple layers:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Requirement Resolution                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  "vix_index"  ──┬─▶  Registry Lookup (by ID)  ──┬──▶ FOUND      │
│                 │                               │                │
│                 └─▶  Registry Lookup (by alias) ─┘               │
│                 │                                                │
│                 └─▶  QC Native Aliases (150+)  ─────▶ VIX       │
│                 │    - vix_index → VIX                          │
│                 │    - eur_usd → EURUSD                         │
│                 │    - sp500_futures → ES                       │
│                 │                                                │
│                 └─▶  QC Native Patterns ────────────▶ AUTO      │
│                      - spy_prices → SPY                         │
│                      - aapl_data → AAPL                         │
│                                                                  │
│  Resolution fails only if no match at any level                 │
└─────────────────────────────────────────────────────────────────┘
```

**Semantic aliases automatically resolve to QC Native data:**

| Category | Examples | Resolves To |
|----------|----------|-------------|
| Cash Indices | `vix_index`, `sp500_index`, `dollar_index` | VIX, SPX, DXY |
| Forex | `eur_usd`, `gbp_usd`, `usd_jpy` | EURUSD, GBPUSD, USDJPY |
| Crypto | `bitcoin`, `ethereum` | BTCUSD, ETHUSD |
| ETFs | `sp500_etf`, `gold_etf`, `vix_etf` | SPY, GLD, VXX |
| Futures | `sp500_futures`, `gold_futures`, `oil_futures` | ES, GC, CL |
| Sectors | `technology_etf`, `financials_etf` | XLK, XLF |

**Data tiers (in resolution order):**

1. **QC Native** - QuantConnect built-in data (always preferred)
2. **QC Object Store** - Data you've uploaded to QC cloud
3. **Internal Purchased** - Paid data you own
4. **Internal Curated** - Free data you've validated
5. **Internal Experimental** - Unverified data (use with caution)

### Statistical Thresholds

| Metric | Threshold | Description |
|--------|-----------|-------------|
| p-value | < 0.01 | Single test significance |
| p-value (corrected) | < 0.01/N | Multiple tests (Bonferroni) |
| Alpha | > 1% | Minimum annualized alpha |
| Sharpe improvement | > 0.10 | For filter tests vs baseline |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RESEARCH_WORKSPACE` | Path to your workspace | `~/.research-workspace` |

## Configuration

The workspace `config.json` contains your settings:

```json
{
  "name": "My Research",
  "qc_user_id": "",
  "qc_api_token": "",
  "qc_organization_id": "",
  "min_is_years": 15,
  "min_oos_years": 4,
  "base_alpha": 0.01,
  "min_sharpe_improvement": 0.10,
  "min_alpha_threshold": 0.01
}
```

### QuantConnect Credentials

QC credentials are resolved in this order:

1. **Workspace config** - If `qc_user_id` and `qc_api_token` are set in `config.json`, those are used
2. **Lean CLI** - Falls back to `~/.lean/credentials` if available (auto-detected)

If you have Lean CLI configured, you don't need to duplicate credentials in your workspace config.

## Workspace Structure

```
~/my-research/
├── config.json               # Your settings
├── inbox/                    # Drop files here to process
│   └── papers/               # Subdirectories preserved
├── reviewed/                 # Processed but not cataloged (purgeable)
│   └── papers/               # Subdirectory structure preserved
├── catalog/
│   ├── index.json            # Quick-lookup index
│   ├── entries/              # One JSON file per entry
│   │   ├── IND-001.json
│   │   ├── IND-002.json
│   │   └── STRAT-001.json
│   └── sources/              # Original files that created entries
│       └── papers/           # Subdirectory structure preserved
│           └── 20251223_a1b2c3d4_strategy.pdf
├── data-registry/
│   ├── registry.json         # Data source definitions
│   └── sources/              # Local data files
├── validations/
│   └── IND-002/              # One folder per validation
│       ├── metadata.json
│       ├── hypothesis.json
│       ├── data_audit.json
│       ├── is_test/
│       ├── oos_test/
│       └── determination.json
└── combinations/
    └── matrix.json           # Generated combinations
```

**File naming in sources/ and reviewed/:**
- Format: `{timestamp}_{hash8}_{original_name}`
- Example: `20251223_a1b2c3d4_strategy.pdf`
- Timestamp ensures uniqueness, hash detects duplicates

## Design Principles

1. **Code over context** - Deterministic scripts do the testing, not LLM judgment
2. **Separation of concerns** - Application code separate from user data
3. **Schema enforcement** - JSON Schema validation for all data structures
4. **Mandatory gates** - No skipping steps, enforced by code
5. **Reproducibility** - Every artifact self-contained and re-runnable
6. **Audit trail** - Every action logged with provenance

## Troubleshooting

### "Workspace not initialized"

Run `research init` to create a workspace, or set `RESEARCH_WORKSPACE` to point to your existing workspace.

```bash
export RESEARCH_WORKSPACE=~/my-research
research catalog list
```

### "Data source not found"

Add the data source to your `data-registry/registry.json` or check that the ID matches exactly.

### "Entry not found"

Check `research catalog list` to see available entries and their IDs.

## Getting Help

```bash
research --help                    # General help
research <command> --help          # Command-specific help
research validate --help           # Validation help
```

## License

MIT
