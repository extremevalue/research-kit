# Research Validation System - User Journey

The complete workflow from idea discovery to validated research.

---

## Core Philosophy

1. **Structured, repeatable testing** - Every idea goes through the same rigorous pipeline
2. **Reproducible results** - Anyone can re-run your exact test and get the same outcome
3. **Nothing thrown away** - Failed tests generate learnings; learnings spawn new ideas
4. **Growing knowledge base** - The catalog is a tree of tested research, not a pass/fail graveyard
5. **Multiple perspectives** - Every result reviewed through different lenses to find blind spots

---

## Actors

- **User**: Trader/researcher validating trading ideas
- **Claude**: AI assistant (restricted to CLI commands only via skill)
- **System**: The `research` CLI and infrastructure

---

## Phase 1: Setup

```bash
# Install (replace <repo> with the actual repository URL)
git clone <repo> && cd research-system
python3 -m venv .venv && source .venv/bin/activate
pip install jsonschema
chmod +x research

# Initialize workspace
research init ~/my-research --name "My Trading Research"
```

Creates:
```
~/my-research/
├── inbox/          # Drop files here
├── archive/        # Processed files
├── catalog/        # Research entries
├── data-registry/  # Data sources
├── validations/    # Test results
└── config.json     # Settings
```

---

## Phase 2: Bulk Ingestion

### User drops files in inbox

Any number of files - 1 or 1000. Supported formats: HTML, PDF, markdown, Python, text.

```
inbox/
├── reddit-post.html
├── research-paper.pdf
├── indicator-code.py
├── trading-blog-1.html
├── trading-blog-2.html
└── ... (any number of files)
```

### User triggers ingestion

```
User: "I put a bunch of files in the inbox. Can you process them?"

Claude: research ingest process
```

### Internal process

Each file goes through a two-stage pipeline:

**Stage 1: Haiku Extraction (LLM)**
- Reads raw file content
- Extracts structured metadata: name, type, summary, data requirements, tags
- Outputs validated JSON

**Stage 2: Deterministic Processing (Python)**
- Validates metadata against schema
- Checks data requirements against QC Native reference + user registry
- Sets status: UNTESTED (all data available) or BLOCKED (missing data)
- Generates entry ID, writes to catalog, archives source file

### Output

```
Processing inbox (847 files)...

  [1/847] reddit-post.html
    → STRAT-001: SPY Options MA Strategy
    → Status: BLOCKED (missing: abc_indicator)

  [2/847] research-paper.pdf
    → IDEA-001: Volatility Clustering Approach
    → Status: UNTESTED

  [3/847] indicator-code.py
    → IND-001: Custom RSI Variant
    → Status: UNTESTED

  ...

  [847/847] old-blog.html
    → SKIPPED: Could not extract structured data (see errors.log)

Complete: 823 entries created, 24 skipped
```

### Preview mode

```bash
research ingest process --dry-run
```

Shows what would be created without committing.

---

## Phase 3: Resolving Blocked Entries

Entries are BLOCKED when data requirements can't be satisfied.

### Check what's blocked

```bash
research catalog list --status BLOCKED
```

### See why

```bash
research catalog show STRAT-001
```

```json
{
  "status": "BLOCKED",
  "blocked_reason": "Missing data: abc_indicator",
  "data_requirements": [
    {"id": "spy_prices", "available": true, "source": "qc_native"},
    {"id": "abc_indicator", "available": false}
  ]
}
```

### Add missing data

```bash
research data add \
  --id abc_indicator \
  --name "ABC Custom Indicator" \
  --type indicator \
  --tier internal_experimental \
  --path ~/my-research/data/abc_indicator.csv
```

### Unblock

```bash
research validate check STRAT-001
```

```
All data requirements satisfied.
Status: BLOCKED → UNTESTED
```

---

## Phase 4: Validation Pipeline

Seven mandatory stages. No skipping. No shortcuts.

```bash
research validate start STRAT-001
```

### Stage 1: HYPOTHESIS

Lock all parameters BEFORE any testing.

```yaml
Locked:
  hypothesis: "50/200 MA cross generates buy signal for ATM calls"
  parameters: {fast_ma: 50, slow_ma: 200, dte: 30}
  is_period: 2012-01-01 to 2020-12-31
  oos_period: 2021-01-01 to 2024-12-31
  success_criteria: {min_alpha: 1%, max_p_value: 0.01}
```

