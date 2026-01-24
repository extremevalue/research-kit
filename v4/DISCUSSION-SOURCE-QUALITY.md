# Discussion: Source Quality and the "Why"

**Date:** 2026-01-23

---

## The Question

Is sourcing strategies from expert podcasts, research documents, and practitioner insights fundamentally different from what the personas recommended?

---

## The Answer: No, It's Not Different

The personas themselves recommend using external sources:

| Persona | Sources They'd Use |
|---------|-------------------|
| Veteran Quant | SSRN, AQR research library, Alpha Architect, Quantpedia |
| Statistician | Academic papers (Fama-French, Jegadeesh-Titman, etc.) |
| Startup CTO | Literature, practitioner blogs, QuantConnect forums |
| Experienced Trader | Trading books, observation journals |

The Statistician explicitly said: "Don't reinvent the wheel."

---

## The Real Concern: Quality, Not Source

The skeptical concerns weren't about using external sources. They were:

1. **"If you can find it easily, so can everyone else"** — Some strategies are already arbitraged
2. **"Most podcast strategies don't survive costs"** — Transaction costs kill most edges
3. **"What if the pile is noise?"** — Filtering noise efficiently still produces noise

These are **filtering problems**, not source problems.

---

## What's Missing: The "Why"

Every persona emphasized capturing the economic rationale:

> "If you can't explain WHY the edge exists and who's on the other side losing money, it probably doesn't work."

**Current ingestion captures:**
- Entry rules (WHAT)
- Exit rules (WHAT)
- Position sizing (WHAT)
- Universe (WHAT)

**What should also be captured:**
- Economic rationale (WHY)
- Counterparty (WHO is losing)
- Persistence explanation (WHY hasn't it been arbitraged)
- Decay conditions (WHEN will it stop working)

---

## Example: The Difference

**WHAT only:**
> "Buy when RSI < 30, sell when RSI > 70"

**WHAT + WHY:**
> "Buy when RSI < 30 because retail traders panic sell, creating predictable overshoots. Institutions and patient capital buy these overshoots. The edge persists because it requires holding through uncomfortable drawdowns. It will decay if retail participation decreases or if too many algos front-run the signal."

The WHY is what separates strategies worth testing from noise.

---

## Decision

**Add to ingestion requirements:**

1. `economic_rationale` — Why does this edge exist? (behavioral, structural, informational)
2. `counterparty` — Who is on the other side of this trade? Why are they losing?
3. `persistence_reason` — Why hasn't this been arbitraged away?
4. `decay_conditions` — Under what conditions should this stop working?

These fields should be:
- Required for ingestion (or flagged as incomplete)
- Used as quality signals in validation prioritization
- Reviewed by personas during Learn phase

---

## Next Step

Ask personas directly: Given that research-kit ingests strategies from expert podcasts, research documents, and practitioner insights — what would make you trust those sources? What separates signal from noise?

---

## Design Decision: Rationale Inference (2026-01-23)

### The Question

When a strategy is ingested and the source doesn't clearly state the "WHY" behind it, should we:
- A) Reject the strategy
- B) Have sub-agents try to infer the rationale
- C) Process anyway and let validation determine if it works

### The Decision: Option B+C — Infer and Track Provenance

**Rationale for this decision:**

1. **The WHY can exist even if unstated.** A trader might share something that works without articulating the economic theory. Rejecting based on articulation quality ≠ rejecting based on edge quality.

2. **Validation is the actual test.** If a strategy survives rigorous walk-forward validation with realistic costs, it works. The market doesn't care about our explanations.

3. **Asymmetric risk.** Cost of missing a good strategy (lost alpha) > Cost of processing noise (compute time). If compute runs in background, be inclusive.

4. **Sub-agents can add value.** Connecting strategies to known factors/anomalies is useful work that enriches the strategy document.

### Implementation

```
Source material arrives
    │
    ▼
Extract stated rationale (if any)
    │
    ├── Rationale clear? → Mark as "source_stated"
    │
    ├── Rationale partial? → Sub-agent enhances → Mark as "source_enhanced"
    │
    └── Rationale absent? → Sub-agent researches:
        │
        ├── Match to known factor/anomaly? → Mark as "inferred" + confidence
        │
        └── No match found? → Mark as "unknown" (STILL PROCESS!)
```

### Provenance Tracking

```yaml
edge:
  provenance:
    source: source_stated | source_enhanced | inferred | unknown
    confidence: high | medium | low
    research_notes: "How was rationale determined?"
    factor_alignment: "Which known factor does this resemble?"
    factor_alignment_tested: boolean  # Did returns correlate with the factor?
```

### Trust Calibration

- `source_stated` with high confidence → Standard validation bar
- `inferred` with medium confidence → Standard validation, extra scrutiny
- `unknown` → Still validate, but human review before deployment

### Key Principle

> "No economic rationale" is NOT a hard rejection. Validation is the real test.
> The market doesn't care about our explanations.
> But we track provenance so trust can be calibrated appropriately downstream.
