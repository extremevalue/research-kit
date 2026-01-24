# Research-Kit V4: Implementation Plan

## Overview

Build incrementally. Test each piece. Don't move forward until current piece works.

---

## Phase 1: Foundation

**Goal:** Basic structure, schema validation, config loading

### Tasks

1. **Project setup**
   - Create new Python package structure
   - Set up pyproject.toml with dependencies
   - Configure logging (TimedRotatingFileHandler)
   - Set up pytest

2. **Schema implementation**
   - Implement strategy document schema as Pydantic models
   - Write schema validation tests
   - Test against 5 test cases (must all validate)

3. **Config loading**
   - Parse research-kit.yaml
   - Validate config on load
   - Make config accessible throughout system

4. **CLI skeleton**
   - Set up Click/Typer CLI
   - Implement placeholder commands
   - Verify CLI structure works

### Acceptance Criteria

- [ ] `research --help` shows all commands
- [ ] `research config --validate` works
- [ ] All 5 test strategies validate against schema
- [ ] Logging writes to daily rotating files

---

## Phase 2: Ingest Flow

**Goal:** Extract strategies from source files with quality filtering

### Tasks

1. **Ingestion engine**
   - Read source files from inbox
   - Call Claude sub-agent for extraction
   - Structure output as strategy documents

2. **Gap filling**
   - Sub-agent to fill missing parameters
   - Propose reasonable defaults
   - Flag assumptions made

3. **Rationale extraction and research (Critical)**
   - Attempt to extract stated rationale from source
   - If rationale is clear → mark as "source_stated"
   - If rationale is partial → sub-agent enhances → mark as "source_enhanced"
   - If rationale is absent → sub-agent researches:
     - Check against known factors (momentum, value, quality, low-vol, etc.)
     - Check against structural edges (index rebalancing, calendar effects, etc.)
     - Research academic literature for similar strategies
     - Propose rationale with confidence level → mark as "inferred"
   - If no rationale found even after research → mark as "unknown" (still proceed!)
   - Track provenance: source, confidence, factor_alignment, research_notes
   - **Note: Unknown rationale is NOT a rejection reason**

4. **Source credibility assessment (NEW)**
   - Assess author track record
   - Check for skin in the game
   - Identify conflicts of interest
   - Record claimed performance

5. **Red flag detection**
   - Check for hard rejection flags:
     - Sharpe > 3.0 claimed (non-HFT)
     - Author selling courses/signals/newsletters
     - "Works in all market conditions"
     - "Never had a losing month/year"
   - Check for soft warning flags:
     - Single market tested
     - Bull market only period (2010-2020)
     - High leverage required (> 3x)
     - No transaction costs discussed
     - Unknown rationale after research (proceed but flag)
   - **Note: "No rationale" is NOT a hard rejection** — sub-agent will attempt to infer