**Cannot be changed after this point.**

### Stage 2: DATA_AUDIT

Automatic checks:
- ✓ Data available for full period
- ✓ No lookahead bias (T-1 data usage)
- ✓ Column mappings correct
- ✓ Sufficient history for IS/OOS split

Must pass before testing begins.

### Stage 3: IS_TESTING

In-sample backtest on locked date range.

```
Results:
  Trades: 47 | Win rate: 61.7% | Alpha: 3.2% | Sharpe: 0.87

IS_TESTING: PASSED (alpha 3.2% > 1% threshold)
```

### Stage 4: STATISTICAL

Significance testing with Bonferroni correction.

```
Bootstrap p-value: 0.0043
Bonferroni threshold: 0.01/1 = 0.01
Effect size (Cohen's d): 0.72

STATISTICAL: PASSED
```

### Stage 5: REGIME

Performance breakdown by market condition.

```
Bull market:  Alpha 4.8%, p=0.002 ✓
Bear market:  Alpha -0.3%, p=0.34 ✗
High vol:     Alpha 1.1%, p=0.12
Low vol:      Alpha 4.1%, p=0.008 ✓

REGIME: PASSED (conditional - underperforms in bear)
```

### Stage 6: OOS_TESTING

**ONE SHOT. No retries. No adjustments.**

```
⚠️  OUT-OF-SAMPLE TEST IS FINAL
    Parameters locked. Results are final regardless of outcome.
    Continue? [y/N]: y

OOS Results:
  Trades: 19 | Alpha: 2.1% | Sharpe: 0.71
  Decay from IS: Alpha -34%, Sharpe -18%

OOS_TESTING: PASSED (positive edge maintained)
```

### Stage 7: DETERMINATION

Final verdict based on all evidence.

```
STRAT-001: CONDITIONAL

"Statistically significant edge in bull markets.
 Not recommended during bear regimes."
```

---

## Phase 5: Multi-Perspective Review

After validation, five personas analyze the results.

```bash
research analyze run STRAT-001
```

| Persona | Focus | Example Output |
|---------|-------|----------------|
| **Momentum Trader** | Trend-following fit | "Classic signal, options add leverage" |
| **Risk Manager** | Drawdown, tail risk | "22% drawdown concerning, add VIX stop" |
| **Quant Researcher** | Statistical validity | "19 OOS trades is marginal sample" |
| **Contrarian** | Challenge consensus | "Crowded trade, watch for alpha decay" |
| **Synthesizer** | Integrate all views | Final assessment with action items |

---

## Phase 6: Feedback Loop

Persona insights become new catalog entries.

```
Personas suggested 3 improvements:

  1. [RISK-MANAGER] Add VIX > 30 exit rule
  2. [QUANT-RESEARCHER] Test with weekly options
  3. [CONTRARIAN] Monitor for alpha decay

Add to catalog? [1,2,3/none]: 1,2

Created:
  IDEA-001: "STRAT-001 with VIX exit filter" (parent: STRAT-001)
  IDEA-002: "STRAT-001 with weekly options" (parent: STRAT-001)
```

### The catalog grows

```
research catalog list --derived-from STRAT-001

STRAT-001 (CONDITIONAL)
├── IDEA-001 (UNTESTED) - VIX exit filter
├── IDEA-002 (UNTESTED) - Weekly options variant
└── IDEA-003 (UNTESTED) - Bear market hedge
```

Each child can be validated through the same pipeline, potentially spawning its own children. The catalog becomes a tree of tested research with full lineage.

---

## Phase 7: Returning with New Data

Over time, entries accumulate in BLOCKED status waiting for data you don't have. Months later, you acquire new data sources.

### See what's blocked and why

```bash
research catalog list --status BLOCKED --show-missing
```

```
BLOCKED entries (43):

Missing: bloomberg_sentiment (23 entries)
  STRAT-045, STRAT-067, STRAT-089, IDEA-012, ...

Missing: options_flow (12 entries)
  STRAT-102, STRAT-118, IND-034, ...

Missing: crypto_funding_rates (5 entries)
  STRAT-201, STRAT-202, STRAT-203, ...

Missing: cot_data (3 entries)
  STRAT-088, IDEA-056, IDEA-078
```

