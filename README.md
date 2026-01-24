# Research-Kit V4

A structured workflow for ingesting, organizing, and validating trading strategy research.

## What This Tool Does

Research-Kit V4 helps you:

1. **Ingest research** - Drop transcripts, papers, and notes into your inbox
2. **Verify strategies** - Check for look-ahead bias, survivorship bias, and other issues
3. **Validate strategies** - Apply validation gates (Sharpe ratio, max drawdown, win rate)
4. **Extract learnings** - Document what worked and what didn't for future reference
5. **Track progress** - View your workspace status, list strategies, and see detailed information

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Quick Start

### 1. Install

**From local clone:**

```bash
git clone https://github.com/extremevalue/research-kit.git
cd research-kit

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Or with uv
uv sync
source .venv/bin/activate
```

**From git (once published):**

```bash
pip3 install git+https://github.com/extremevalue/research-kit.git
```

> **Note:** If you see "externally managed environment" error on macOS, use `uv` or create a virtual environment first.

### 2. Initialize a V4 Workspace

```bash
# Create a new V4 workspace
research init --v4 ~/my-research
cd ~/my-research
```

This creates:
```
~/my-research/
├── research-kit.yaml     # Configuration
├── inbox/                # Drop files here to ingest
├── strategies/
│   ├── pending/          # Newly ingested, awaiting validation
│   ├── validated/        # Passed validation
│   ├── invalidated/      # Failed validation
│   └── blocked/          # Missing data dependencies
├── validations/          # Validation results
├── learnings/            # Extracted learnings
├── ideas/                # Strategy ideas
├── archive/              # Archived/rejected items
└── logs/                 # Daily rotating logs
```

### 3. Add Files to Inbox

Drop research files into the `inbox/` folder:

```bash
cp ~/Downloads/strategy_transcript.txt inbox/
```

### 4. Ingest Research

```bash
# Process all files in inbox
research v4-ingest --force

# Preview what would happen (no changes made)
research v4-ingest --force --dry-run
```

### 5. View Your Strategies

```bash
# Check workspace status
research v4-status

# List all strategies
research v4-list

# View strategy details
research v4-show STRAT-001
```

## Complete Example Workflow

```bash
# 1. Clone and install
git clone https://github.com/extremevalue/research-kit.git
cd research-kit
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. Initialize workspace
research init --v4 ~/trading-research
cd ~/trading-research

# 3. Add a file to inbox
cat > inbox/volatility_strategy.txt << 'EOF'
PODCAST TRANSCRIPT: Volatility Trading

Host: Tell us about your VIX strategy.

Trader: When VIX spikes above 25, I wait for it to drop back below 20,
then buy SPY. Entry is when VIX crosses below its 20-day moving average.
I use a trailing stop of 5% and exit if VIX goes above 30 again.
Position size is 10% of portfolio. Sharpe ratio has been around 1.2.
EOF

# 4. Ingest the file
research v4-ingest --force

# 5. View the strategy
research v4-show STRAT-001

# 6. Run verification tests
research v4-verify STRAT-001

# 7. Generate backtest config (for external backtesting)
research v4-validate STRAT-001 --generate-config

# 8. After running backtest externally, apply validation gates
cat > backtest_results.json << 'EOF'
{"sharpe_ratio": 1.5, "max_drawdown": 0.15, "win_rate": 0.55}
EOF
research v4-validate STRAT-001 --results backtest_results.json

# 9. Extract learnings
research v4-learn STRAT-001

# 10. Generate new ideas based on what you learned
research v4-ideate

# 11. Check final status
research v4-status
```

## Commands Reference

### `research init --v4 [path]`

Initialize a new V4 workspace.

```bash
research init --v4                      # Default: ~/.research-workspace-v4
research init --v4 ~/my-workspace       # Specific location
research init --v4 --force              # Reinitialize existing
```

### `research v4-status`

Show workspace dashboard with strategy counts, inbox status, and suggested next actions.

```bash
research v4-status
research v4-status --workspace ~/my-workspace
```

### `research v4-ingest [file]`

Process inbox files into strategy documents.

```bash
research v4-ingest --force              # Process all inbox files
research v4-ingest --force --dry-run    # Preview without changes
research v4-ingest --force file.txt     # Process specific file
```

**What happens during ingest:**
1. File content is read from inbox
2. Strategy document is created with extracted metadata
3. Original file is archived

### `research v4-list`

List strategies with optional filtering.

