# Research-Kit User Journeys

Practical workflows for using research-kit.

---

## The Two Processes

Research-kit runs two main processes:

### Process 1: Ingestion (Inbox → Catalog)

```
inbox/
├── strategy.pdf
├── indicator.py
└── idea.html
        │
        ▼
research ingest process
        │
        ▼
catalog/
├── STRAT-001 (UNTESTED)
├── IND-001 (UNTESTED)
└── IDEA-001 (BLOCKED - missing data)
```

**This process is solid.** It walks all files, extracts ideas, deduplicates, and builds your catalog.

### Process 2: Validation + Expert Loop (The Core)

```
For each UNTESTED item in catalog:
    │
    ├── 1. Code it (generate backtest)
    ├── 2. Test it (IS + OOS via lean)
    ├── 3. Expert review (on real results)
    │      ├── Critical assessment
    │      ├── Improvement ideas
    │      └── New ideas → back to catalog
    └── 4. Mark result (VALIDATED/INVALIDATED)
```

**This process runs via `research run`.** It's deterministic - code drives, Claude provides analysis.

---

## Journey 1: First Time Setup

You have research files you want to evaluate.

```bash
# 1. Initialize workspace
$ research init ~/research-project --name "Trading Research"
Initialized workspace at /Users/you/research-project

# 2. Copy your files to inbox
$ cp -r ~/my-research-files/* ~/research-project/inbox/

# 3. Process into catalog
$ research ingest process
Processing inbox (47 files)...

  [1/47] momentum-strategy.pdf
      -> STRAT-001 (UNTESTED)

  [2/47] custom-indicator.py
      -> IND-001 (UNTESTED)

  [3/47] sentiment-idea.html
      -> IDEA-001 (BLOCKED: missing sentiment_data)
  ...

Complete: 42 entries created, 5 skipped

# 4. Check what you have
$ research catalog stats
UNTESTED:    35
BLOCKED:      7
TOTAL:       42

# 5. Start validating
$ research run
```

---

## Journey 2: Daily Validation Work

Run the validation loop on your catalog.

```bash
# Process everything that's ready
$ research run

[1/35] STRAT-001: Momentum Strategy
       IS Results: CAGR 12.3%, Sharpe 0.8, Alpha +2.1%
       OOS Results: CAGR 8.1%, Sharpe 0.6, Alpha +1.2%
       Expert Review: 4 personas analyzed
       → VALIDATED
       → Added 2 derived ideas

[2/35] STRAT-002: Mean Reversion
       IS Results: CAGR 4.2%, Sharpe 0.3, Alpha -1.1%
       IS Gates: FAILED (negative alpha)
       → INVALIDATED (skipped OOS - IS failed)

...

Complete: 35 processed
  VALIDATED:    8
  INVALIDATED: 24
  DERIVED:      19 new ideas added
```

---

## Journey 3: Single Item Validation

Test one specific strategy.

```bash
$ research run STRAT-309

STRAT-309: Forex Fandango
──────────────────────────────────────────────────────
Generating backtest code...
Running IS backtest (2015-2020)...

IS Results:
  CAGR: 20.3%  |  Sharpe: 0.66  |  Max DD: -43.2%
  Alpha vs SPY: +4.9%

Running OOS backtest (2021-2024)...

OOS Results:
  CAGR: 5.9%   |  Sharpe: 0.20  |  Max DD: -64.4%
  Alpha vs SPY: -9.8%

OOS Gates: FAILED

Expert Review:
  [Risk Manager] 64% drawdown unacceptable...
  [Quant] IS/OOS divergence suggests overfitting...
  [Contrarian] Bond-equity correlation broke...
  [Ideator] Try removing TMF, add rate filter...

──────────────────────────────────────────────────────
DETERMINATION: INVALIDATED

Derived ideas:
  IDEA-047: Forex Fandango without TMF
  IDEA-048: Forex Fandango with rate regime filter
```

---

## Journey 4: Unblocking Strategies

Some strategies need data that QC doesn't have.

```bash
# 1. See what's blocked
$ research catalog list --status BLOCKED
STRAT-015  Breadth Momentum    (missing: nyse_breadth)
STRAT-023  Sentiment Strategy  (missing: aaii_sentiment)

# 2. Check what a specific strategy needs
$ research data check STRAT-015
Missing: nyse_breadth
Required columns: date, advances, declines

# 3. Add your data
$ research data add \
    --id nyse_breadth \
    --name "NYSE Breadth Data" \
    --path ./my-breadth-data.csv

Registered: nyse_breadth
STRAT-015: BLOCKED → UNTESTED

# 4. Now you can run it
$ research run STRAT-015
```

---

## Journey 5: Checking Progress

See where you stand.

```bash
$ research catalog stats

┌─────────────────────────────────────┐
│ CATALOG STATUS                      │
├─────────────────────────────────────┤
│ VALIDATED      │  12  (24%)         │
│ INVALIDATED    │  28  (56%)         │
│ UNTESTED       │   5  (10%)         │
│ BLOCKED        │   3  (6%)          │
│ IN_PROGRESS    │   2  (4%)          │
├─────────────────────────────────────┤
│ TOTAL          │  50                │
│ DERIVED IDEAS  │  31  (pending)     │
└─────────────────────────────────────┘

Top validated strategies:
1. STRAT-007: Multi-Asset Momentum (Sharpe 1.2, Alpha 4.3%)
2. STRAT-019: VIX Regime Switch (Sharpe 0.9, Alpha 2.8%)
3. STRAT-033: Sector Rotation (Sharpe 0.8, Alpha 2.1%)
```

---

## Journey 6: The Feedback Loop

Derived ideas from expert review become new catalog entries.

```bash
# Original strategy failed
$ research run STRAT-001
...
DETERMINATION: INVALIDATED
Derived ideas:
  IDEA-001: STRAT-001 with VIX filter
  IDEA-002: STRAT-001 with weekly rebalance

# Later, run the derived ideas
$ research run IDEA-001
...
DETERMINATION: VALIDATED  # The improvement worked!

# The catalog grows into a tree
$ research catalog list --derived-from STRAT-001
STRAT-001 (INVALIDATED)
├── IDEA-001 (VALIDATED) ← VIX filter helped!
├── IDEA-002 (INVALIDATED)
└── IDEA-003 (UNTESTED)
```

---

## Quick Reference

```bash
# Setup (once)
research init ~/workspace

# Add files (occasionally)
cp files/* ~/workspace/inbox/
research ingest process

# Add data (when needed)
research data add --id X --path Y

# THE CORE LOOP (daily)
research run                    # All items
research run STRAT-001          # Single item

# Check progress
research catalog stats
research catalog list --status VALIDATED
```

---

## Ultimate Goal

```
Raw Research Files
        │
        ▼
    Ingestion
        │
        ▼
     Catalog
        │
        ▼
  Validation Loop ◄────┐
        │              │
        ▼              │
  Expert Review        │
        │              │
        ├─► Derived Ideas
        │
        ▼
Rock Solid Strategies
        │
        ▼
   Live Trading
```