### Add the new data source

```bash
research data add \
  --id bloomberg_sentiment \
  --name "Bloomberg Market Sentiment" \
  --type sentiment \
  --tier internal_purchased \
  --path ~/my-research/data/bloomberg/sentiment.csv
```

### Bulk unblock

```bash
research validate check-all --status BLOCKED
```

```
Checking 43 BLOCKED entries against data registry...

  STRAT-045: bloomberg_sentiment ✓ → UNBLOCKED
  STRAT-067: bloomberg_sentiment ✓ → UNBLOCKED
  STRAT-089: bloomberg_sentiment ✓ → UNBLOCKED
  ...
  STRAT-102: options_flow ✗ → still BLOCKED
  ...

Summary:
  UNBLOCKED: 23 entries (bloomberg_sentiment now available)
  STILL BLOCKED: 20 entries (still missing data)

Status updated: BLOCKED → UNTESTED for 23 entries
```

### Continue with validation

The 23 unblocked entries are now UNTESTED and ready for the validation pipeline.

```bash
research catalog list --status UNTESTED --unblocked-since 2025-06-18
```

Pick one and validate:

```bash
research validate start STRAT-045
```

**BLOCKED is a parking lot, not a dead end.** Entries wait patiently. One data source can unlock many entries at once.

---

## Reproducibility Guarantees

Anyone can reproduce your results:

| Element | How It's Preserved |
|---------|-------------------|
| Parameters | Locked in hypothesis.json before testing |
| Date ranges | Locked in hypothesis.json |
| Algorithm | Saved in validations/STRAT-001/is_test/main.py |
| Results | Saved in results.json with full metrics |
| Random seeds | Captured if any randomization used |
| Data sources | Recorded with exact paths/versions |
| Timestamps | Every stage transition logged |

**To reproduce:**
1. Read hypothesis.json (exact parameters)
2. Run saved main.py (exact algorithm)
3. Over exact date ranges
4. Get same results

---

## Error Handling

### Ingestion failures

Files that can't be parsed are logged and skipped:

```
[147/1000] corrupt-file.pdf
  → SKIPPED: PDF extraction failed (logged to errors.log)
```

Batch continues. Review errors.log afterward.

### Validation failures

Any stage failure stops the pipeline:

```
Stage 3: IS_TESTING
  Alpha: 0.2% (threshold: 1%)

IS_TESTING: FAILED
Validation stopped. Entry remains IN_PROGRESS.
```

User can:
- Review results and mark INVALIDATED
- Restart with different hypothesis (new validation, not retry)

### Data audit failures

Specific, actionable errors:

```
DATA_AUDIT: FAILED
  ✗ Lookahead bias detected: abc_indicator uses same-day data
  ✗ Insufficient history: options data starts 2015, need 2012

Fix data issues and re-run audit.
```

---

## Enforcement Mechanism

Claude interacts via CLI only. A skill restricts available tools:

```yaml
---
name: research-workflow
allowed-tools: Bash, Read, Glob, Grep
---
```

**Write and Edit are not available.** Claude cannot directly modify catalog, validations, or data-registry files. All changes go through the `research` CLI.

---

## Quick Reference

### Common Commands

```bash
# Ingestion
research ingest list                    # See inbox contents
research ingest process                 # Process all files
research ingest process --dry-run       # Preview only

# Catalog
research catalog list                   # All entries
research catalog list --status BLOCKED  # Blocked only
research catalog list --type indicator  # By type
research catalog show STRAT-001         # Entry details
research catalog list --derived-from X  # Children of X

# Data
research data list                      # All data sources
research data check spy_prices vix      # Check availability
research data add --id X --path Y       # Add source

# Validation
research validate start STRAT-001       # Begin pipeline
research validate status STRAT-001      # Current stage
research validate run STRAT-001         # Run next stage
research validate check STRAT-001       # Re-check blocked

# Analysis
research analyze run STRAT-001          # Multi-persona review
```

### Status Values

| Status | Meaning |
|--------|---------|
| UNTESTED | Ready for validation |
| BLOCKED | Missing data requirements |
| IN_PROGRESS | Validation started |
| VALIDATED | Passed all tests, works broadly |
| CONDITIONAL | Passed with caveats (regime-specific) |
| INVALIDATED | Failed testing |
