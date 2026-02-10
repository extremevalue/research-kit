# Research-Kit

A structured workflow for ingesting, organizing, and validating trading strategy research.

## What This Tool Does

Research-Kit helps you:

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

**Option A: pipx (recommended — isolates the tool)**
```bash
pipx install git+https://github.com/extremevalue/research-kit.git
```

**Option B: pip from git**
```bash
pip install git+https://github.com/extremevalue/research-kit.git
```

**Option C: local development**
```bash
git clone https://github.com/extremevalue/research-kit.git
cd research-kit
pip install -e .
```

> **Note:** If you see "externally managed environment" error on macOS, use `uv` or create a virtual environment first.

### 2. Initialize a Workspace

```bash
# Create a new workspace
research init ~/my-research
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
research ingest --force

# Preview what would happen (no changes made)
research ingest --force --dry-run
```

### 5. View Your Strategies

```bash
# Check workspace status
research status

# List all strategies
research list

# View strategy details
research show STRAT-001
```

## Complete Example Workflow

```bash
# 1. Clone and install
git clone https://github.com/extremevalue/research-kit.git
cd research-kit
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. Initialize workspace
research init ~/trading-research
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
research ingest --force

# 5. View the strategy
research show STRAT-001

# 6. Run verification tests
research verify STRAT-001

# 7. Generate backtest config (for external backtesting)
research validate STRAT-001 --generate-config

# 8. After running backtest externally, apply validation gates
cat > backtest_results.json << 'EOF'
{"sharpe_ratio": 1.5, "max_drawdown": 0.15, "win_rate": 0.55}
EOF
research validate STRAT-001 --results backtest_results.json

# 9. Extract learnings
research learn STRAT-001

# 10. Generate new ideas based on what you learned
research ideate

# 11. Run cross-strategy synthesis
research synthesize

# 12. Check final status
research status
```

## Commands Reference

### `research init [path]`

Initialize a new workspace.

```bash
research init                        # Default: ~/.research-workspace
research init ~/my-workspace         # Specific location
research init --force                # Reinitialize existing
```

### `research status`

Show workspace dashboard with strategy counts, inbox status, and suggested next actions.

```bash
research status
research status --workspace ~/my-workspace
```

### `research ingest [file]`

Process inbox files into strategy documents.

```bash
research ingest --force              # Process all inbox files
research ingest --force --dry-run    # Preview without changes
research ingest --force file.txt     # Process specific file
```

**What happens during ingest:**
1. File content is read from inbox
2. Strategy document is created with extracted metadata
3. Original file is archived

### `research list`

List strategies with optional filtering.

```bash
research list                        # All strategies
research list --status pending       # Filter by status
research list --tags momentum        # Filter by tags
research list --format json          # JSON output
```

**Output columns:** ID, Name, Status, Created

### `research show <strategy_id>`

Display full strategy details.

```bash
research show STRAT-001              # Human-readable format
research show STRAT-001 --format yaml  # Raw YAML
research show STRAT-001 --format json  # JSON output
```

### `research verify <strategy_id>`

Run verification tests to check for common issues before backtesting.

```bash
research verify STRAT-001            # Verify a single strategy
research verify --all                # Verify all pending strategies
research verify STRAT-001 --dry-run  # Preview without saving results
```

**Tests include:**
- `look_ahead_bias` - Check for future information leakage
- `survivorship_bias` - Check for survivorship bias in universe
- `position_sizing` - Validate position sizing is defined
- `data_requirements` - Verify data requirements are specified
- `entry_defined` - Check entry conditions are complete
- `exit_defined` - Check exit conditions include stop loss
- `universe_defined` - Verify universe is properly defined

### `research validate <strategy_id>`

Run validation with configurable gates after backtesting.

```bash
# Generate backtest configuration
research validate STRAT-001 --generate-config

# Apply validation gates to backtest results
research validate STRAT-001 --results backtest_results.json

# Validate all strategies with verification results
research validate --all --results backtest_results.json
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

### `research learn <strategy_id>`

Extract learnings from verification and validation results.

```bash
research learn STRAT-001             # Extract and save learnings
research learn --all                 # Extract learnings from all strategies
research learn STRAT-001 --dry-run   # Preview without saving
```

**Learnings include:**
- Verification test outcomes and recommendations
- Validation gate results
- Strategy definition quality assessment
- Actionable insights for improvement

### `research ideate`

Generate new strategy ideas using LLM-powered multi-persona synthesis.

```bash
research ideate                       # LLM-powered (3 personas + quality gate)
research ideate --quick               # Template-based (faster, no LLM needed)
research ideate --dry-run             # Preview without saving
```

### `research synthesize`

Run full cross-strategy synthesis with expert panel analysis.

```bash
research synthesize                   # 5 specialist personas + director
```

Requires validated strategies in the workspace.

### `research develop <id>`

Develop vague ideas through a 10-step framework.

```bash
research develop IDEA-001             # Interactive development
research develop IDEA-001 --non-interactive  # Auto-complete with LLM
research develop IDEA-001 --status    # Show progress
research develop IDEA-001 --finalize  # Create strategy from completed development
```

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

## Workspace Location

By default, all commands use `~/.research-workspace`. To use a different location, you have two options:

**Option 1: Set environment variable (recommended)**
```bash
export RESEARCH_WORKSPACE=~/my-research
research status  # Uses ~/my-research
```

**Option 2: Use --workspace flag on each command**
```bash
research status --workspace ~/my-research
research list --workspace ~/my-research
```

> **Note:** Simply `cd`ing into a workspace directory does NOT automatically select it. You must use one of the options above.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RESEARCH_WORKSPACE` | Path to workspace | `~/.research-workspace` |

## Troubleshooting

### "workspace not initialized"

Run `research init` to create a workspace:

```bash
research init ~/my-research
export RESEARCH_WORKSPACE=~/my-research
research status
```

### "Strategy not found"

Check available strategies:

```bash
research list
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
research ingest  # Uses LLM for metadata extraction
```

This enables:
- Quality scoring (specificity 0-8, trust 0-100)
- Red flag detection
- Automatic accept/reject decisions

## Getting Help

```bash
research --help                     # General help
research ingest --help           # Command help
research verify --help
research validate --help
research learn --help
research ideate --help
research list --help
research show --help
research status --help
```

## License

MIT
