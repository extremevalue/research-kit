# Research-Kit Architecture

**Version:** 2.0 (Proposed Rebuild)
**Status:** DRAFT - For Discussion
**Date:** 2025-01-08

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Design Principles](#design-principles)
4. [C4 Architecture Diagrams](#c4-architecture-diagrams)
5. [Technology Trade-offs](#technology-trade-offs)
6. [Core Data Schemas](#core-data-schemas)
7. [Component Details](#component-details)
8. [Data Flow](#data-flow)
9. [Implementation Phases](#implementation-phases)
10. [Open Questions](#open-questions)

---

## Executive Summary

Research-Kit is a **strategy discovery and validation system** that:

1. **Ingests** trading ideas from diverse sources (PDFs, code, articles)
2. **Validates** strategies rigorously with walk-forward analysis and regime tagging
3. **Synthesizes** insights across the portfolio to identify complementary strategies
4. **Outputs** deploy-ready trading systems with documented performance characteristics

### Key Design Decision

**LLMs output structured data; deterministic code executes.**

This separation ensures reproducibility, prevents LLM drift, and maintains validation integrity.

---

## Problem Statement

### Issues with Current System

| Problem | Impact |
|---------|--------|
| LLM generates free-form backtest code | Inconsistent, unreproducible, embeds assumptions |
| Date injection fails (regex bug) | IS/OOS validation broken, identical results |
| Derived ideas auto-create entries | Explosion of 600+ entries, many duplicates |
| No regime analysis | Can't identify when strategies work/don't work |
| No portfolio synthesis | Individual strategy focus, no combination insights |
| No human checkpoints | Bad data flows through unchecked |

### Goals for v2.0

1. **Reproducibility**: Same input always produces same output
2. **Validation Integrity**: Framework controls all test parameters
3. **Regime Awareness**: Know which market conditions each strategy suits
4. **Portfolio Synthesis**: Combine strategies intelligently
5. **Auditability**: Full lineage tracking, human review on demand

---

## Design Principles

### 1. Separation of Concerns

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM BOUNDARY                                  │
│  - Extracts information from documents                          │
│  - Fills structured schemas                                     │
│  - Analyzes results                                             │
│  - Proposes combinations                                        │
│  - CANNOT: Execute code, create entries, set parameters         │
├─────────────────────────────────────────────────────────────────┤
│                    DETERMINISTIC BOUNDARY                        │
│  - Creates catalog entries                                      │
│  - Generates backtest code from templates                       │
│  - Runs backtests with controlled parameters                    │
│  - Stores results                                               │
│  - ALWAYS: Controls dates, versions artifacts                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Tiered Strategy Definitions

| Tier | Coverage | LLM Role | Code Generation |
|------|----------|----------|-----------------|
| **Tier 1: Templated** | 70% | Fill parameters | Template engine |
| **Tier 2: Component-based** | 20% | Assemble blocks + expressions | Block combiner |
| **Tier 3: Custom** | 10% | Generate code (reviewed) | LLM + human review |

### 3. Proposals, Not Auto-Creation

LLM suggestions become **proposals** that enter a queue for human review, not automatic catalog entries.

### 4. Everything is Versioned

- Strategy definitions: Hashed and versioned
- Generated code: Derived from definition, regeneratable
- Results: Linked to specific code + parameter versions

---

## C4 Architecture Diagrams

### Level 1: System Context

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CONTEXT DIAGRAM                                 │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │    USER     │
                              │ (Researcher)│
                              └──────┬──────┘
                                     │
                      ┌──────────────┼──────────────┐
                      │              │              │
                      ▼              ▼              ▼
               ┌───────────┐  ┌───────────┐  ┌───────────┐
               │  Source   │  │  Review   │  │  Deploy   │
               │ Documents │  │ Proposals │  │Strategies │
               └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
                     │              │              │
                     └──────────────┼──────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │                               │
                    │        RESEARCH-KIT           │
                    │                               │
                    │   Strategy Discovery and      │
                    │   Validation System           │
                    │                               │
                    └───────────────┬───────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
   ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
   │QuantConnect │          │   Claude    │          │External Data│
   │   Cloud     │          │     API     │          │  Sources    │
   │ (Backtest)  │          │   (LLM)     │          │ (FRED, etc) │
   └─────────────┘          └─────────────┘          └─────────────┘
```

### Level 2: Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CONTAINER DIAGRAM                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         RESEARCH-KIT                                 │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │             │  │             │  │             │  │            │  │   │
│  │  │  INGESTION  │  │ VALIDATION  │  │  ANALYSIS   │  │ SYNTHESIS  │  │   │
│  │  │   ENGINE    │  │   ENGINE    │  │   ENGINE    │  │  ENGINE    │  │   │
│  │  │             │  │             │  │             │  │            │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘  │   │
│  │         │                │                │               │         │   │
│  │         └────────────────┴────────────────┴───────────────┘         │   │
│  │                                   │                                  │   │
│  │                                   ▼                                  │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │                        DATA LAYER                              │  │   │
│  │  │                                                                │  │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │  │   │
│  │  │  │ Catalog  │  │ Strategy │  │Validation│  │   Proposal   │   │  │   │
│  │  │  │ (entries)│  │  Defs    │  │ Results  │  │    Queue     │   │  │   │
│  │  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │  │   │
│  │  │                                                                │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │                                                                      │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │                         CLI / API                              │  │   │
│  │  │   /ingest  /validate  /analyze  /synthesize  /proposals       │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Level 3: Component Diagram (Validation Engine)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VALIDATION ENGINE - COMPONENTS                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  INPUT: Strategy Definition (JSON)                                   │   │
│  │                                                                      │   │
│  └───────────────────────────────┬──────────────────────────────────────┘   │
│                                  │                                          │
│                                  ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      CODE GENERATOR                                  │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │   Tier 1     │  │   Tier 2     │  │   Tier 3     │               │   │
│  │  │  Template    │  │    Block     │  │   Custom     │               │   │
│  │  │   Engine     │  │  Combiner    │  │  (Reviewed)  │               │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  │                                                                      │   │
│  └───────────────────────────────┬──────────────────────────────────────┘   │
│                                  │                                          │
│                                  ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    BACKTEST RUNNER                                   │   │
│  │                                                                      │   │
│  │  • Injects dates (ALWAYS framework-controlled)                      │   │
│  │  • Manages QuantConnect Cloud API                                   │   │
│  │  • Handles retries and rate limiting                                │   │
│  │                                                                      │   │
│  └───────────────────────────────┬──────────────────────────────────────┘   │
│                                  │                                          │
│                                  ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   WALK-FORWARD ANALYZER                              │   │
│  │                                                                      │   │
│  │  ┌────────┬────────┬────────┬────────┬────────┬────────┐            │   │
│  │  │2010-12 │2012-14 │2014-16 │2016-18 │2018-20 │2020-24 │            │   │
│  │  │Window 1│Window 2│Window 3│Window 4│Window 5│Window 6│            │   │
│  │  └────────┴────────┴────────┴────────┴────────┴────────┘            │   │
│  │                                                                      │   │
│  └───────────────────────────────┬──────────────────────────────────────┘   │
│                                  │                                          │
│                                  ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     REGIME TAGGER                                    │   │
│  │                                                                      │   │
│  │  Tags each window with:                                              │   │
│  │  • Market Direction (bull/bear/sideways)                            │   │
│  │  • Volatility (high/normal/low)                                     │   │
│  │  • Sector Leadership (tech/energy/healthcare/...)                   │   │
│  │  • Cap Leadership (large/mid/small)                                 │   │
│  │  • Rate Environment (rising/flat/falling)                           │   │
│  │                                                                      │   │
│  └───────────────────────────────┬──────────────────────────────────────┘   │
│                                  │                                          │
│                                  ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                  STATISTICAL VALIDATOR                               │   │
│  │                                                                      │   │
│  │  • Bootstrap confidence intervals                                   │   │
│  │  • p-values with multiple testing correction                        │   │
│  │  • Consistency score (% windows positive)                           │   │
│  │  • Regime performance aggregation                                   │   │
│  │                                                                      │   │
│  └───────────────────────────────┬──────────────────────────────────────┘   │
│                                  │                                          │
│                                  ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  OUTPUT: Validation Result + Performance Fingerprint                │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Trade-offs

### Decision 1: Primary Language

| Option | Pros | Cons |
|--------|------|------|
| **Python** | QuantConnect uses Python; rich data science ecosystem; existing code is Python; easy LLM integration | Slower; less rigorous typing; dependency management |
| **Go** | Fast; single binary distribution; strong typing; excellent CLI tooling (Cobra); good concurrency | Less data science ecosystem; would need Python for QC code gen |
| **Hybrid** | Best of both: Go for CLI/orchestration, Python for data/QC integration | Two languages to maintain; interface complexity |

**Recommendation**: **Python** for v2.0, with clean interfaces that could allow Go rewrite later.

**Rationale**:
- QuantConnect algorithms must be Python
- Existing code is Python
- LLM integration libraries (anthropic) are Python-native
- Faster iteration for initial build

---

### Decision 2: Data Storage

| Option | Pros | Cons |
|--------|------|------|
| **JSON files** | Human-readable; git-friendly; simple; current approach | No querying; no relationships; slow for large catalogs |
| **SQLite** | Queryable; relational; still single-file portable; fast | Less human-readable; git diffs harder; migration needed |
| **Hybrid** | JSON for strategy definitions (human review); SQLite for catalog/results (querying) | Two systems; sync complexity |

**Recommendation**: **Hybrid** approach.

**Rationale**:
- Strategy definitions should be human-reviewable (JSON)
- Catalog queries like "show all validated strategies with Sharpe > 1.0 in bull markets" need SQL
- SQLite is still a single file, portable, no server needed

**Proposed split**:
```
workspace/
├── strategies/           # JSON files (human-reviewable)
│   ├── STRAT-001.json
│   └── ...
├── catalog.db            # SQLite (queryable)
│   ├── entries table
│   ├── validations table
│   ├── regime_performance table
│   └── proposals table
└── generated/            # Generated artifacts
    ├── code/
    └── results/
```

---

### Decision 3: Schema Validation

| Option | Pros | Cons |
|--------|------|------|
| **JSON Schema** | Standard; language-agnostic; existing schemas | Verbose; limited expressiveness |
| **Pydantic** | Pythonic; auto-generates JSON Schema; excellent validation; good IDE support | Python-only |
| **TypeScript types** | If we add web UI later | Not useful for Python backend |

**Recommendation**: **Pydantic** as primary, export to JSON Schema for documentation/external tools.

---

### Decision 4: CLI Framework

| Option | Pros | Cons |
|--------|------|------|
| **Click** | Mature; well-documented; widely used | Decorator-heavy; less type-safe |
| **Typer** | Modern; type-annotated; auto-generates help; built on Click | Newer; smaller community |
| **argparse** | Built-in; no dependencies | Verbose; manual help text |

**Recommendation**: **Typer** for cleaner code and better type integration with Pydantic.

---

### Decision 5: Template Engine

| Option | Pros | Cons |
|--------|------|------|
| **Jinja2** | Powerful; well-known; good for complex templates | Maybe overkill for code gen |
| **String templates** | Simple; no dependencies | Limited features; escaping issues |
| **Custom builder** | Full control; can optimize for our use case | More code to maintain |

**Recommendation**: **Jinja2** for Tier 1/2 templates, with well-defined template contracts.

---

### Decision 6: Testing Framework

| Option | Pros | Cons |
|--------|------|------|
| **pytest** | Current choice; powerful; good plugins | None significant |

**Recommendation**: Keep **pytest**. Add:
- **pytest-golden** for reproducibility tests (same input → same output)
- **hypothesis** for property-based testing of schemas

---

## Core Data Schemas

### Strategy Definition (Tier 1)

```json
{
  "$schema": "strategy-definition-v1.json",
  "schema_version": "1.0",
  "tier": 1,

  "metadata": {
    "id": "STRAT-001",
    "name": "Dual Momentum Rotation",
    "description": "...",
    "source_document": "research/paper.pdf",
    "created_at": "2025-01-08T00:00:00Z",
    "definition_hash": "sha256:abc123..."
  },

  "strategy_type": "momentum_rotation",

  "universe": {
    "type": "fixed",
    "symbols": ["SPY", "EFA", "EEM", "TLT", "GLD"],
    "defensive_symbols": ["TLT", "GLD"]
  },

  "signal": {
    "type": "relative_momentum",
    "lookback_days": 126,
    "selection": {
      "method": "top_n",
      "n": 3
    }
  },

  "filters": [
    {
      "type": "absolute_momentum",
      "condition": "positive",
      "lookback_days": 126
    }
  ],

  "position_sizing": {
    "method": "equal_weight"
  },

  "rebalance": {
    "frequency": "monthly"
  },

  "risk_management": {
    "regime_filter": {
      "enabled": true,
      "indicator": "volatility_proxy",
      "crisis_threshold": 25,
      "crisis_action": "switch_to_defensive"
    }
  }
}
```

### Strategy Definition (Tier 2 - with expressions)

```json
{
  "$schema": "strategy-definition-v1.json",
  "schema_version": "1.0",
  "tier": 2,

  "metadata": {
    "id": "STRAT-042",
    "name": "Fed Policy Adaptive Strategy"
  },

  "data_requirements": [
    {
      "id": "fed_funds",
      "source": "fred",
      "series": "FEDFUNDS",
      "frequency": "daily"
    },
    {
      "id": "yield_curve",
      "source": "fred",
      "series": "T10Y2Y",
      "frequency": "daily"
    }
  ],

  "derived_signals": [
    {
      "id": "fed_tightening",
      "expression": "roc(fed_funds, 90) > 0"
    },
    {
      "id": "curve_inverted",
      "expression": "yield_curve < 0"
    },
    {
      "id": "risk_off_regime",
      "expression": "fed_tightening AND curve_inverted"
    }
  ],

  "allocation_rules": [
    {
      "name": "risk_off",
      "condition": "risk_off_regime",
      "allocation": {
        "TLT": 0.6,
        "GLD": 0.4
      }
    },
    {
      "name": "risk_on",
      "condition": "NOT risk_off_regime",
      "allocation": {
        "SPY": 0.5,
        "QQQ": 0.3,
        "EFA": 0.2
      }
    }
  ],

  "rebalance": {
    "frequency": "monthly",
    "on_signal_change": true
  }
}
```

### Validation Result

```json
{
  "strategy_id": "STRAT-001",
  "strategy_definition_hash": "sha256:abc123...",
  "generated_code_hash": "sha256:def456...",
  "validation_timestamp": "2025-01-08T12:00:00Z",

  "walk_forward_results": [
    {
      "window": "2010-01-01/2012-12-31",
      "metrics": {
        "cagr": 0.12,
        "sharpe": 0.85,
        "max_drawdown": 0.15,
        "win_rate": 0.58
      },
      "regime_tags": {
        "direction": "bull",
        "volatility": "normal",
        "sector_leader": "tech",
        "rate_environment": "falling"
      }
    }
    // ... more windows
  ],

  "aggregate_metrics": {
    "overall": {
      "mean_sharpe": 0.72,
      "sharpe_95_ci": [0.45, 0.99],
      "consistency": 0.83,
      "p_value": 0.02,
      "p_value_adjusted": 0.06
    }
  },

  "regime_performance": {
    "by_direction": {
      "bull": { "mean_sharpe": 0.95, "n_windows": 4 },
      "bear": { "mean_sharpe": 0.25, "n_windows": 1 },
      "sideways": { "mean_sharpe": 0.45, "n_windows": 2 }
    },
    "by_volatility": {
      "high": { "mean_sharpe": 1.10, "n_windows": 2 },
      "normal": { "mean_sharpe": 0.65, "n_windows": 3 },
      "low": { "mean_sharpe": 0.55, "n_windows": 2 }
    }
    // ... more dimensions
  },

  "performance_fingerprint": {
    "best_regimes": ["bull", "high_volatility"],
    "worst_regimes": ["bear"],
    "untested_regimes": ["small_cap_leadership"],
    "recommended_use": "Bull market / high volatility conditions"
  },

  "validation_status": "VALIDATED",
  "confidence": "HIGH"
}
```

### Proposal

```json
{
  "id": "PROP-001",
  "type": "composite_strategy",
  "status": "pending_review",
  "created_at": "2025-01-08T12:00:00Z",
  "created_by": "synthesis_engine",

  "title": "Bull/Bear Regime Switching Strategy",
  "description": "Combine STRAT-001 (bull specialist) with STRAT-042 (bear specialist)",

  "rationale": {
    "gap_identified": "Portfolio has no bear market coverage",
    "proposed_solution": "Switch between strategies based on VIX regime",
    "expected_improvement": "Reduce max drawdown from 35% to 20%"
  },

  "component_strategies": ["STRAT-001", "STRAT-042"],

  "switching_logic": {
    "indicator": "VIX",
    "rules": [
      { "condition": "VIX < 20", "use_strategy": "STRAT-001" },
      { "condition": "VIX >= 20", "use_strategy": "STRAT-042" }
    ]
  },

  "data_requirements_delta": [
    { "needed": "VIX index", "unblocks": "regime switching" }
  ],

  "review_notes": null,
  "reviewed_at": null,
  "reviewed_by": null,
  "decision": null
}
```

---

## Component Details

### Ingestion Engine

**Responsibility**: Extract strategy information from source documents.

**Input**: PDF, code files, markdown, etc.
**Output**: Strategy Definition JSON (Tier 1, 2, or 3 draft)

**Process**:
1. LLM reads document
2. LLM fills strategy definition schema
3. Deterministic code validates schema
4. Deterministic code checks for duplicates
5. If valid and unique → creates catalog entry
6. If duplicate → links to existing entry

**Constraints**:
- LLM can only READ source documents
- LLM must output schema-compliant JSON
- LLM cannot create entries (code does)

### Validation Engine

**Responsibility**: Test strategies rigorously.

**Input**: Strategy Definition JSON
**Output**: Validation Result JSON

**Process**:
1. Code generator creates backtest code (from templates or blocks)
2. Walk-forward analyzer runs backtest on each window
3. Framework ALWAYS injects dates (never from strategy def)
4. Regime tagger labels each window
5. Statistical validator calculates significance
6. Results stored with full version tracking

**Constraints**:
- All parameters (dates, windows) controlled by framework
- Generated code is versioned and immutable after first run
- No LLM in the execution loop

### Analysis Engine

**Responsibility**: Critically assess validation results.

**Input**: Validation Result JSON
**Output**: Analysis JSON (concerns, insights)

**Process**:
1. LLM reads validation results
2. LLM applies analytical personas (risk manager, quant, etc.)
3. LLM outputs structured assessment
4. Code stores assessment, extracts proposals to queue

**Constraints**:
- LLM is read-only
- LLM outputs structured JSON
- Proposals go to queue, not directly to catalog

### Synthesis Engine

**Responsibility**: Find patterns across portfolio.

**Input**: All validated strategies + regime fingerprints
**Output**: Synthesis insights + composite proposals

**Process**:
1. LLM analyzes full portfolio
2. Identifies correlations, gaps, opportunities
3. Proposes combinations with switching logic
4. Identifies data acquisition priorities
5. All proposals go to queue

**Constraints**:
- LLM is read-only
- Cannot create entries
- All output is proposals for human review

### Enhancement Engine

**Responsibility**: Explore ways to improve validated strategies through leverage, options, futures, or position sizing.

**Input**: Validated strategy + validation results
**Output**: Enhancement proposals

**Trigger**: When a strategy validates successfully on the underlying (e.g., SPY ETF).

**Enhancement Types**:

| Type | Description | Example |
|------|-------------|---------|
| **Leverage** | Apply multipliers to base strategy | 1.5x, 2x, 3x via leveraged ETFs or margin |
| **Options Overlay** | Add options strategies on top | Covered calls for income, protective puts for downside |
| **Options Replacement** | Replace underlying with options | Buy calls instead of stock for defined-risk leverage |
| **Futures Implementation** | Use futures instead of ETFs | ES futures vs SPY (capital efficiency, tax advantages) |
| **Position Sizing** | Optimize allocation methodology | Kelly criterion, risk parity, volatility targeting |

**Process**:
1. Strategy validates successfully on underlying (e.g., SPY)
2. Enhancement engine analyzes the strategy characteristics
3. Generates relevant enhancement proposals:
   - If high Sharpe → explore leverage to amplify returns
   - If high volatility → explore options overlays to reduce risk
   - If capital-intensive → explore futures for efficiency
4. Each variant becomes a proposal for human review
5. Approved proposals get validated through same pipeline
6. Compare risk/return profiles across variants

**Example Enhancement Proposals**:

```
Original: STRAT-001 (Momentum on SPY)
│
├── STRAT-001-LEV2: Apply 2x leverage via SSO
│   └── Expected: Higher returns, higher drawdown
│
├── STRAT-001-CC: Add covered call overlay (30-delta monthly)
│   └── Expected: Reduced volatility, capped upside, income
│
├── STRAT-001-PP: Add protective put (20-delta quarterly)
│   └── Expected: Reduced drawdown, reduced returns
│
├── STRAT-001-COLLAR: Covered call + protective put
│   └── Expected: Defined risk/reward band
│
├── STRAT-001-FUT: Implement via ES futures
│   └── Expected: Capital efficiency, 60/40 tax treatment
│
└── STRAT-001-VOLTGT: Apply volatility targeting (12% annual)
    └── Expected: More consistent risk profile
```

**Goal**: Maximize risk-adjusted returns. Find the optimal implementation for each validated strategy.

**Constraints**:
- Only triggered for validated strategies
- All variants go through full walk-forward validation
- Human approves which variants to explore
- Clear lineage tracking (parent → enhancement)
- Must document trade-offs (higher return vs higher risk)

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                       │
└─────────────────────────────────────────────────────────────────────────────┘

Source Document
      │
      ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  INGESTION  │────▶│  Strategy   │────▶│   CATALOG   │
│   ENGINE    │     │ Definition  │     │   ENTRY     │
│   (LLM)     │     │   (JSON)    │     │  (SQLite)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  Generated  │◀────│ VALIDATION  │
                    │    Code     │     │   ENGINE    │
                    │  (Python)   │     │   (Code)    │
                    └─────────────┘     └──────┬──────┘
                                               │
                           ┌───────────────────┼───────────────────┐
                           │                   │                   │
                           ▼                   ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
                    │ Window 1    │     │ Window 2    │     │ Window N    │
                    │ Results     │     │ Results     │     │ Results     │
                    └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
                           │                   │                   │
                           └───────────────────┼───────────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  REGIME     │
                                        │  TAGGER     │
                                        └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ STATISTICAL │
                                        │ VALIDATOR   │
                                        └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ Validation  │
                                        │  Result     │
                                        │  (JSON)     │
                                        └──────┬──────┘
                                               │
                           ┌───────────────────┴───────────────────┐
                           │                                       │
                           ▼                                       ▼
                    ┌─────────────┐                          ┌─────────────┐
                    │  ANALYSIS   │                          │  SYNTHESIS  │
                    │   ENGINE    │                          │   ENGINE    │
                    │   (LLM)     │                          │   (LLM)     │
                    └──────┬──────┘                          └──────┬──────┘
                           │                                       │
                           ▼                                       ▼
                    ┌─────────────┐                          ┌─────────────┐
                    │  Analysis   │                          │  Synthesis  │
                    │   (JSON)    │                          │   (JSON)    │
                    └──────┬──────┘                          └──────┬──────┘
                           │                                       │
                           └───────────────────┬───────────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  PROPOSAL   │
                                        │   QUEUE     │
                                        └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   HUMAN     │
                                        │   REVIEW    │
                                        └──────┬──────┘
                                               │
                              ┌────────────────┼────────────────┐
                              │                │                │
                              ▼                ▼                ▼
                         [APPROVE]         [REJECT]         [DEFER]
                              │                │                │
                              ▼                ▼                ▼
                    ┌─────────────┐     ┌─────────────┐  Stays in
                    │ Create New  │     │    Log      │   Queue
                    │   Entry     │     │  Decision   │
                    └─────────────┘     └─────────────┘
```

---

## Implementation Phases

### Phase 0: Setup & Foundation
- [ ] Create GitHub project board
- [ ] Define issue templates
- [ ] Set up CI/CD pipeline
- [ ] Create branch protection rules

### Phase 1: Core Schemas & Data Layer
- [ ] Define Pydantic models for all schemas
- [ ] Set up SQLite database schema
- [ ] Implement catalog CRUD operations
- [ ] Add schema validation tests

### Phase 2: Code Generation (Tier 1)
- [ ] Design template structure for momentum strategies
- [ ] Implement template engine
- [ ] Build code generator with date injection (framework-controlled)
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
- [ ] Implement analysis engine (LLM with constraints)
- [ ] Implement synthesis engine
- [ ] Build proposal queue
- [ ] Create review CLI commands

### Phase 6: Tier 2 Support
- [ ] Define expression language
- [ ] Implement expression parser
- [ ] Build block combiner
- [ ] Add external data support

### Phase 7: Testing & Documentation
- [ ] Comprehensive test suite
- [ ] User documentation
- [ ] API documentation
- [ ] Example workflows

---

## Finalized Decisions

### 1. Walk-Forward Window Configuration

**Decision**: 3-year windows (default), configurable.

**Rationale**:
- 3 years provides ~750 trading days - enough for statistical significance
- With data from 2010-2024, yields 5 non-overlapping windows
- Configurable via CLI flag `--window-years` for advanced users
- Minimum 2 years enforced to prevent overfit detection

**Windows (default)**:
```
Window 1: 2010-01-01 to 2012-12-31
Window 2: 2013-01-01 to 2015-12-31
Window 3: 2016-01-01 to 2018-12-31
Window 4: 2019-01-01 to 2021-12-31
Window 5: 2022-01-01 to 2024-12-31
```

---

### 2. Regime Definitions

**Decision**: Multi-dimensional regime tagging using established indicators.

| Dimension | Indicator | Thresholds |
|-----------|-----------|------------|
| **Market Direction** | SPY position vs 200-day SMA | Bull: >5% above; Bear: >5% below; Sideways: within 5% |
| **Volatility** | VIX level | Low: <15; Normal: 15-25; High: >25 |
| **Rate Environment** | 10Y Treasury 6-month change | Rising: >50bps; Falling: <-50bps; Flat: within 50bps |
| **Sector Leadership** | Best performing sector (trailing 3mo) | Tech/Energy/Healthcare/Financials/etc. |
| **Cap Leadership** | IWM/SPY relative performance | Small: IWM > SPY by 5%; Large: SPY > IWM by 5% |

**Rationale**:
- Uses widely available, liquid instruments
- Thresholds based on historical norms
- Objective, reproducible calculations

---

### 3. Expression Language (Tier 2)

**Decision**: Simple DSL with predefined functions, not full Python.

**Syntax**:
```
// Supported operators
AND, OR, NOT, >, <, >=, <=, ==, !=, +, -, *, /

// Supported functions
sma(series, period)      // Simple moving average
ema(series, period)      // Exponential moving average
roc(series, period)      // Rate of change (percentage)
rsi(series, period)      // RSI indicator
std(series, period)      // Standard deviation
max(series, period)      // Rolling max
min(series, period)      // Rolling min
cross_above(a, b)        // True when a crosses above b
cross_below(a, b)        // True when a crosses below b

// Example expressions
"roc(spy, 126) > 0"                              // 6-month momentum positive
"sma(spy, 50) > sma(spy, 200)"                   // Golden cross
"rsi(spy, 14) < 30 AND vix > 25"                 // Oversold in high vol
```

**Rationale**:
- Full Python would be a security risk and reproducibility nightmare
- Simple DSL covers 90%+ of Tier 2 needs
- Parser is deterministic and auditable
- Can extend functions as needed

---

### 4. Tier 3 Review Process

**Decision**: Always require human review for custom code.

**Process**:
1. LLM generates custom code draft
2. Code stored with `review_required: true` flag
3. Human reviews via `research review CODE-123` command
4. Options: Approve / Request Changes / Reject
5. Only approved code enters validation pipeline

**Rationale**:
- Custom code can contain subtle bugs, look-ahead bias, etc.
- Safety over convenience for the 10% of strategies needing this
- Review queue prevents blocking; human gets to it when available

---

### 5. External Data Integration

**Decision**: Start with FRED, add others incrementally.

**Phase 1 Sources**:
| Source | Data Types | Priority |
|--------|------------|----------|
| **FRED** | Macro (rates, GDP, employment, etc.) | HIGH |
| **Yahoo Finance** | Price data fallback | MEDIUM |
| **Quandl** | Alternative data | FUTURE |

**Data Quality Handling**:
- Validate date ranges before backtest
- Flag missing data periods
- Block strategies if required data unavailable
- Store data provenance (source, fetch date, version)

**Rationale**:
- FRED is free, reliable, has comprehensive macro data
- Most Tier 2 strategies need macro data for regime detection
- Yahoo is backup for price data edge cases

---

### 6. Multiple Testing Correction

**Decision**: FDR (Benjamini-Hochberg) as default, configurable.

| Method | Description | Use Case |
|--------|-------------|----------|
| **FDR (default)** | Controls false discovery rate at 5% | Exploratory research |
| **Bonferroni** | Very conservative | Final deployment decisions |
| **None** | Raw p-values | Understanding raw statistics |

**Rationale**:
- Bonferroni too conservative for exploration (would reject most strategies)
- FDR provides good balance - expect ~5% of "significant" results to be false positives
- User can switch to Bonferroni for final deployment decisions via `--correction bonferroni`

---

## Next Steps

1. **Review this document** and discuss open questions
2. **Finalize technology decisions** (confirm Python + SQLite hybrid)
3. **Create GitHub issues** for Phase 1 tasks
4. **Begin implementation** with core schemas

---

*Document created: 2025-01-08*
*Last updated: 2025-01-08*
