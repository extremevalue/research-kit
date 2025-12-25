# Research-Kit Commands

Complete reference for all research-kit CLI commands.

---

## Command Overview

| Command | Purpose | Frequency |
|---------|---------|-----------|
| `research init` | Initialize workspace | Once |
| `research ingest process` | Process inbox files | Occasionally |
| `research data add` | Add custom data | Occasionally |
| `research run` | **The core validation + expert loop** | Daily |
| `research catalog list/show/stats` | Query catalog | As needed |

---

## Setup Commands

### `research init [path]`

Initialize a new workspace.

```bash
research init ~/research-project              # Specific path
research init                                  # Default: ~/.research-workspace
research init --name "Trading Research"        # With custom name
research init --force                          # Overwrite existing
```

**Creates:**
```
workspace/
├── inbox/              # Drop files here
├── catalog/            # Research entries
├── data-registry/      # Data sources
├── validations/        # Test results
└── config.json         # Settings
```

---

## Ingestion Commands (Process 1)

### `research ingest process`

Process all files in inbox into catalog entries.

```bash
research ingest process                        # Process all inbox files
research ingest process --dry-run              # Preview without processing
research ingest process --file paper.pdf       # Process specific file
```

**What happens:**
1. Walk all files (including subfolders)
2. Hash for deduplication
3. Extract metadata via Claude
4. Create catalog entry
5. Move file to archive

### `research ingest list`

Show files in inbox.

```bash
research ingest list
```

---

## Data Management Commands

### `research data list`

Show registered data sources.

```bash
research data list                             # All sources
research data list --available                 # Only available sources
```

### `research data add`

Add custom data to unblock strategies.

```bash
research data add \
  --id nyse_breadth \
  --name "NYSE Breadth Data" \
  --type indicator \
  --path ./breadth-data.csv
```

### `research data check`

Check what data is missing for a strategy.

```bash
research data check STRAT-309
```

---

## The Core Loop (Process 2)

### `research run [ID]`

**This is the main command.** Runs the full validation + expert loop.

```bash
research run                                   # Process all UNTESTED items
research run STRAT-309                         # Process single item
research run --continue                        # Resume interrupted run
```

**What happens for each item:**

```
1. CODE IT
   └── Generate backtest code from hypothesis

2. TEST IT
   ├── Run IS backtest (via lean CLI)
   ├── Check gates (alpha > 0, sharpe, drawdown)
   ├── Run OOS backtest (one shot)
   └── Check OOS gates

3. EXPERT REVIEW
   ├── Risk Manager: "What could blow up?"
   ├── Momentum Trader: "Does this fit market dynamics?"
   ├── Quant Researcher: "Is this statistically robust?"
   ├── Contrarian: "Why might this stop working?"
   └── Ideator: "How do we make this better?"

4. OUTPUT
   ├── Mark item: VALIDATED / INVALIDATED
   └── Add derived ideas to catalog
```

**Example output:**

```
$ research run STRAT-309

STRAT-309: Forex Fandango
──────────────────────────────────────────────────────
Generating backtest code...
Running IS backtest (2015-2020)...

IS Results:
  CAGR: 20.3%  |  Sharpe: 0.66  |  Max DD: -43.2%
  Alpha vs SPY: +4.9%

IS Gates: PASSED

Running OOS backtest (2021-2024)...

OOS Results:
  CAGR: 5.9%   |  Sharpe: 0.20  |  Max DD: -64.4%
  Alpha vs SPY: -9.8%

OOS Gates: FAILED (Sharpe < 0.3, Drawdown > 50%)

Running expert review...

[Risk Manager]
  64% drawdown is catastrophic. TMF (3x bonds) destroyed
  this strategy in 2022 rate hikes. Unacceptable risk.

[Quant Researcher]
  IS/OOS divergence of 14.7% alpha suggests severe
  overfitting to pre-2020 regime.

[Contrarian]
  Bond-equity correlation assumptions broke post-COVID.
  DXY strength no longer predicts equity returns.

[Ideator]
  Try: (1) Remove TMF entirely, (2) Add rate regime filter,
  (3) Test with shorter lookback period.

──────────────────────────────────────────────────────
DETERMINATION: INVALIDATED

Derived ideas added to catalog:
  IDEA-047: Forex Fandango without TMF
  IDEA-048: Forex Fandango with rate regime filter
```

---

## Catalog Query Commands

### `research catalog list`

List catalog entries.

```bash
research catalog list                          # All entries
research catalog list --status UNTESTED        # Filter by status
research catalog list --status BLOCKED         # See what needs data
research catalog list --type strategy          # Filter by type
```

### `research catalog show`

Show entry details.

```bash
research catalog show STRAT-309
```

### `research catalog stats`

Show catalog statistics.

```bash
research catalog stats
```

**Example output:**

```
┌─────────────────────────────────────┐
│ CATALOG STATUS                      │
├─────────────────────────────────────┤
│ VALIDATED      │  12  (24%)         │
│ INVALIDATED    │  28  (56%)         │
│ UNTESTED       │   5  (10%)         │
│ BLOCKED        │   3  (6%)          │
│ IN_PROGRESS    │   2  (4%)          │
├─────────────────────────────────────┤
│ TOTAL          │  50                │
│ DERIVED IDEAS  │  31  (pending)     │
└─────────────────────────────────────┘
```

---

## Status Values

| Status | Meaning |
|--------|---------|
| UNTESTED | Ready for `research run` |
| BLOCKED | Missing data - use `research data add` |
| IN_PROGRESS | Currently being validated |
| VALIDATED | Passed all tests |
| CONDITIONAL | Passed with caveats |
| INVALIDATED | Failed testing |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RESEARCH_WORKSPACE` | Path to workspace | `~/.research-workspace` |

---

## Getting Help

```bash
research --help                    # General help
research run --help                # Run command help
research catalog --help            # Catalog command help
```
