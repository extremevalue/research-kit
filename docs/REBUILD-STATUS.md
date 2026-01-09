# Research-Kit v2.0 Rebuild Status

**Purpose**: This document tracks the full context of the v2.0 rebuild. Read this first when starting a new session.

**Last Updated**: 2025-01-08

---

## Quick Context

We are **rebuilding research-kit from scratch** to fix fundamental issues with v1.0. The current workspace (`/Users/t/_repos/research-project/`) is a flawed instance that will be replaced once v2.0 is complete.

---

## Why We're Rebuilding

### Critical Issues Found in v1.0

1. **Broken Validation** (date injection bug)
   - `_inject_dates()` regex only matches PascalCase (`SetStartDate`)
   - `_fix_qc_api_issues()` converts to snake_case (`set_start_date`)
   - Result: Dates never injected, IS/OOS produce identical results
   - 25+ "validated" strategies have invalid results

2. **LLM Drift**
   - LLM generates free-form code with embedded assumptions
   - LLM interprets hypothesis literally ("test on 2024" → hardcodes 2024)
   - Inconsistent output (same input → different code)

3. **Derived Idea Explosion**
   - Expert review suggestions auto-create catalog entries
   - 600+ entries, many duplicates (62 "Follow the Flow" variants)
   - No deduplication at ingestion

4. **No Regime Analysis**
   - Can't tell when strategies work vs don't work
   - No multi-dimensional performance fingerprinting

5. **No Portfolio Synthesis**
   - Individual strategy focus
   - No combination or enhancement suggestions

---

## What We're Building

### Core Principle

**LLMs output structured data; deterministic code executes.**

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  INGESTION → VALIDATION → ANALYSIS → SYNTHESIS → ENHANCEMENT   │
│      ↓            ↓           ↓           ↓            ↓        │
│  Strategy    Walk-Forward   Critical   Portfolio   Leverage/   │
│  Definition   + Regime      Review     Combos      Options/    │
│  (JSON)      Tagging                               Futures     │
│                                                                 │
│  All proposals → QUEUE → Human Review → Approved entries       │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python | QC requires Python; existing code |
| Storage | JSON + SQLite hybrid | Human-readable defs; queryable catalog |
| Schema | Pydantic | Auto-generates JSON Schema |
| CLI | Typer | Type-annotated; works with Pydantic |
| Templates | Jinja2 | Powerful; well-known |
| Validation | Walk-forward + regime tagging | Better than simple IS/OOS |

### Tiered Strategy Definitions

| Tier | Coverage | Description |
|------|----------|-------------|
| Tier 1 | 70% | Templated - LLM fills parameters only |
| Tier 2 | 20% | Component-based with expression language |
| Tier 3 | 10% | Custom code with human review |

### Multi-Dimensional Regime Analysis

Every strategy gets a performance fingerprint across:
- Market direction (bull/bear/sideways)
- Volatility (high/normal/low)
- Sector leadership (tech/energy/healthcare/...)
- Market cap (large/mid/small)
- Geography (US/Europe/EM/...)
- Rate environment (rising/flat/falling)

### Strategy Enhancement Layer (NEW)

When a strategy validates on the underlying (e.g., SPY), explore:
- **Leverage variants**: 1x, 1.5x, 2x, 3x
- **Options strategies**: Covered calls, protective puts, spreads
- **Futures implementation**: ES vs SPY
- **Position sizing optimization**: Kelly criterion, risk parity

Goal: Maximize return while managing drawdown.

### Proposal Queue

All LLM suggestions become proposals that require human review:
- Composite strategies (A + B with switching)
- Enhancement variants (leverage, options)
- Data acquisition recommendations
- New strategy applications

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| CLI Framework | Typer |
| Schema Validation | Pydantic |
| Data Storage | SQLite + JSON files |
| Template Engine | Jinja2 |
| Testing | pytest + golden tests |
| Backtesting | QuantConnect Cloud |
| LLM | Claude API (Anthropic) |

---

## Implementation Phases

### Phase 0: Setup & Foundation
- [ ] Create GitHub project board
- [ ] Define issue templates
- [ ] Set up CI/CD pipeline
- [ ] **Clean up v1 documentation** (only v2 docs remain)
- [ ] Create branch protection rules

### Phase 1: Core Schemas & Data Layer
- [ ] Define Pydantic models for all schemas
- [ ] Set up SQLite database schema
- [ ] Implement catalog CRUD operations
- [ ] Add schema validation tests

### Phase 2: Code Generation (Tier 1)
- [ ] Design template structure
- [ ] Implement template engine
- [ ] Build code generator (framework-controlled dates)
- [ ] Add golden tests for reproducibility

### Phase 3: Validation Pipeline
- [ ] Implement walk-forward analyzer
- [ ] Build regime tagger
- [ ] Add statistical validation
- [ ] Integrate with QuantConnect

