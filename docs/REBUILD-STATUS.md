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

**Phase**: Phase 2 - Code Generation (in progress)
**Last Updated**: 2025-01-10

### Completed Phases

#### Phase 0: Setup & Foundation
- [x] #71 - CI/CD pipeline (PR #78) - lint, format, type check, tests with 97% coverage
- [ ] #70 - Project board - **REQUIRES USER ACTION** (needs admin access)
- [ ] #72 - Branch protection - **REQUIRES USER ACTION** (needs admin access)

#### Phase 1: Core Schemas & Data Layer (COMPLETE)
- [x] #73 - Pydantic models (strategy, validation, proposal schemas)
- [x] #74 - SQLite database schema
- [x] #75 - Catalog CRUD operations (CatalogManager)
- [x] #76 - Schema validation tests (PR #79, #80, #81) - 112 tests, 97% coverage

#### Phase 2: Code Generation (IN PROGRESS)
- [x] #82 - Template structure (PR #86) - 6 Jinja2 templates
- [x] #83 - Template engine (PR #87) - TemplateEngine class, filters, validation
- [ ] #84 - Code generator CLI - **CURRENT WORK**
- [ ] #85 - Golden tests for code generation

### Test Suite
- **165 tests** passing
- **97% code coverage** (minimum 90% enforced in CI)
- Golden tests for schema stability

## GitHub Issues

### Epic
- #77 - [Epic] Research-Kit v2.0 Rebuild (tracks all phases)

### Phase 0: Setup & Foundation
- #70 - Project board and issue templates - **OPEN (user action required)**
- #71 - CI/CD pipeline with pytest - **CLOSED**
- #72 - Branch protection rules - **OPEN (user action required)**

### Phase 1: Core Schemas & Data Layer (ALL CLOSED)
- #73 - Pydantic models - **CLOSED**
- #74 - SQLite database schema - **CLOSED**
- #75 - Catalog CRUD operations - **CLOSED**
- #76 - Schema validation tests - **CLOSED**

### Phase 2: Code Generation
- #82 - Template structure design - **CLOSED**
- #83 - Template engine implementation - **CLOSED**
- #84 - Code generator with framework-controlled dates - **OPEN (current)**
- #85 - Golden tests for code generation - **OPEN**

---

## Key Files Created

### Schemas (`research_system/schemas/`)
- `strategy.py` - StrategyDefinition, UniverseConfig, SignalConfig, etc.
- `validation.py` - ValidationResult, WindowMetrics, RegimeTags
- `proposal.py` - Proposal for LLM suggestions
- `common.py` - Shared enums (EntryStatus, EntryType, etc.)

### Database (`research_system/db/`)
- `connection.py` - DatabaseConnection with transactions
- `catalog.py` - CatalogManager for CRUD operations
- `schema.sql` - SQLite schema definition

### Code Generation (`research_system/codegen/`)
- `templates/base.py.j2` - Base QuantConnect template
- `templates/momentum_rotation.py.j2` - Top-N momentum selection
- `templates/mean_reversion.py.j2` - Z-score entry/exit
- `templates/trend_following.py.j2` - MA trend filter
- `templates/dual_momentum.py.j2` - Absolute + relative momentum
- `templates/breakout.py.j2` - Price breakout with trailing stops
- `engine.py` - TemplateEngine for rendering
- `filters.py` - Custom Jinja2 filters

### Tests (`tests_v2/`)
- `test_schemas.py` - Strategy schema tests
- `test_validation.py` - Validation schema tests
- `test_common.py` - Enum tests
- `test_db_connection.py` - Database connection tests
- `test_catalog_manager.py` - CatalogManager CRUD tests
- `test_golden.py` - Schema stability tests
- `test_templates.py` - Template structure tests
- `test_codegen_engine.py` - Template engine tests

---

## Next Actions

1. **Current**: Implement code generator CLI (#84)
   - CLI command: `research codegen STRAT-001 --output ./output/`
   - Integration with CatalogManager (lookup by ID)
   - Ensure no hardcoded dates in output

2. **Next**: Add golden tests for code generation (#85)

3. **User Action Required**:
   - #70 - Create GitHub project board
   - #72 - Configure branch protection rules

---

*This document should be updated as decisions are made and phases complete.*
