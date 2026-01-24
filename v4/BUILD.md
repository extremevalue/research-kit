# Research-Kit V4: Build Guide

**For:** Claude Code in a fresh session
**Created:** 2026-01-24
**Repo:** `extremevalue/research-kit`

---

## Quick Start

This document tells you everything you need to build research-kit v4. Read this first, then reference the other docs as needed.

### Reference Documents

| Document | Purpose |
|----------|---------|
| `VISION.md` | Why this exists, user objectives |
| `ARCHITECTURE.md` | System architecture, data flows |
| `SCHEMA.md` | Strategy document YAML schema (Pydantic models) |
| `TEST-CASES.md` | 5 complex strategies + 6 ingestion filter tests |
| `IMPLEMENTATION-PLAN.md` | Detailed phase breakdown |
| `DESIGN-DECISIONS.md` | All architectural decisions made |
| `PERSONA-*.md` | Background context (for Learn phase personas) |

---

## Project Overview

**What it does:** Ingest trading strategies from various sources, validate them through backtesting, learn from results, and generate new ideas.

**User's objectives:**
1. Make money from trading strategies
2. Don't lose money
3. Figure out which strategies work from a mountain of maybes

**Core insight:** Most strategies (90-95%) are noise. The system filters noise early and validates the rest rigorously.

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE (Orchestrator)                    │
│  - Receives user commands                                        │
│  - Spawns sub-agents for LLM-heavy work                         │
│  - Calls CLI for mechanical operations                          │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Sub-Agent:    │  │   Sub-Agent:    │  │   Sub-Agent:    │
│   Extraction    │  │   Rationale     │  │   Personas      │
│                 │  │   Research      │  │   (parallel)    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CLI (research command)                      │
│  Mechanical operations only:                                     │
│  - File I/O (read/write YAML)                                   │
│  - Schema validation (Pydantic)                                  │
│  - Quality scoring calculations                                  │
│  - LEAN CLI execution                                           │
│  - Status queries                                                │
└─────────────────────────────────────────────────────────────────┘
```

**Key principle:** Sub-agents handle LLM work, CLI handles deterministic operations.

---

## Three Build Phases

Build in this order. Each phase must be independently testable before moving on.

### Phase 1: Ingestion

**Goal:** Extract strategies from source files with quality filtering

**Commands:**
```bash
research ingest <file>              # Extract strategy from source file
research ingest <file> --dry-run    # Show what would be extracted, don't save
research list                       # List all strategies
research show <id>                  # Show strategy details
```

**What the CLI does:**
1. Read source file from inbox
2. Call sub-agent for extraction (LLM work)
3. Call sub-agent for rationale research if needed (LLM work)
4. Calculate specificity score (0-8)
5. Calculate trust score (0-100)
6. Detect red flags (hard/soft)
7. Check for duplicates/variants
8. Write strategy YAML to /strategies
9. Return result (accept/archive/reject)

**Sub-agent responsibilities:**
- Extract strategy components from source text
- Fill gaps (missing parameters)
- Research rationale if not stated (check factors, academic literature)
- Track provenance (source_stated | source_enhanced | inferred | unknown)
- Detect red flags

**Acceptance criteria:**
- [ ] `research ingest <file>` produces valid strategy YAML
- [ ] Specificity score calculated correctly
- [ ] Trust score calculated correctly
- [ ] Hard red flags cause rejection
- [ ] Soft red flags produce warnings
- [ ] Strategies with unknown rationale are NOT rejected
- [ ] Duplicates are blocked
- [ ] All 6 ingestion test cases pass (see TEST-CASES.md)

---

### Phase 2: Validation

**Goal:** Run strategies through LEAN backtesting with walk-forward validation

**Commands:**
```bash
research verify <id>                # Run verification tests only
research validate <id>              # Full validation (verify + backtest)
research validate <id> --cloud      # Use QC cloud instead of local LEAN
research validate <id> --dry-run    # Generate code only, don't run
research validate --all-pending     # Batch validate all pending
```

**What the CLI does:**
1. Load strategy document
2. Run verification tests (look-ahead bias, position sizing, etc.)
3. Generate QuantConnect Python code
4. Execute via LEAN CLI (`lean backtest` or `lean cloud backtest`)
5. Parse results
6. Apply gates (min Sharpe, consistency, max drawdown)
7. Store results in /validations (immutable)
8. Update strategy status

**Verification tests (pre-backtest gate):**
- Look-ahead bias detection
- Position sizing validation
- Data availability check
- Parameter sanity check
- Hardcoded values detection

**Validation gates (configurable in research-kit.yaml):**
```yaml
gates:
  min_sharpe: 0.5
  min_consistency: 0.6      # % of windows profitable
  max_drawdown: 0.30        # 30% max
  min_trades: 30