### Phase 4: Ingestion Pipeline
- [ ] Implement schema-based ingestion
- [ ] Build deduplication checker
- [ ] Create ingestion CLI command

### Phase 5: Analysis & Synthesis
- [ ] Implement analysis engine
- [ ] Implement synthesis engine
- [ ] Build proposal queue
- [ ] Create review CLI commands

### Phase 6: Strategy Enhancement
- [ ] Leverage variant generator
- [ ] Options strategy templates
- [ ] Futures implementation support
- [ ] Position sizing optimizer

### Phase 7: Tier 2 Support
- [ ] Define expression language
- [ ] Implement expression parser
- [ ] Build block combiner
- [ ] Add external data support

### Phase 8: Testing & Documentation
- [ ] Comprehensive test suite
- [ ] User documentation
- [ ] API documentation
- [ ] Example workflows

---

## Finalized Design Decisions

All open questions have been resolved. See `ARCHITECTURE.md` for full details.

| Question | Decision |
|----------|----------|
| Walk-forward window size | 3-year windows (configurable) |
| Regime definitions | Multi-dimensional: direction (SPY vs 200-SMA), volatility (VIX levels), rates, sectors, cap |
| Expression language | Simple DSL with predefined functions (sma, ema, roc, rsi, etc.) |
| External data sources | FRED first (macro data), Yahoo as fallback |
| Multiple testing correction | FDR (Benjamini-Hochberg) default, Bonferroni optional |
| Tier 3 review | Always require human review for custom code |

---

## File Locations

| What | Where |
|------|-------|
| Architecture doc | `/Users/t/_repos/extremevalue/research-kit/docs/ARCHITECTURE.md` |
| This status doc | `/Users/t/_repos/extremevalue/research-kit/docs/REBUILD-STATUS.md` |
| Old flawed workspace | `/Users/t/_repos/research-project/` (DO NOT BUILD ON THIS) |
| research-kit repo | `/Users/t/_repos/extremevalue/research-kit/` |

---

## Session Recovery Instructions

If starting a new session:

1. Read this document first (`docs/REBUILD-STATUS.md`)
2. Read the architecture (`docs/ARCHITECTURE.md`)
3. Check GitHub issues for current work items
4. Continue from where we left off

---

## Decisions Log

| Date | Decision | Context |
|------|----------|---------|
| 2025-01-08 | Rebuild v2.0 from scratch | v1.0 has fundamental validation bugs |
| 2025-01-08 | Python + SQLite hybrid | Balance human-readability with queryability |
| 2025-01-08 | Tiered strategy definitions | Constrain LLM where possible, allow flexibility where needed |
| 2025-01-08 | Walk-forward + regime tagging | Better than simple IS/OOS split |
| 2025-01-08 | Proposal queue for human review | Prevent auto-created entries |
| 2025-01-08 | Strategy enhancement layer | Explore leverage/options/futures on validated strategies |
| 2025-01-08 | 3-year walk-forward windows | Good balance of data and number of windows |
| 2025-01-08 | Multi-dimensional regime definitions | SPY/200-SMA for direction, VIX for vol, rates, sectors, cap |
| 2025-01-08 | Simple DSL for Tier 2 expressions | Security and reproducibility over flexibility |
| 2025-01-08 | FRED as primary external data | Free, reliable, comprehensive macro data |
| 2025-01-08 | FDR for multiple testing correction | Better balance than Bonferroni for exploration |
| 2025-01-08 | Always require human review for Tier 3 | Safety over convenience |

---

## Current Status

**Phase**: Pre-implementation (architecture finalized)
**Last Updated**: 2025-01-08

Completed:
- [x] Architecture document created
- [x] All open questions finalized
- [x] Technology stack decided (Python, SQLite hybrid, Pydantic, Typer, Jinja2)
- [x] GitHub issues created for Phase 0 and Phase 1
- [x] Phase 0: CI/CD pipeline, issue templates
- [x] Phase 1: Pydantic schemas, SQLite schema, CatalogManager

## GitHub Issues

### Epic
- #77 - [Epic] Research-Kit v2.0 Rebuild (tracks all phases)

### Phase 0: Setup & Foundation
- #70 - Project board and issue templates
- #71 - CI/CD pipeline with pytest
- #72 - Branch protection rules

### Phase 1: Core Schemas & Data Layer
- #73 - Pydantic models for all schemas
- #74 - SQLite database schema
- #75 - Catalog CRUD operations
- #76 - Schema validation tests

---

## Next Actions

1. ~~Finalize open questions~~ DONE
2. ~~Create GitHub issues for Phase 0 and Phase 1~~ DONE
3. Begin implementation (start with #73 - Pydantic models)

---

*This document should be updated as decisions are made and phases complete.*
