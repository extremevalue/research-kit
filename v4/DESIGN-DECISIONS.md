# Research-Kit V4: Design Decisions

**Purpose:** Track all architectural and implementation decisions made during planning.
**Date Started:** 2026-01-24

---

## Decision Log

### DD-001: Backtest Execution — LEAN CLI

**Decision:** Use LEAN CLI for backtest execution instead of direct QC API calls.

**Options Considered:**
- A) Direct QC API calls
- B) LEAN CLI (local + cloud)
- C) Abstraction layer with pluggable backends

**Choice:** B — LEAN CLI

**Rationale:**
- Can run backtests locally without cloud credits during development
- Same execution engine as QC cloud (consistent results)
- Official tooling, actively maintained
- Can switch between local (`lean backtest`) and cloud (`lean cloud backtest`)

**Tradeoffs Accepted:**
- Requires LEAN CLI installation (`pip install lean`)
- Requires Docker for local execution
- Requires historical data download for local backtests

**Implementation Notes:**
```bash
research validate STRAT-001              # Uses local LEAN by default
research validate STRAT-001 --cloud      # Push to QC cloud
research validate STRAT-001 --dry-run    # Generate code only, don't run
```

**Config (.env):**
```bash
LEAN_DATA_PATH=/path/to/lean/data
LEAN_ENGINE_IMAGE=quantconnect/lean:latest
QC_USER_ID=12345        # For cloud backtests
QC_API_TOKEN=xxxxx      # For cloud backtests
```

---

### DD-002: CLI Framework — Typer

**Options Considered:**
- A) Click — More established, more verbose
- B) Typer — Modern, less boilerplate, built on Click

**Decision:** B — Typer

**Rationale:**
- Cleaner code using type hints
- Auto-generates help from annotations
- Built on Click (can drop down if needed)
- Less boilerplate

**Example:**
```python
import typer
app = typer.Typer()

@app.command()
def ingest(source: Path, dry_run: bool = False):
    """Extract strategies from source file."""
    ...
```

---

### DD-003: Data Storage — YAML Files (MVP)

**Options Considered:**
- A) YAML files only
- B) SQLite + YAML
- C) SQLite only

**Decision:** A — YAML files only (for MVP)

**Rationale:**
- Simple, human-readable, git-friendly
- Easy to manually inspect/edit during development
- Can add SQLite indexing later if needed

**Structure:**
```
/strategies/STRAT-001.yaml
/strategies/STRAT-002.yaml
/validations/STRAT-001/results.json
/learnings/learnings.yaml
```

**Note:** May add SQLite indexing in future if querying 100+ strategies becomes slow.

---

### DD-004: Sub-Agent Architecture — Claude Code Task Tool

**Options Considered:**
- A) Claude API directly (Anthropic SDK) — CLI calls API for LLM work
- B) Claude Code Task tool — Claude Code orchestrates, spawns sub-agents
- C) MCP server — External server handles LLM calls

**Decision:** B — Claude Code Task Tool

**Rationale:**
- **Context isolation:** Each sub-agent gets fresh context, prevents drift
- **Parallelization:** Sub-agents can run concurrently (e.g., all personas at once)
- **Separation of concerns:** Clear boundary between orchestration and mechanical work
- **Failure isolation:** If a sub-agent fails, it doesn't corrupt main context
- **Simpler CLI:** CLI only handles file I/O, LEAN execution, schema validation

**Architecture:**
```
User ↔ Claude Code (orchestrator)
           │
           ├── Task tool → Sub-agent (extraction)
           ├── Task tool → Sub-agent (rationale research)
           ├── Task tool → Sub-agent (persona 1) ─┐
           ├── Task tool → Sub-agent (persona 2) ─┼── parallel
           └── Task tool → Sub-agent (persona N) ─┘
                    │
                    ▼
              CLI commands (mechanical)
              - research ingest (file I/O, schema validation)
              - research validate (LEAN execution)
              - research learn (store learnings)
```

**CLI Responsibilities (Mechanical):**
- Read/write strategy YAML files
- Execute LEAN CLI commands
- Schema validation (Pydantic)
- Quality scoring calculations
- Similarity checking against existing strategies
- Status queries and reporting

**Sub-Agent Responsibilities (LLM-heavy):**
- Strategy extraction from source text
- Gap filling (missing parameters)
- Rationale inference and research
- Red flag detection
- Persona reviews
- Idea generation

**Benefits:**
- Sub-agents run in parallel where tasks are independent
- Main conversation stays lightweight (orchestration only)
- Less likely to "skip commands and edit directly" when issues arise
- Each phase (Ingest, Validate, Learn) can spawn multiple sub-agents

---

### DD-005: Strategy ID Generation — Sequential with Prefix