```

**Walk-forward approach:**
- 12 rolling windows
- Train/test split per window
- Report consistency across windows

**Acceptance criteria:**
- [ ] `research verify <id>` runs all verification tests
- [ ] `research validate <id>` generates valid QC code
- [ ] LEAN CLI integration works (local mode)
- [ ] Walk-forward windows calculated correctly
- [ ] Gates evaluated correctly
- [ ] Results stored immutably in /validations
- [ ] All 5 test strategies validate end-to-end (see TEST-CASES.md)

---

### Phase 3: Ideation

**Goal:** Learn from results, generate new ideas

**Commands:**
```bash
research learn                      # Run persona review on recent results
research learn --strategy <id>      # Review specific strategy
research learnings                  # Show all learnings
research ideas                      # Show idea backlog
research approve <idea-id>          # Convert idea to pending strategy
```

**What the CLI does:**
1. Load validation results
2. Spawn persona sub-agents (can run in parallel)
3. Each persona reviews and provides insights
4. Extract learnings (append to /learnings)
5. Generate new ideas (add to /ideas)
6. Track lineage when ideas approved

**Personas (defined in /personas/*.md):**
- Veteran Quant
- Skeptical Statistician
- Experienced Trader
- First Principles Thinker
- Startup CTO
- Failure Analyst
- Software Architect

**Acceptance criteria:**
- [ ] `research learn` spawns persona sub-agents
- [ ] Personas can run in parallel
- [ ] Learnings extracted and stored
- [ ] Ideas generated with lineage tracking
- [ ] `research approve` converts idea to strategy
- [ ] Lineage correctly recorded

---

## Project Structure

```
research-kit/
├── pyproject.toml              # Package config, dependencies
├── src/
│   └── research_kit/
│       ├── __init__.py
│       ├── cli.py              # Typer CLI entry point
│       ├── commands/           # CLI command implementations
│       │   ├── ingest.py
│       │   ├── validate.py
│       │   ├── learn.py
│       │   └── status.py
│       ├── schema/             # Pydantic models
│       │   ├── strategy.py
│       │   ├── validation.py
│       │   └── learning.py
│       ├── scoring/            # Quality scoring
│       │   ├── specificity.py
│       │   ├── trust.py
│       │   └── red_flags.py
│       ├── validation/         # Validation logic
│       │   ├── verification.py # Pre-backtest tests
│       │   ├── codegen.py      # QC code generation
│       │   ├── lean.py         # LEAN CLI wrapper
│       │   └── gates.py        # Gate evaluation
│       └── utils/
│           ├── config.py       # Config loading
│           ├── storage.py      # YAML file I/O
│           └── similarity.py   # Duplicate detection
└── tests/
    ├── test_schema.py
    ├── test_scoring.py
    ├── test_verification.py
    └── test_ingestion_cases.py