```bash
research v4-list                        # All strategies
research v4-list --status pending       # Filter by status
research v4-list --tags momentum        # Filter by tags
research v4-list --format json          # JSON output
```

**Output columns:** ID, Name, Status, Created

### `research v4-show <strategy_id>`

Display full strategy details.

```bash
research v4-show STRAT-001              # Human-readable format
research v4-show STRAT-001 --format yaml  # Raw YAML
research v4-show STRAT-001 --format json  # JSON output
```

### `research v4-verify <strategy_id>`

Run verification tests to check for common issues before backtesting.

```bash
research v4-verify STRAT-001            # Run all verification tests
research v4-verify STRAT-001 --dry-run  # Preview without saving results
```

**Tests include:**
- `look_ahead_bias` - Check for future information leakage
- `survivorship_bias` - Check for survivorship bias in universe
- `position_sizing` - Validate position sizing is defined
- `data_requirements` - Verify data requirements are specified
- `entry_defined` - Check entry conditions are complete
- `exit_defined` - Check exit conditions include stop loss
- `universe_defined` - Verify universe is properly defined

### `research v4-validate <strategy_id>`

Run validation with configurable gates after backtesting.

```bash
# Generate backtest configuration
research v4-validate STRAT-001 --generate-config

# Apply validation gates to backtest results
research v4-validate STRAT-001 --results backtest_results.json
```

**Validation gates (configurable in research-kit.yaml):**
- `sharpe_ratio` - Minimum Sharpe ratio (default: 1.0)
- `max_drawdown` - Maximum drawdown (default: 25%)
- `win_rate` - Minimum win rate (default: 40%)

**Results file format (JSON):**
```json
{
  "sharpe_ratio": 1.5,
  "max_drawdown": 0.15,
  "win_rate": 0.55
}
```

### `research v4-learn <strategy_id>`

Extract learnings from verification and validation results.

```bash
research v4-learn STRAT-001             # Extract and save learnings
research v4-learn STRAT-001 --dry-run   # Preview without saving
```

**Learnings include:**
- Verification test outcomes and recommendations
- Validation gate results
- Strategy definition quality assessment
- Actionable insights for improvement

### `research v4-ideate`

Generate new strategy ideas based on existing strategies and learnings.

```bash
research v4-ideate                      # Generate up to 5 ideas
research v4-ideate --max-ideas 10       # Generate up to 10 ideas
research v4-ideate --dry-run            # Preview without saving
```

**Ideas are generated by:**
- Creating variations of existing strategies (timeframe, instrument, filter, sizing)
- Addressing issues found in validation failures
- Suggesting generic patterns if no strategies exist

## Workspace Structure

```
~/my-research/
├── .state/                   # Internal state (counters, locks)
├── research-kit.yaml         # Configuration
├── inbox/                    # Drop files here
├── strategies/
│   ├── pending/              # STRAT-001.yaml, STRAT-002.yaml, ...
│   ├── validated/
│   ├── invalidated/
│   └── blocked/
├── validations/              # Walk-forward validation results
├── learnings/                # Extracted learnings
├── ideas/                    # IDEA-001.yaml, ...
├── personas/                 # AI persona configurations
├── archive/                  # Archived files
│   ├── processed/            # Files that were successfully ingested
│   └── rejected/             # Files that were rejected
└── logs/                     # Daily rotating logs
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RESEARCH_WORKSPACE` | Path to V4 workspace | `~/.research-workspace-v4` |

## Troubleshooting

### "V4 workspace not initialized"

Run `research init --v4` to create a workspace:

```bash
research init --v4 ~/my-research
cd ~/my-research
research v4-status
```

### "Strategy not found"

Check available strategies:

```bash
research v4-list
```

## Advanced: LLM-Based Extraction

For richer metadata extraction, you can configure an Anthropic API key:

```bash
cd ~/my-research
cp .env.template .env
# Edit .env and add: ANTHROPIC_API_KEY=sk-ant-...
```

Then run ingest without `--force`:

```bash
research v4-ingest  # Uses LLM for metadata extraction
```

This enables:
- Quality scoring (specificity 0-8, trust 0-100)
- Red flag detection
- Automatic accept/reject decisions

## Getting Help

```bash
research --help                     # General help
research v4-ingest --help           # Command help
research v4-verify --help
research v4-validate --help
research v4-learn --help
research v4-ideate --help
research v4-list --help
research v4-show --help
research v4-status --help
```

## License

MIT
