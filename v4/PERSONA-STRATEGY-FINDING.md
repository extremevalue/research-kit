# Persona Perspectives: How to Find Winning Strategies

**Date:** 2026-01-23

---

## The Question

If pushed to find a winning trading strategy from scratch, what exactly would each persona do?

---

## Universal Process (All Personas Converged Here)

```
1. Start with WHY (economic rationale, not patterns)
2. Use existing research (don't reinvent the wheel)
3. Test simply, validate ruthlessly
4. Paper trade, then tiny real money
5. Track everything, kill fast
```

---

## Persona-Specific Approaches

### Veteran Quant (20+ years at hedge funds)

**Starting point:** Get 20 years of clean, institutional-quality data. Set up infrastructure.

**What to hunt for:**
- Calendar effects (month-end, quarter-end flows)
- Momentum (12-1 month, cross-sectional)
- Volatility patterns (clustering, regime detection)
- Structural edges: index rebalancing, futures roll yield, earnings drift

**Process:**
- Daily: Watch markets, log observations
- Weekly: Backtest one idea properly, read research (SSRN, AQR, Alpha Architect)
- Test across regimes, apply punishing transaction costs

**Key insight:** "The edge isn't in the strategy. It's in risk management and surviving long enough to learn."

---

### Skeptical Investor

**Starting point:** Focus on markets where smart money CAN'T operate.

**What to hunt for:**
- Small/micro-cap stocks (too illiquid for institutions)
- Obscure fixed income
- Index reconstitution arbitrage
- Distressed debt with specific catalysts
- Merger arbitrage in small deals ($50-500M)

**Validation requirements:**
- Economic rationale (WHY does this edge exist?)
- Transaction cost reality
- Multiple testing correction
- 3+ years live trading before believing

**Key insight:** "90% chance I find nothing. 8% chance it needs more capital than I have. 2% chance I find a real edge. That 2% is why I'd still try."

---

### Experienced Trader (15+ years trading own capital)

**Starting point:** Sit and WATCH for 2 weeks. No indicators. Just price, volume, time.

**What to observe:**
- Behavior around round numbers
- Opening range dynamics
- Prior day's high/low/close reactions
- Volume exhaustion patterns

**Process:**
- Week 1-2: Observe and journal
- Week 3-4: Form hypotheses in plain English
- Week 5-8: Manual backtesting (bar by bar, spreadsheet)
- Week 9-10: Add filters (what separates winners from losers?)
- Week 11-12: Paper trade with real-time execution
- Month 4-6: Live trading with minimum size

**Specific patterns found over career:**
- Opening range breakout failure
- "Gap and crap" (gap up >4%, no new high by 30 min = fade)
- Volume exhaustion (big move on huge volume, next push on lower volume = exhausted)

**Key insight:** "The edge isn't some secret formula. It's doing the boring work of observation, hypothesis, testing when everyone else looks for shortcuts."

---

### Statistician

**Starting point:** Academic literature. Don't reinvent the wheel.

**Papers to read first:**
1. Jegadeesh & Titman (1993) - Momentum
2. Asness, Moskowitz & Pedersen (2013) - Value and Momentum Everywhere
3. Fama & French (2015) - Five-Factor Model
4. Novy-Marx (2013) - Gross Profitability
5. McLean & Pontiff (2016) - Which anomalies survive publication?
6. Harvey, Liu & Zhu (2016) - Multiple testing problem

**What to test first:**
1. Cross-sectional momentum (12-1 month)
2. Time-series momentum (trend following on futures)
3. Value + Momentum combination
4. Quality/Profitability (Gross Profit / Assets)
5. Low volatility/low beta

**Statistical standards:**
- t-stat > 3.0 (not 2.0)
- Out-of-sample validation (one look only)
- Multiple testing correction (Bonferroni or FDR)
- Economic magnitude must survive costs

**Key insight:** "Most apparent trading strategies are statistical artifacts, not genuine alpha. After transaction costs and realistic assumptions, most retail traders would be better served by low-cost index funds."

---

### First Principles Thinker

**Starting point:** Ask what CREATES edge.

