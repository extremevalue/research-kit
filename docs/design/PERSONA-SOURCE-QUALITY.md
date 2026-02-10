# Persona Perspectives: Source Quality and Ingestion Filtering

**Date:** 2026-01-23

---

## The Question

Given that research-kit ingests strategies from expert podcasts, research documents, and practitioner insights — what separates signal from noise? What should be captured during ingestion?

---

## Universal Consensus

All personas agreed on these points:

### 1. Economic Rationale is Mandatory

Every persona emphasized: **If you can't explain WHY the edge exists, it probably doesn't.**

Valid rationale categories:
- **Structural**: Index rebalancing, regulatory constraints, liquidity provision
- **Behavioral**: Loss aversion, herding, anchoring, overreaction
- **Informational**: Processing speed, specialized data, expertise barriers
- **Risk Premium**: Getting paid to bear risk others avoid

### 2. Source Credibility Hierarchy

```
Most Trustworthy:
├── Practitioner sharing something they STOPPED using (no incentive to mislead)
├── Academic paper with out-of-sample period including recent data
├── Fund manager explaining WHY (mechanism), not just THAT it works
└── Practitioner with verifiable track record and skin in game

Least Trustworthy:
├── Anyone selling courses/signals/newsletters
├── Podcast claims without specific rules
├── "I backtested this and it returned 400%"
└── Blog posts without code/data
```

### 3. The Base Rate is Low

> "The base rate for published strategies being genuinely profitable after costs and decay is probably 5-10%." — Statistician

> "95%+ of strategies you ingest will be noise. Your system's primary job is rejection, not discovery." — Failure Analyst

---

## What to Capture During Ingestion

### Mandatory Fields (Reject if Missing)

| Field | Why It Matters |
|-------|----------------|
| **Exact Entry/Exit Rules** | Must be unambiguous enough to code |
| **Universe Definition** | Which instruments? "Stocks" is too vague |
| **Position Sizing** | Equal weight? Volatility-scaled? This changes everything |
| **Time Period of Claims** | To check for survivorship bias, regime dependence |
| **Economic Rationale** | No mechanism = no conviction during drawdowns |
| **Transaction Cost Assumptions** | Many strategies die here |

### The "Why" Framework (Critical Addition)

For each strategy, force completion of this sentence:

> "This strategy works because **[AGENT]** does **[BEHAVIOR]** due to **[CONSTRAINT/BIAS]**, creating predictable **[PRICE PATTERN]** that persists because **[REASON IT WON'T BE ARBITRAGED]**."

**Good Example:**
> "This strategy works because **index funds** do **mechanical rebalancing** due to **mandate constraints**, creating predictable **end-of-quarter price pressure** that persists because **the funds can't change their behavior**."

**Red Flag Example:**
> "This strategy works because **prices** do **mean reversion** due to **unknown reasons**, creating predictable **profits** that persist because **it backtested well**."

### Extended Capture Schema

```yaml
strategy_ingestion:
  # IDENTITY
  source_type: [academic|podcast|blog|practitioner|personal]
  source_url: string
  date_published: date

  # SOURCE CREDIBILITY
  author_track_record: [verified_fund_manager|academic|retail|unknown]
  author_skin_in_game: boolean  # Are they actually trading this?
  author_conflicts: string  # Selling courses? Raising capital?

  # THE STRATEGY
  asset_class: [equity|fx|rates|crypto|commodities|multi]
  strategy_type: [momentum|mean_reversion|carry|value|volatility|event|other]
  time_horizon: string
  rebalance_frequency: [daily|weekly|monthly|quarterly]

  # THE EDGE (Critical)
  edge_mechanism: string  # What drives returns
  edge_why_exists: string  # Economic rationale
  edge_counterparty: string  # Who's on the other side losing
  edge_why_persists: string  # Why not arbitraged away
  edge_decay_conditions: string  # When will it stop working

  # IMPLEMENTATION REALITY
  universe_size: integer
  estimated_capacity_usd: integer
  transaction_cost_assumptions: string
  execution_requirements: string

  # CLAIMED PERFORMANCE
  claimed_sharpe: float | null
  claimed_cagr: float | null
  claimed_max_drawdown: float | null
  sample_period: date_range | null
  is_out_of_sample: boolean
  survivorship_bias_addressed: boolean

  # SPECIFICITY SCORE (0-8)
  has_entry_rules: boolean
  has_exit_rules: boolean
  has_position_sizing: boolean
  has_universe_definition: boolean
  has_backtest_period: boolean
  has_out_of_sample: boolean
  has_transaction_costs: boolean
  has_code_or_pseudocode: boolean

  # RED FLAGS (auto-populated)
  red_flags: list[string]
  red_flag_count: integer

  # TRIAGE
  priority: [backtest_immediately|queue|archive|reject]
  rejection_reason: string | null
```

---

## Red Flags for Immediate Rejection

### Hard Rejects (All Personas Agreed)

| Red Flag | Why It's Fatal |
|----------|----------------|
| **Sharpe > 2.0-3.0 without HFT context** | Almost certainly curve-fit or fraud |
| **"Works in all market conditions"** | No strategy does. This is marketing |
| **No drawdown discussed** | Hiding the pain |
| **No transaction costs** | Most strategies die here |
| **No out-of-sample period** | Assume overfitting |
| **Backtest starts at convenient date** | March 2009 starts are cherry-picked |
| **No economic rationale** | "It just works" = it won't |
| **Excessive parameters (>5)** | Overfitting machine |
| **Look-ahead bias** | Using data unavailable at decision time |
| **Survivorship bias** | Testing on current constituents historically |
| **Author selling something** | Courses/newsletters = massive bias |
| **Sample size < 30 independent observations** | Statistically meaningless |