**Options Considered:**
- A) Sequential (STRAT-001, STRAT-002)
- B) Date-based (STRAT-20260124-001)
- C) UUID-based (STRAT-a1b2c3d4)

**Decision:** A — Sequential with Prefix

**Rationale:**
- Simple and human-readable
- Easy to reference in conversation ("STRAT-042")
- Natural ordering for chronological review
- IDs don't change if strategy is edited

**Implementation:**
- Format: `STRAT-{NNN}` where NNN is zero-padded to 3 digits
- Stored in config: `next_strategy_id: 43`
- Ideas use: `IDEA-{NNN}`
- Validation results reference strategy ID

**Note:** If we hit 999 strategies, extend to 4 digits. Good problem to have.

---

### DD-006: Workspace Structure — Confirmed

**Decision:** Use proposed structure with minor additions.

```
~/research-workspace/
├── .env                    # Secrets (LEAN paths, QC credentials)
├── research-kit.yaml       # Config (gates, thresholds, enabled tests)
├── inbox/                  # Source files to ingest
├── strategies/             # Strategy documents (YAML)
│   ├── STRAT-001.yaml
│   └── STRAT-002.yaml
├── validations/            # Validation results (immutable)
│   ├── STRAT-001/
│   │   ├── results.json
│   │   └── generated_code.py
│   └── STRAT-002/
├── learnings/              # Extracted learnings (append-only)
│   └── learnings.yaml
├── ideas/                  # Generated ideas (backlog)
│   ├── IDEA-001.yaml
│   └── IDEA-002.yaml
├── personas/               # Persona definitions (markdown)
│   ├── veteran-quant.md
│   └── skeptical-statistician.md
├── archive/                # Rejected/archived strategies
│   └── STRAT-003.yaml
└── logs/                   # Daily rotating logs
    └── research-kit-2026-01-24.log
```

**Key Points:**
- `inbox/` is working directory, files processed and removed
- `strategies/` is the active catalog
- `validations/` are immutable once written
- `learnings/` is append-only
- `archive/` for strategies that failed quality filters (kept for reference)
- `personas/` allows customizing persona prompts

---

## Previously Decided (During Architecture Phase)

### DD-007: Rationale Handling — Infer if Not Stated

**Decision:** Don't reject strategies missing economic rationale. Sub-agents attempt to infer rationale and track provenance.

**Rationale:**
- The WHY can exist even if unstated by source
- Validation is the real test
- Asymmetric risk: cost of missing good strategy > cost of processing noise

**Implementation:**
```yaml
edge:
  provenance:
    source: source_stated | source_enhanced | inferred | unknown
    confidence: high | medium | low
    research_notes: string
    factor_alignment: string
```

---

### DD-008: Red Flags — Hard vs Soft

**Decision:**
- Hard rejects: Sharpe > 3, "never loses", "works all conditions", author selling courses
- Soft warnings: Unknown rationale, no transaction costs, single market, etc.

**Key Change:** "No economic rationale" moved from hard reject to soft warning (sub-agent will infer).

---

### DD-009: Ingestion Quality Scoring

**Decision:** Two-tier scoring system:
- Specificity score (0-8): Can we test this? Reject if < 4
- Trust score (0-100): Is it worth testing? Archive if < 50

---

### DD-010: Phase 3 Scope — Full Persona Review

**Decision:** Include full LLM persona review in the Learn/Ideation phase (not a stripped-down version).

---

### DD-011: Build Approach — Phased with Testing

**Decision:** Build in three major phases, each independently testable:
1. Ingestion
2. Validation
3. Ideation

Use GitHub best practices: issues, feature branches, PRs, merges.

---

### DD-012: Target Platform

**Decision:** Python CLI application

**Rationale:**
- QC/LEAN compatibility
- Rich ecosystem
- Fast iteration

---

## Open Questions

**Resolved:**
- [x] DD-001: Backtest Execution → LEAN CLI
- [x] DD-002: CLI Framework → Typer
- [x] DD-003: Data Storage → YAML files (MVP)
- [x] DD-004: Sub-Agent Architecture → Claude Code Task tool
- [x] DD-005: Strategy ID → Sequential (STRAT-NNN)
- [x] DD-006: Workspace Structure → Confirmed
- [x] DD-007: Rationale Handling → Infer if not stated
- [x] DD-008: Red Flags → Hard vs Soft categories
- [x] DD-009: Quality Scoring → Specificity + Trust
- [x] DD-010: Phase 3 Scope → Full persona review
- [x] DD-011: Build Approach → Phased with testing
- [x] DD-012: Target Platform → Python CLI

**Still Open (document during build):**
- [ ] Data strategy for LEAN (which data packs to document)
- [ ] Docker requirement documentation
- [ ] Error handling approach (graceful failures, retry logic)
- [ ] Logging format (structured JSON vs plain text)
- [ ] Persona prompt structure (how much context to include)
