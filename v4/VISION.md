# Research-Kit V4: Vision

## The Objectives (In Priority Order)

1. **Make money trading**
2. **Don't lose money**
3. **Figure out which strategies actually work** from a mountain of "maybes"

Everything else serves these objectives.

## What We're Building

A **filter** that separates strategies that work from strategies that don't — before you risk real capital.

You have a pile of potential strategies from podcasts, papers, ideas, old notes. You don't know which ones work. Testing them all manually would take forever. Testing them badly loses you money.

Research-kit's job:
- **Filter out the losers** before you risk capital
- **Surface the winners** with enough rigor that you trust them
- **Extract value from everything** — even failures contribute to finding winners

The end state isn't "a nice catalog of strategies." The end state is **you trading validated strategies and making money.**

## Why We're Building It

### The Problem

1. **Too many potential strategies, not enough time** — podcasts, papers, notes, conversations
2. **No way to know what works without risking capital** — validation is manual, inconsistent, easy to introduce biases
3. **Failed strategies are wasted** — they disappear without extracting insights
4. **Previous iterations failed** — Claude went off-script, edited files directly, bypassed rigor

### The Solution

A pipeline that:
- **Ingests** ideas from any source and structures them
- **Validates** strategies through rigorous walk-forward backtesting
- **Learns** from both successes and failures
- **Generates** new ideas by combining insights

All while ensuring Claude can't bypass the verification gates.

## The Hypothesis: LLM Personas as Research Team

A core hypothesis we're testing: **Claude Code / LLMs taking on different personas can extract more value from strategy data than traditional analysis alone.**

The idea:
- Different personas (expert trader, statistician, contrarian, etc.) look at the same data from different angles
- They think creatively about what could work
- They think critically about what's wrong
- They find patterns and combinations a single perspective would miss
- They surface ideas that lead to better strategies

If this hypothesis is right, the system gets smarter over time — failed strategies teach us something, personas generate ideas, those ideas get validated, and the cycle compounds.

If this hypothesis is wrong, we've at least built a rigorous validation pipeline. But we believe the personas add real value beyond just filtering.

## Core Principles

### 1. Claude Proposes, System Verifies

Claude does the heavy lifting (extraction, analysis, idea generation). But verification tests are mandatory gates that can't be skipped.

### 2. Semantic Documents, Not Templates

Strategies are captured as rich documents describing WHAT they do — not forced into rigid templates that limit expressiveness.

### 3. Verification Before Validation

Every strategy must pass verification tests (look-ahead bias, position sizing, etc.) before consuming QC resources.

### 4. Learn From Everything

Failed strategies are data. Extract learnings. Generate new ideas. Nothing is wasted.

### 5. Sub-Agents Protect Context

Heavy lifting happens in sub-agents. Main conversation stays lightweight. Prevents context degradation that caused previous failures.

## The User Experience

```
You: "I have a podcast transcript about dividend capture strategies"

[Drop file in inbox]

You: research ingest ~/inbox/podcast.txt

System: Extracted 2 strategies:
  - STRAT-047: Dividend capture with covered calls
  - STRAT-048: Dividend aristocrat momentum
  Both added as PENDING.

You: research validate --all-pending

System: Running verification tests...
  STRAT-047: Passed
  STRAT-048: Passed

  Running walk-forward validation (12 windows)...
  STRAT-047: VALIDATED (Sharpe 0.52, 75% consistency)
  STRAT-048: INVALIDATED (Sharpe 0.18, failed gates)

You: research learn --since today

System: Persona review complete.

  Learnings:
  - Covered calls improve dividend capture returns
  - Pure dividend momentum insufficient edge

  Ideas generated:
  - IDEA-031: Combine dividend capture + momentum filter

You: research approve IDEA-031

System: Created STRAT-049 from IDEA-031. Status: PENDING.
```

## What Success Looks Like

1. **Strategies that pass validation are trustworthy** — rigorous methodology, no biases
2. **Failed strategies teach us something** — learnings extracted, ideas generated
3. **Claude can't corrupt the process** — verification gates are mandatory
4. **Complex strategies are supported** — options, pairs, regime-adaptive, not just SMA crossovers
5. **The system improves over time** — learnings accumulate, ideas compound

## What We're NOT Building

- A trading system (execution, live trading)
- A portfolio optimizer
- A data provider
- A replacement for human judgment on final decisions