6. **Quality scoring (NEW)**
   - Calculate specificity score (0-8)
     - Reject if < 4 (can't test it)
   - Calculate trust score (0-100)
     - Archive if < 50 (not worth testing)
   - Prioritize queue by score

7. **Similarity checking**
   - Compare new strategy to existing catalog
   - Block duplicates
   - Tag variants

8. **Storage**
   - Write strategy documents to /strategies
   - Track provenance (source, excerpt, hash)
   - Store ingestion quality metrics

### Test Cases

- Ingest a text file describing dividend capture strategy → should pass quality filter
- Ingest a "too good to be true" strategy (Sharpe > 3, no rationale) → should reject
- Ingest a vague strategy without entry rules → should archive (specificity < 4)

### Acceptance Criteria

- [ ] `research ingest <file>` produces valid strategy document
- [ ] Ingestion extracts the "WHY" framework fields
- [ ] Red flags are detected and logged
- [ ] Specificity score calculated (reject if < 4)
- [ ] Trust score calculated (archive if < 50)
- [ ] Duplicates are blocked with message
- [ ] Variants are tagged with parent reference
- [ ] Provenance is recorded (source, hash, excerpt)

---

## Phase 3: Verification Tests

**Goal:** Mandatory gate before validation

### Tasks

1. **Verification framework**
   - Define verification test interface
   - Implement test runner
   - Aggregate results

2. **Individual tests**
   - Look-ahead bias detection
   - Position sizing validation
   - Data availability check
   - Parameter sanity check
   - Hardcoded values detection

3. **CLI integration**
   - `research verify <id>` runs tests
   - `research validate` calls verify first
   - Cannot proceed if verification fails

### Test Cases

- Strategy with obvious look-ahead bias → should fail
- Strategy with invalid position sizing → should fail
- Valid strategy → should pass all tests

### Acceptance Criteria

- [ ] `research verify STRAT-XXX` runs all enabled tests
- [ ] Clear output showing pass/fail per test
- [ ] Failed verification blocks validation
- [ ] Tests are configurable in YAML

---

## Phase 4: Validation Flow

**Goal:** Run strategies through QC walk-forward validation

### Tasks

1. **Code generation**
   - Generate QuantConnect Python from strategy document
   - Support all strategy types (single-leg, multi-leg, pairs, regime-adaptive)
   - Include transaction costs, slippage

2. **QC integration**
   - Submit backtest to QuantConnect API
   - Handle 12 walk-forward windows
   - Retrieve results

3. **Gate evaluation**
   - Apply configured gates (Sharpe, consistency, etc.)
   - Determine VALIDATED/INVALIDATED

4. **Result storage**
   - Write immutable validation results
   - Store generated code
   - Record gate outcomes

### Test Case

- Validate a simple trend-following strategy
- Verify results match expected format
- Verify results are immutable

### Acceptance Criteria

- [ ] `research validate STRAT-XXX` runs full validation
- [ ] Results stored in /validations/STRAT-XXX/
- [ ] Gates evaluated correctly
- [ ] Batch validation works with `--all-pending`

---

## Phase 5: Learn Flow

**Goal:** Persona review and idea generation

### Tasks

1. **Persona framework**
   - Load persona definitions from markdown
   - Call Claude sub-agent with persona prompt
   - Structure persona output

2. **Learning extraction**
   - Analyze validation results
   - Identify patterns, insights
   - Store learnings (append-only)

3. **Idea generation**
   - Generate new strategy ideas from learnings
   - Check for similarity to existing
   - Add to backlog

4. **Idea approval**
   - `research approve <idea-id>`
   - Convert idea to PENDING strategy
   - Track lineage

### Test Case

- Run learn on a set of validated/invalidated strategies
- Verify learnings are extracted
- Verify ideas are generated and added to backlog

### Acceptance Criteria

- [ ] `research learn` produces learnings
- [ ] `research ideas` shows backlog
- [ ] `research approve IDEA-XXX` creates new strategy
- [ ] Lineage tracked (derived from X, Y)

---

## Phase 6: Status and Queries

**Goal:** Dashboard and querying

### Tasks

1. **Status dashboard**
   - Summary stats (total, validated, invalidated)
   - Top performers (Sharpe, CAGR, consistency, max drawdown)
   - Ideas backlog count

2. **Query commands**
   - `research list [filters]`
   - `research show <id>`
   - `research learnings [filters]`

3. **Exports**
   - CSV export of strategies
   - JSON export for analysis

### Acceptance Criteria

- [ ] `research status` shows dashboard
- [ ] `research list --status validated` filters correctly
- [ ] `research show STRAT-XXX` displays full details

---

## Phase 7: CI Pipeline

**Goal:** Automated verification on commits

### Tasks

1. **GitHub Actions workflow**
   - Run verification on push/PR
   - Validate all strategy schemas
   - Run test suite

2. **Pre-commit hooks (optional)**
   - Local verification before commit

### Acceptance Criteria

- [ ] Push triggers CI pipeline
- [ ] PR cannot merge if verification fails
- [ ] All tests pass in CI

---

## Phase 8: Hardening

**Goal:** Edge cases, error handling, polish

### Tasks

1. **Error handling**
   - Graceful failures with clear messages
   - Retry logic for QC API
   - Recovery from partial failures

2. **Edge cases**
   - Large files in ingestion
   - Concurrent operations
   - Config errors

3. **Documentation**
   - README
   - CLI help text
   - Examples

### Acceptance Criteria

- [ ] System handles errors gracefully
- [ ] Clear error messages guide user
- [ ] Documentation is complete

---

## Validation: Test Against 5 Complex Strategies

Before declaring V4 complete, all 5 test strategies must:

1. [ ] **Dividend Capture** — Ingest, verify, validate end-to-end
2. [ ] **FX Correlation** — Ingest, verify, validate end-to-end
3. [ ] **Earnings + Sentiment** — Ingest, verify, validate end-to-end (may need mock data)
4. [ ] **Regime-Adaptive** — Ingest, verify, validate end-to-end
5. [ ] **Volatility Arb** — Ingest, verify, validate end-to-end (may need mock data)

---

## Rough Sequence

```
Phase 1: Foundation        ████████░░  (schema, config, CLI skeleton)
Phase 2: Ingest            ████████░░  (extraction, similarity)
Phase 3: Verification      ████████░░  (test framework, individual tests)
Phase 4: Validation        ██████████  (code gen, QC, gates)
Phase 5: Learn             ████████░░  (personas, learnings, ideas)
Phase 6: Status/Queries    ██████░░░░  (dashboard, list, show)
Phase 7: CI Pipeline       ████░░░░░░  (GitHub Actions)
Phase 8: Hardening         ████████░░  (errors, edge cases, docs)
```

Each phase builds on the previous. Don't skip ahead.
