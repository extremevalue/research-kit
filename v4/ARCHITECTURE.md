# Research-Kit V4: Architecture

## Overview

Research-kit is a CLI tool that orchestrates the ingestion, validation, and learning cycle for trading strategies.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           RESEARCH-KIT                                   │
│                                                                          │
│  ┌─────────┐     ┌──────────────┐     ┌──────────┐     ┌─────────┐     │
│  │ INGEST  │ ──▶ │   VALIDATE   │ ──▶ │  LEARN   │ ──▶ │  IDEAS  │     │
│  │         │     │              │     │          │     │         │     │
│  │ Extract │     │ Verify first │     │ Personas │     │ Backlog │     │
│  │ + Dedup │     │ Then QC test │     │ + Learn  │     │ + Approve│    │
│  └─────────┘     └──────────────┘     └──────────┘     └─────────┘     │
│       │                                                      │          │
│       └──────────────────────────────────────────────────────┘          │
│                            (cycle continues)                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Three Flows

### Flow 1: Ingest

```
Source file (podcast, PDF, notes, etc.)
    │
    ▼
Claude sub-agents extract strategies/indicators
    │
    ▼
Fill in gaps (parameters, rules, universe)
    │
    ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INGESTION QUALITY FILTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    │
    ├── Source credibility assessment:
    │   ├── Author track record
    │   ├── Skin in the game?
    │   └── Conflicts of interest?
    │
    ├── Red flag check (HARD REJECT):
    │   ├── Sharpe > 3.0 claimed
    │   ├── Author selling courses
    │   ├── "Works in all conditions"
    │   └── "Never had a losing period"
    │
    ├── Specificity score (0-8):
    │   └── < 4 → Archive (can't test it)
    │
    ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RATIONALE RESEARCH (Infer if not stated)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    │
    ├── Extract stated rationale from source (if any)
    │   │
    │   ├── Rationale clear? → Mark as "source_stated"
    │   │
    │   ├── Rationale partial? → Sub-agent enhances
    │   │   └── Mark as "source_enhanced"
    │   │
    │   └── Rationale absent? → Sub-agent researches:
    │       │
    │       ├── Does strategy match known factor/anomaly?
    │       │   (momentum, value, quality, low-vol, carry, etc.)
    │       │
    │       ├── Does it match structural edge?
    │       │   (index rebalancing, calendar effects, etc.)
    │       │
    │       ├── Can we identify the counterparty?
    │       │
    │       └── Propose rationale with confidence level
    │           ├── Match found → Mark as "inferred" + confidence
    │           └── No match → Mark as "unknown" (still process!)
    │
    ├── Track provenance:
    │   ├── source: stated | enhanced | inferred | unknown
    │   ├── confidence: high | medium | low
    │   ├── factor_alignment: which factor it resembles
    │   └── research_notes: how rationale was determined
    │
    ▼
    NOTE: Strategies with "unknown" rationale are NOT rejected.
          They proceed to validation but with lower trust weighting.
          The market doesn't care about our explanations.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    │
    ▼
Similarity check:
    ├── Duplicate? → Block
    ├── Variant? → Tag as variant, add
    └── New? → Add
    │
    ▼
Strategy document created (status: PENDING)
```

**Key points:**
- **Ingestion filter catches hard red flags** (Sharpe > 3, selling courses, etc.)
- **Specificity filter archives strategies too vague to test** (score < 4)
- **Rationale is inferred if not stated** — don't throw away strategies from inarticulate sources
- **Provenance is tracked** — "stated" vs "enhanced" vs "inferred" vs "unknown"
- **Unknown rationale is NOT a rejection** — validation is the real test
- Strategies with inferred/unknown rationale get lower trust weighting downstream
- Duplicates blocked, variants tagged

### Flow 2: Validate

```
PENDING strategy
    │
    ▼
Data requirements check (do we have what we need?)
    │
    ▼
Verification tests (MANDATORY - CANNOT SKIP):
    ├── Look-ahead bias
    ├── Position sizing
    ├── Data availability
    ├── Parameter sanity
    └── ... (configurable)
    │
    ▼
Pass? ──No──▶ BLOCKED (feedback provided)
    │
   Yes
    │
    ▼
Generate QuantConnect code
    │
    ▼
Submit to QC for walk-forward backtest (12 windows)
    │
    ▼
Apply gates (Sharpe, consistency, drawdown, etc.)
    │
    ▼
Record results (IMMUTABLE)
    │
    ▼
VALIDATED or INVALIDATED
```

**Key points:**
- Verification tests are hard gate — cannot bypass
- Results are immutable once recorded
- Batch processing with stop on catastrophic failure

### Flow 3: Learn

```
VALIDATED/INVALIDATED strategies
    │
    ▼
Persona review (configurable personas):
    ├── Expert Trader
    ├── Statistician
    ├── Risk Manager
    └── ... (defined in YAML)
    │
    ▼
Extract learnings:
    ├── What worked?
    ├── What didn't?
    ├── What patterns emerge?
    └── What could be combined?
    │
    ▼
Store learnings (PERMANENT, append-only)
    │
    ▼
Generate ideas (BACKLOG)
    │
    ▼
Human approves idea → Becomes PENDING strategy → Cycle continues
```

---

## Directory Structure

### Research-Kit (the tool)

