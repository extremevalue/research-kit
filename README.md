# Research-Kit V4

A structured workflow for ingesting, organizing, and validating trading strategy research.

## What This Tool Does

Research-Kit V4 helps you:

1. **Ingest research** - Drop transcripts, papers, and notes into your inbox. The system extracts structured strategy information using LLM analysis.
2. **Quality scoring** - Each strategy is scored for specificity (0-8) and trust (0-100), with automatic red flag detection.
3. **Organize strategies** - Strategies are organized by status (pending, validated, invalidated, blocked).
4. **Track progress** - View your workspace status, list strategies, and see detailed information.

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Anthropic API key (for LLM extraction)

## Quick Start

### 1. Install

```bash
# Install with uv (recommended)
uv tool install research-kit --from git+https://github.com/extremevalue/research-kit.git

# Or with pip
pip3 install git+https://github.com/extremevalue/research-kit.git
```

> **Note:** If you see "externally managed environment" error on macOS, use `uv` or create a virtual environment first.

### 2. Initialize a V4 Workspace

```bash
# Create a new V4 workspace
research init --v4 ~/my-research

# Or use the default location
research init --v4
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

### 3. Set Up API Key

Create a `.env` file in your workspace (copy from `.env.template`):

```bash
cd ~/my-research
cp .env.template .env
```

Edit `.env` and add your Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Ingest Research

Drop files into your `inbox/` folder:

```bash
cp ~/Downloads/strategy_transcript.txt ~/my-research/inbox/
```

Then run ingest:

```bash
# Preview what would happen
research v4-ingest --dry-run

# Process all files in inbox
research v4-ingest

# Process a specific file
research v4-ingest ~/my-research/inbox/strategy_transcript.txt
```

### 5. View Your Strategies

```bash
# Check workspace status
research v4-status

# List all strategies
research v4-list

# Filter by status
research v4-list --status pending

# View strategy details
research v4-show STRAT-001

# Export as YAML or JSON
research v4-show STRAT-001 --format yaml
```

## Example Workflow

```bash
# 1. Initialize workspace
research init --v4 ~/trading-research
cd ~/trading-research

# 2. Set up API key
echo "ANTHROPIC_API_KEY=sk-ant-xxx" > .env

# 3. Add a podcast transcript to inbox
cp "Macro Voices Episode 412.txt" inbox/

# 4. Check status - should show 1 file in inbox
research v4-status

# 5. Preview ingestion
research v4-ingest --dry-run

# 6. Run ingestion
research v4-ingest

# 7. Check what was created
research v4-list

# 8. View the strategy details
research v4-show STRAT-001
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
research v4-ingest                      # Process all inbox files
research v4-ingest --dry-run            # Preview without changes
research v4-ingest /path/to/file.txt    # Process specific file
```

**What happens during ingest:**
1. File content is extracted and sent to LLM for analysis
2. Strategy metadata is extracted (name, hypothesis, edge, universe, entry/exit logic)
3. Quality scoring: specificity (0-8) and trust (0-100)
4. Red flag detection (selling author, no transaction costs, etc.)
5. Decision: accept (→ pending), queue, archive, or reject
6. Original file is archived

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

## V4 Strategy Schema

Each strategy document contains:

- **Metadata**: ID, name, created date, status
- **Source**: Type (podcast, paper, etc.), author, track record
- **Hypothesis**: Thesis, type, testable prediction, expected Sharpe
- **Edge**: Category (behavioral, structural), why it exists/persists
- **Universe**: Symbols, filters
- **Entry**: Signal logic, conditions
- **Exit**: Exit paths (stops, targets, reversals)
- **Data Requirements**: Primary data, derived indicators

## Quality Scoring

### Specificity Score (0-8)

Higher is better. Measures how concrete and actionable the strategy is.

| Score | Description |
|-------|-------------|
| 7-8   | Ready to code - all parameters specified |
| 5-6   | Mostly complete - minor gaps |
| 3-4   | Vague - needs development |
| 0-2   | Very vague - just an idea |

### Trust Score (0-100)

Measures credibility of the source and author.

| Score | Description |
|-------|-------------|
| 80+   | Verified fund manager, academic research |
| 60-79 | Practitioner with track record |
| 40-59 | Unknown author, some evidence |
| 0-39  | Unverified, potential conflicts |

### Red Flags

Hard flags (reject):
- Selling something
- Obviously fraudulent claims

Soft flags (queue for review):
- No mention of transaction costs
- Survivorship bias risk
- Lack of out-of-sample testing

## Configuration

The `research-kit.yaml` file in your workspace controls:

```yaml
gates:
  min_specificity: 4        # Minimum specificity to accept
  min_trust: 30             # Minimum trust to accept
  is_years: 15              # In-sample period for validation
  oos_years: 4              # Out-of-sample period

scoring:
  specificity:
    entry_logic: 2          # Weight for entry logic
    exit_logic: 1           # Weight for exit logic
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RESEARCH_WORKSPACE` | Path to V4 workspace | `~/.research-workspace-v4` |
| `ANTHROPIC_API_KEY` | API key for LLM extraction | (required) |

## Workspace Structure

```
~/my-research/
├── .state/                   # Internal state (counters, locks)
├── research-kit.yaml         # Configuration
├── .env                      # API keys (git-ignored)
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
    └── research-kit.2024-01-15.log
```

## Troubleshooting

### "V4 workspace not initialized"

Run `research init --v4` to create a workspace:

```bash
research init --v4 ~/my-research
export RESEARCH_WORKSPACE=~/my-research
research v4-status
```

### "LLM client not available"

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# Or add to .env file in workspace
```

### "Strategy not found"

Check available strategies:

```bash
research v4-list
```

## Getting Help

```bash
research --help                     # General help
research v4-ingest --help           # Command help
research v4-list --help
research v4-show --help
research v4-status --help
```

## License

MIT