**Edge can only come from:**
1. Information advantage (you know something others don't)
2. Processing advantage (you interpret same info better)
3. Behavioral advantage (you act rationally when others don't)
4. Structural advantage (market mechanics create exploitable inefficiencies)

**Honest assessment:** "You likely have none of these."

**What to actually do:**
1. Paper trade with discipline (but know it removes emotional component)
2. Start with tiny real money ($100-500) - psychological difference is everything
3. Track everything - not just P&L, but WHY you entered, what you expected, what happened
4. 100+ trades before conclusions
5. Calculate actual edge: (Win rate × avg win) vs (Loss rate × avg loss)

**The uncomfortable answer:** "Your objective is to make money. Trading is one of the least efficient ways to do this. Invest in your skills, career, or broad index funds instead. That's the edge most people ignore."

---

### Startup CTO (MVP mindset)

**Week 1:**
- Day 1-2: Get data (Yahoo Finance, Binance API)
- Day 3-4: Build simplest possible backtester (one file, 100 lines)
- Day 5-7: Generate 50+ strategy hypotheses from literature/forums

**Week 2:**
- Morning: Code 2-3 simple strategies
- Midday: Run backtests, record results
- Afternoon: Analyze failures, generate variations
- Evening: Update hypothesis list

**What to test first:**
- Batch 1: Mean reversion (RSI oversold bounce)
- Batch 2: Momentum (simple breakout)
- Batch 3: Volatility-based (buy low vol, sell high vol)

**Kill criteria (be ruthless):**
- Sharpe < 0.5 in-sample → Dead
- Out-of-sample Sharpe < 50% of in-sample → Dead (overfit)
- < 30 trades in test period → Inconclusive

**Key insight:** "The goal isn't to find a holy grail. It's to systematically eliminate bad ideas fast until you find something with a real, explainable edge."

---

### Failure Analyst / Risk Manager

**Starting point:** Define survival constraints FIRST.

**Before any research, define:**
- Maximum acceptable drawdown: 20-25%
- Minimum Sharpe after costs: 0.8+
- Minimum trades per year: 50+
- Maximum model complexity: <5 parameters
- Minimum years out-of-sample: 5+

**Work backwards from how strategies die:**

| Strategy Type | Primary Death Cause | Survival Requirement |
|--------------|---------------------|---------------------|
| Momentum | Regime change / crowding | Must work across regimes |
| Mean Reversion | Fat tails / correlation breakdown | Strict stop losses |
| Carry | Tail events | Explicit tail hedging |
| Value | Decade-long drawdowns | Patience + psychology |
| Stat Arb | Alpha decay | Continuous refresh pipeline |

**Pre-registration ritual:** Before any backtest, write down and LOCK:
- Hypothesis
- Exact signal definition
- Entry/exit rules
- Success criteria
- Number of variations to test (1-3, max 5)

**The torture tests:**
1. Regime tests (bull, bear, high vol, low vol)
2. Temporal stability (5-year rolling windows)
3. Parameter sensitivity (±25%)
4. Universe variation (US → Europe)
5. Delay test (add 1 day delay to signals)
6. Remove best trades (still profitable without top 5%?)

**Key insight:** "The winning strategy isn't the one with the highest backtest Sharpe. It's the one that's still alive in 10 years."

---

### Software Architect

**Treat it as a systematic search problem.**

**Phase 1: Data Infrastructure (Weeks 1-4)**
- Data lake with 5+ years history
- Quality pipeline (survivorship bias, look-ahead, corporate actions)
- Storage: TimescaleDB or Parquet

**Phase 2: Define Search Space (Weeks 4-8)**
- Strategy "genome" representation
- Dimensions: Signal type, time horizon, universe, execution style
- Generate 500+ candidate hypotheses

**Phase 3: Search Algorithm (Weeks 8-16)**
- Stage 1: Rapid screening (1 day per strategy)
- Stage 2: Deep dive (1 week per strategy)
- Stage 3: Stress testing (2 weeks per strategy)
- Use Bayesian optimization or genetic algorithms

**Phase 4: Validation (Weeks 16-20)**
- Statistical significance (t-stat > 3)
- Economic rationale review
- Regime robustness
- Stress scenarios

**Phase 5: Deployment (Weeks 20+)**
- Paper trading (4-8 weeks)
- Gradual capital deployment (10% → 25% → 50% → 100%)
- Decay monitoring and kill switches

**Key insight:** "Data quality is everything. Spend 30% of your time on data. The more parameters you have, the more likely you're curve-fitting."

---

## The Edges They'd Test First (Consensus)

### Structural (Highest Conviction)
- Index rebalancing (S&P additions/deletions)
- Futures roll yield (contango/backwardation)
- Month-end/quarter-end flows
- Options expiration dynamics

### Behavioral
- Momentum (12-1 month) - most robust anomaly
- Post-earnings announcement drift
- Mean reversion after emotional spikes
- Lottery stock effect (fade high-skewness)

### Time-Based
- Overnight vs intraday returns
- Tuesday-Thursday vs Monday-Friday
- First/last 30 minutes vs midday

### Relative Value
- Value + Momentum combination
- Low volatility / low beta
- Quality (gross profitability)

---

## The Validation Process (Universal Agreement)

```
Phase 1: Hypothesis (Before Data)
├── Write down WHY it should work
├── Identify who's on the other side losing
└── Predict when it should break

Phase 2: Backtest (Paranoid Mode)
├── Out-of-sample: 70/30 split, NEVER peek
├── Walk-forward: Train on window 1, test on window 2, slide
├── Realistic costs: 2x what you expect
├── Regime testing: Bull, bear, high vol, low vol
└── Parameter sensitivity: ±25% should still work

Phase 3: Paper Trade (6+ months)
├── Real-time decisions, not backtested
├── Compare fills to backtest assumptions
├── Track emotional state

Phase 4: Live (Tiny Size)
├── 10-20% of intended capital
├── 50-100 trades before conclusions
├── Scale up only if live matches backtest
```

---

## Realistic Expectations

| Metric | Backtest | Live (Expect) |
|--------|----------|---------------|
| Sharpe | 1.0-1.5 | 0.5-1.0 |
| Performance degradation | — | 30-50% |
| Win rate edge | Significant | Marginal |

---

## The Meta-Insight

**The process IS the edge.**

- Most strategies don't work
- Most backtests lie
- Most people give up or blow up
- The winners follow rigorous process, size appropriately, survive long enough for compounding

---

## Open Question

Is sourcing strategies from expert podcasts/research fundamentally different from this process?

See: [Discussion to follow]