```
/path/to/research-kit/
├── research_system/        # Python package
│   ├── cli/                # CLI commands
│   ├── core/               # Core logic
│   ├── ingest/             # Ingestion engine
│   ├── validate/           # Validation engine
│   ├── learn/              # Learning engine
│   ├── schemas/            # Pydantic models
│   └── verification/       # Verification tests
├── personas/               # Persona definitions (markdown)
├── pyproject.toml
└── research                # CLI entry point
```

### Workspace (user instance)

```
/path/to/workspace/
├── strategies/             # Strategy documents (YAML)
│   ├── STRAT-001.yaml
│   ├── STRAT-002.yaml
│   └── ...
├── validations/            # Validation results (immutable)
│   ├── STRAT-001/
│   │   ├── verification.json
│   │   ├── backtest.py
│   │   └── results.json
│   └── ...
├── learnings/              # Extracted learnings (append-only)
│   └── learnings.db        # SQLite or YAML files
├── ideas/                  # Ideas backlog
│   ├── IDEA-001.yaml
│   └── ...
├── inbox/                  # Source files for ingestion
├── logs/                   # Daily log files
│   └── 2026-01-23.log
└── research-kit.yaml       # Configuration
```

---

## Commands

| Command | Purpose |
|---------|---------|
| `research ingest <source>` | Extract strategies from source files |
| `research validate [--all-pending]` | Run validation on strategies |
| `research learn [--since DATE]` | Run persona review |
| `research list [filters]` | Query strategies |
| `research show <id>` | Show strategy details |
| `research ideas` | List ideas backlog |
| `research approve <idea-id>` | Promote idea to strategy |
| `research learnings [filters]` | Query learnings |
| `research status` | Dashboard summary |
| `research verify <id>` | Run verification tests only |
| `research config --validate` | Validate configuration |

---

## Configuration

```yaml
# research-kit.yaml

logging:
  level: INFO
  retention_days: 30

validation:
  windows: 12
  gates:
    min_sharpe: 0.3
    min_consistency: 0.5
    max_drawdown: -0.25
    min_trades: 10

verification:
  enabled: true
  tests:
    - look_ahead_bias
    - survivorship_bias
    - position_sizing
    - data_availability
    - parameter_sanity
    - hardcoded_values

similarity:
  duplicate_threshold: 0.95
  variant_threshold: 0.70

status:
  top_performers:
    count: 5
    columns: [sharpe, cagr, consistency, max_drawdown]
    sort_by: sharpe

personas:
  - name: expert_trader
    file: personas/expert_trader.md
    enabled: true
  - name: statistician
    file: personas/statistician.md
    enabled: true
  - name: risk_manager
    file: personas/risk_manager.md
    enabled: true

ideas:
  max_per_strategy: 5
  auto_prune_days: 30
```

---

## Verification Tests

Mandatory tests that run BEFORE validation:

| Test | What It Catches |
|------|-----------------|
| `look_ahead_bias` | Using future data in signals |
| `survivorship_bias` | Cherry-picked universe |
| `position_sizing` | Invalid sizes, over-leverage |
| `data_availability` | Using data before it exists |
| `parameter_sanity` | Unreasonable parameter values |
| `hardcoded_values` | Dates/values suggesting overfitting |

**These tests are non-negotiable.** A strategy cannot proceed to QC validation without passing all enabled tests.

---

## Data Model

### Strategy States

```
PENDING ──▶ VALIDATING ──▶ VALIDATED
                      └──▶ INVALIDATED
       └──▶ BLOCKED (failed verification)
```

### Entity Retention

| Entity | Retention | Mutability |
|--------|-----------|------------|
| Strategies | Permanent | Immutable once created |
| Validations | Permanent | Immutable |
| Learnings | Permanent | Append-only |
| Ideas | Ephemeral (30-day prune) | Removable |
| Source files | Ephemeral | Can delete after ingest |
| Logs | 30 days | Append-only |

### Source Provenance

Each strategy tracks its source:
- Reference (title, URL, timestamp)
- Excerpt (relevant text)
- Hash (SHA256 of source file)

---

## Boundaries and Immutability

### What Claude CAN Do

- Run research-kit commands
- Read any file
- Write to inbox
- Approve ideas via command

### What Claude CANNOT Do (enforced)

- Edit strategy documents directly (must use ingest/approve)
- Edit validation results (immutable)
- Skip verification tests (mandatory in CLI)
- Edit learnings (append-only)

### Enforcement Layers

1. **CLI enforcement** — Verification tests are mandatory in the `validate` command
2. **CI pipeline** — GitHub Actions runs verification on all commits
3. **File structure** — Results written as immutable records

---

## Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python | QC compatibility, rich ecosystem, fast iteration |
| CLI framework | Click or Typer | Standard Python CLI tools |
| Config format | YAML | Human-readable, standard |
| Logging | Python `logging` with TimedRotatingFileHandler | Standard practice |
| Strategy format | YAML | Human-readable, machine-parseable |
| Learnings store | SQLite or YAML files | Simple, queryable |
| CI/CD | GitHub Actions | Standard, free for public repos |

---

## Sub-Agent Architecture

To prevent context degradation:

```
Main conversation (lightweight orchestration)
    │
    ├── Ingest sub-agent (extraction, gap-filling)
    │
    ├── Validation sub-agent (code gen, verification)
    │
    ├── Persona sub-agents (one per persona)
    │
    └── Analysis sub-agent (cross-strategy patterns)
```

Each sub-agent:
- Gets fresh context
- Has specific task/skill
- Returns structured result
- Can't influence other agents