```

---

## Workspace Structure

When user initializes workspace:

```
~/research-workspace/
├── .env                        # Secrets
│   LEAN_DATA_PATH=/path/to/lean/data
│   LEAN_ENGINE_IMAGE=quantconnect/lean:latest
│   QC_USER_ID=12345
│   QC_API_TOKEN=xxxxx
│   ANTHROPIC_API_KEY=xxxxx
│
├── research-kit.yaml           # Config
│   gates:
│     min_sharpe: 0.5
│     min_consistency: 0.6
│     max_drawdown: 0.30
│     min_trades: 30
│   verification:
│     enabled_tests: [look_ahead, position_sizing, data_availability]
│   scoring:
│     specificity_threshold: 4
│     trust_threshold: 50
│
├── inbox/                      # Source files to ingest
├── strategies/                 # Strategy documents (YAML)
├── validations/                # Validation results (immutable)
├── learnings/                  # Extracted learnings
├── ideas/                      # Generated ideas
├── personas/                   # Persona definitions
├── archive/                    # Rejected/archived strategies
└── logs/                       # Daily rotating logs
```

---

## Dependencies

```toml
[project]
dependencies = [
    "typer>=0.9.0",             # CLI framework
    "pydantic>=2.0",            # Schema validation
    "pyyaml>=6.0",              # YAML parsing
    "rich>=13.0",               # Pretty CLI output
    "python-dotenv>=1.0",       # .env loading
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
]
```

**External requirements:**
- LEAN CLI (`pip install lean`)
- Docker (for local LEAN execution)
- Historical data (downloaded via LEAN)

---

## Strategy ID Generation

- Format: `STRAT-{NNN}` (zero-padded to 3 digits)
- Ideas: `IDEA-{NNN}`
- Stored in workspace config: `next_strategy_id: 43`
- Sequential, never reused

---

## Red Flag Reference

### Hard Rejection (auto-reject)

| Flag | Condition |
|------|-----------|
| `sharpe_above_3` | Claimed Sharpe > 3.0 (non-HFT) |
| `no_losing_periods` | "Never had a losing month/year" |
| `works_all_conditions` | "Works in all market conditions" |
| `author_selling` | Author selling courses/signals |
| `excessive_parameters` | More than 5 tunable parameters |

### Soft Warning (proceed with flag)

| Flag | Condition |
|------|-----------|
| `unknown_rationale` | No rationale found after research |
| `no_transaction_costs` | Costs not discussed |
| `single_market` | Only one geography tested |
| `single_regime` | Only bull market tested |
| `small_sample` | < 30 observations |
| `high_leverage` | Requires > 3x leverage |
| `crowded_factor` | Well-known factor |

**Key rule:** Unknown rationale is NOT a hard rejection. Sub-agents infer, validation tests.

---

## Test Strategy

### Phase 1 Tests
1. All 6 ingestion test cases (see TEST-CASES.md)
2. Specificity scoring accuracy
3. Trust scoring accuracy
4. Red flag detection
5. Duplicate detection

### Phase 2 Tests
1. Verification tests catch known bad patterns
2. Code generation produces valid QC Python
3. LEAN CLI integration works
4. Gate evaluation is correct
5. All 5 test strategies validate end-to-end

### Phase 3 Tests
1. Personas run in parallel
2. Learnings are extracted
3. Ideas are generated
4. Lineage is tracked

---

## Build Order

1. **Foundation (do first)**
   - Pydantic schema models (validate against 5 test strategies)
   - Config loading
   - CLI skeleton with `--help`
   - Logging setup

2. **Phase 1: Ingestion**
   - Quality scoring
   - Red flag detection
   - Storage (YAML read/write)
   - Duplicate detection
   - Test: 6 ingestion test cases

3. **Phase 2: Validation**
   - Verification tests
   - QC code generation
   - LEAN CLI wrapper
   - Gate evaluation
   - Test: 5 test strategies end-to-end

4. **Phase 3: Ideation**
   - Persona framework
   - Learning extraction
   - Idea generation
   - Lineage tracking
   - Test: Full flow

5. **Hardening**
   - Error handling
   - Edge cases
   - Documentation

---

## GitHub Workflow

1. Create issues for each major component
2. Work on feature branches
3. Write tests before/with code
4. PR for review
5. Merge to main

```bash
git checkout -b feat/schema-models
# ... work ...
git commit -m "Add Pydantic schema models for strategy documents"
git push origin feat/schema-models
# Create PR, review, merge
```

---

## Success Criteria

V4 is complete when:

1. [ ] All 5 test strategies ingest, verify, and validate end-to-end
2. [ ] All 6 ingestion test cases pass
3. [ ] Personas generate useful learnings and ideas
4. [ ] System handles errors gracefully
5. [ ] Documentation is complete

---

## Notes for Claude Code

- **Don't over-engineer.** Build the simplest thing that works.
- **Test each phase** before moving on.
- **Sub-agents do LLM work.** CLI does file I/O and calculations.
- **YAML is the storage format.** Human-readable, git-friendly.
- **Unknown rationale is OK.** Sub-agents infer, validation tests.
- **The market doesn't care about our explanations.** Validation is the real test.