### Soft Warnings (Investigate Further)

| Warning | Action |
|---------|--------|
| Only tested in US equities | Require cross-market validation |
| Only tested 2010-2020 | Require crisis period testing |
| Strategy stopped being discussed | Maybe it stopped working |
| Requires leverage > 3x | Proceed with extreme caution |
| Author has pivoted to education | May have given up on trading |

### Source-Specific Red Flags

**Podcasts:**
- Speaking in generalities when pressed for specifics
- Story changes between appearances
- Only discusses winners
- "I can't share the exact rules but..."

**Academic Papers:**
- Monthly rebalancing assumed (unrealistic execution)
- Statistical significance without economic significance
- No transaction cost analysis
- Factor zoo papers (400+ factors discovered)

**Blogs:**
- Cherry-picked charts
- No accountability for wrong predictions
- Content designed to attract, not inform

---

## Scoring System

### Specificity Score (0-8)

```python
def calculate_implementability(strategy):
    """Can we actually backtest this?"""
    checks = [
        strategy.has_entry_rules,
        strategy.has_exit_rules,
        strategy.has_position_sizing,
        strategy.has_universe_definition,
        strategy.has_backtest_period,
        strategy.has_out_of_sample,
        strategy.has_transaction_costs,
        strategy.has_code_or_pseudocode,
    ]
    return sum(checks)
```

**Threshold:** Score < 4 = archive, don't waste backtest compute.

### Trust Score (Veteran Quant's Formula)

```
Trust Score = (
    Economic_Rationale_Score (0-30) +
    Out_of_Sample_Evidence (0-25) +
    Implementation_Realism (0-20) +
    Source_Credibility (0-15) +
    Novelty (0-10)
) - (Red_Flag_Count * 15)
```

**Threshold:** Only proceed to walk-forward testing if Trust Score > 50.

### Quality Score (First Principles Framework)

```
STRATEGY QUALITY SCORE (0-100)

Mechanism Clarity:     /25  (Can you explain WHY it works?)
Source Credibility:    /20  (Track record, incentives, transparency)
Testability:           /20  (Precise enough to code unambiguously?)
Realistic Assumptions: /15  (Costs, liquidity, capacity addressed?)
Falsifiability:        /10  (What would disprove it?)
Novelty vs. Known:     /10  (New alpha or repackaged factor?)
```

**Thresholds:**
- Score > 80: Test first
- Score 60-80: Queue for backtest
- Score < 60: Archive with reason

---

## Ingestion Pipeline

```
STAGE 1: TRIAGE (< 5 minutes)
├── Red flag check → Fail → Reject
├── Source credibility check → Fail → Reject
├── Economic rationale present? → No → Reject
└── Pass → Stage 2

STAGE 2: DOCUMENTATION (30 minutes)
├── Fill out capture schema
├── Calculate specificity score
├── Specificity < 4? → Archive
└── Pass → Stage 3

STAGE 3: SCORING
├── Calculate trust/quality score
├── Score < threshold? → Archive
└── Pass → Backtest Queue (ranked by score)
```

---

## Key Insights by Persona

### Veteran Quant
> "The best strategies are often the simplest ones that exploit a structural edge with disciplined execution. If a podcast guest spends 45 minutes explaining their strategy, it's probably not as good as the one where someone says: 'We buy stocks getting added to the S&P 500 three days before and sell on inclusion. That's it.'"

### Skeptic
> "The ingestion system is only as good as the rejection rate. If you're not throwing out 90%+ of what you ingest, you're not being skeptical enough."

### Experienced Trader
> "A complete set of rules from someone who's never traded is worth less than a rough framework from someone who's been in the trenches."

### Statistician
> "The base rate for published strategies being genuinely profitable after costs and decay is probably 5-10%. Your ingestion system's job is Bayesian filtering—raising the prior on candidates you actually test to something meaningful like 30-40%."

### First Principles
> "The most valuable signal from any source isn't the strategy itself — it's the mechanism. Strategies decay; understanding of market structure compounds."

### Startup CTO
> "Most strategies fail backtesting anyway. Your real efficiency gain isn't better filtering — it's faster rejection during backtesting. Optimize for 'fast fail' in backtest phase."

### Failure Analyst
> "What people share publicly is either: (1) no longer working, (2) incomplete, (3) capacity-constrained, or (4) wrong. The traders I've seen fail weren't undone by bad strategies — they were undone by insufficient skepticism."

---

## Decision: Schema Updates for Research-Kit

Based on this analysis, add to ingestion:

**Required Fields:**
1. `edge_mechanism` — What drives returns
2. `edge_why_exists` — Economic rationale
3. `edge_counterparty` — Who's losing
4. `edge_why_persists` — Why not arbitraged
5. `edge_decay_conditions` — When will it stop working

**Scoring:**
1. Specificity score (0-8, reject < 4)
2. Trust/quality score (reject < 50-60)
3. Red flag count (each flag = -15 points)

**Pipeline:**
1. Fast triage (< 5 min)
2. Documentation (30 min for survivors)
3. Scoring and prioritization
4. Backtest queue (ranked by score)
