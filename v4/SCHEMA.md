# Strategy Document Schema v1.0

**Status:** Draft
**Last Updated:** 2026-01-23

---

## Overview

This schema defines how trading strategies are represented in the research-kit system. The design goals are:

1. **Semantic, not structural** — Capture WHAT the strategy does, not HOW to implement it
2. **Handle complexity** — Support real-world strategies (options, pairs, regime-adaptive)
3. **Machine-readable** — Can be parsed and validated programmatically
4. **Human-readable** — Can be understood by reading the document

---

## Schema Definition

```yaml
# ============================================================
# STRATEGY DOCUMENT SCHEMA v1.0
# ============================================================

# ------------------------------------------------------------
# METADATA (required)
# ------------------------------------------------------------
id: string                        # System-assigned (e.g., STRAT-047)
name: string                      # Human-readable name
created: ISO-8601                 # When strategy was created
status: pending | validating | validated | invalidated | blocked

source:
  reference: string               # Where this came from (title, episode, etc.)
  url: string | null              # URL if available
  excerpt: string                 # Key excerpt describing the strategy
  hash: string                    # SHA256 of source file (for provenance)
  extracted_date: ISO-8601

  # Source credibility assessment (for ingestion filtering)
  credibility:
    source_type: academic | podcast | blog | practitioner | personal
    author_track_record: verified_fund_manager | academic | retail_verified |
                         retail_unverified | unknown
    author_skin_in_game: boolean    # Do they actually trade this?
    author_conflicts: string | null # Selling courses? Raising capital?
    claimed_performance:
      sharpe: number | null
      cagr: number | null
      max_drawdown: number | null
      sample_period: string | null
      is_out_of_sample: boolean | null

lineage:                          # Optional — if derived from other strategies
  parents: [STRAT-XXX, ...]       # Parent strategy IDs
  relationship: variant | combination | refinement | reversal
  notes: string                   # What was changed/combined

tags:
  hypothesis_type:
    - trend_following
    - mean_reversion
    - momentum
    - volatility
    - event_driven
    - statistical_arbitrage
    - income
    - relative_value
    - regime_adaptive
  asset_class:
    - equity
    - fx
    - options
    - futures
    - crypto
    - multi_asset
  complexity: simple | moderate | complex

# ------------------------------------------------------------
# HYPOTHESIS (required)
# ------------------------------------------------------------
hypothesis:
  summary: string                 # One-line description (< 100 chars)
  detail: string                  # Full explanation of the market hypothesis

  # THE "WHY" FRAMEWORK (Critical for understanding and trust calibration)
  # Complete this: "This strategy works because [agent] does [behavior]
  # due to [constraint/bias], creating [price pattern] that persists
  # because [reason not arbitraged]."
  edge:
    mechanism: string             # What drives returns (the behavior)
    category: structural | behavioral | informational | risk_premium | other
    why_exists: string            # Economic rationale - why does the edge exist?
    counterparty: string          # Who is on the other side losing money?
    why_persists: string          # Why hasn't this been arbitraged away?
    decay_conditions: string      # When/why will this edge stop working?
    capacity_estimate: string | null  # Approximate $ capacity before edge degrades

    # RATIONALE PROVENANCE (track where the "why" came from)
    provenance:
      source: source_stated | source_enhanced | inferred | unknown
      # source_stated: Source explicitly explained the rationale
      # source_enhanced: Source gave partial rationale, sub-agent completed it
      # inferred: Source gave no rationale, sub-agent researched/hypothesized
      # unknown: No rationale found even after research

      confidence: high | medium | low
      # high: Clear match to documented anomaly/factor with strong evidence
      # medium: Plausible match but not certain
      # low: Speculative or weak connection

      research_notes: string | null
      # How was this rationale determined? What did sub-agent find?
      # e.g., "Strategy matches 12-1 month momentum pattern documented
      #        in Jegadeesh-Titman (1993). Entry/exit rules align with
      #        known implementation."

      factor_alignment: string | null
      # If inferred, which known factor/anomaly does this align with?
      # e.g., "momentum", "value", "quality", "low_volatility",
      #       "post_earnings_drift", "index_rebalancing", etc.

      factor_alignment_tested: boolean | null
      # Has the strategy been tested for correlation with the claimed factor?
      # If inferred as "momentum" but doesn't load on momentum factor,
      # the inference may be wrong.

# ------------------------------------------------------------
# STRATEGY MODE (required)
# ------------------------------------------------------------
strategy_mode: simple | regime_adaptive

# ------------------------------------------------------------
# UNIVERSE (required)
# ------------------------------------------------------------
universe:
  type: static | filtered | research_derived | signal_derived

  # --- For type: static ---
  # A fixed list of instruments
  instruments:
    - symbol: string
      asset_type: equity | etf | fx | future | option | crypto

  # --- For type: filtered ---
  # Start with a base and apply filters
  base: us_equities | sp500 | nasdaq100 | sector_etfs | fx_majors |
        commodity_futures | crypto_major | custom
  custom_base: string             # If base is "custom", describe it

  criteria:
    - field: string               # What to filter on
      operator: gt | lt | eq | gte | lte | in | not_in | between | exists
      value: any                  # The threshold/value
      description: string         # Human-readable explanation

  # Additional filter: data availability requirements
  requires:
    - requirement: string         # e.g., "options_chain_available"

  # --- For type: research_derived ---
  # Universe is the OUTPUT of a research/analysis phase
  research:
    description: string           # What research determines the universe
    method: correlation_analysis | factor_analysis | clustering |
            cointegration_test | pca | custom

    inputs:
      starting_universe: string   # What we analyze (e.g., "fx_majors")
      data_required: [string]     # Data needed for analysis
      lookback: string            # Analysis period (e.g., "252 days")

    parameters:                   # Method-specific parameters
      key: value

    outputs:                      # What the research produces
      - name: string              # e.g., "correlated_pairs"
        description: string
        selection_rule: string    # e.g., "correlation > 0.7"

    tradeable: string             # Which output becomes the universe

  # --- For type: signal_derived ---
  # Universe changes based on signals (e.g., "stocks hitting 52-week high today")
  signal_filter:
    description: string
    condition: string             # What makes something enter the universe
    refresh: daily | weekly | intraday | on_signal

# ------------------------------------------------------------
# ENTRY LOGIC (required for strategy_mode: simple)
# ------------------------------------------------------------
entry:
  type: technical | event_driven | statistical | fundamental |
        alternative_data | compound

  # --- For type: technical ---
  technical:
    indicator: string             # e.g., sma_crossover, rsi, macd, breakout
    params:
      key: value                  # Indicator parameters
    condition: string             # e.g., "fast_sma crosses above slow_sma"

  # --- For type: event_driven ---
  event:
    event_type: earnings | ex_dividend | economic_release |
                ipo | split | custom
    custom_event: string          # If event_type is "custom"
    timing:
      reference: before | at | after
      offset: string              # e.g., "1 day", "30 minutes"

  # --- For type: statistical ---
  statistical:
    metric: zscore | percentile | deviation | spread | custom
    params:
      key: value
    threshold:
      entry: number               # When to enter
      direction: above | below | outside_band

  # --- For type: fundamental ---
  fundamental:
    metrics: [string]             # e.g., ["pe_ratio", "earnings_growth"]
    condition: string             # e.g., "PE < 15 AND earnings_growth > 10%"

  # --- For type: alternative_data ---
  alternative:
    data_source: sentiment | news | satellite | web_traffic |
                 options_flow | insider_transactions | custom
    metric: string                # What we measure
    condition: string             # Entry condition

  # --- For type: compound ---
  # Multiple conditions combined
  compound:
    logic: and | or
    conditions:
      - type: technical | event_driven | statistical | fundamental | alternative_data
        # ... nested definition matching the type above
        config: {}                # Type-specific configuration

  # --- Additional filters (apply to all entry types) ---
  filters:
    - name: string
      description: string
      condition: string

  # --- Timing constraints ---
  timing:
    allowed_days: [mon, tue, wed, thu, fri]  # Or "all"
    allowed_hours: string         # e.g., "09:30-16:00" or "all"
    blackout_periods: [string]    # e.g., ["first_hour", "last_15_min"]

# ------------------------------------------------------------
# POSITION STRUCTURE (required)
# ------------------------------------------------------------
position:
  type: single_leg | multi_leg | pairs | spread | custom

  legs:
    - name: string                # Identifier for this leg (e.g., "stock_leg")

      direction: long | short

      instrument:
        source: static | from_universe | from_signal | from_research
        # For static:
        symbol: string            # e.g., "SPY"
        # For from_universe:
        selection: all | filtered | ranked
        rank_by: string           # If ranked, what metric
        top_n: integer            # If ranked, how many
        # For from_signal or from_research:
        reference: string         # e.g., "diverged_down", "correlated_pairs[0]"

      asset_type: equity | etf | option | future | fx | crypto

      # --- For options ---
      option_params:
        option_type: call | put
        strike_selection: atm | otm_1 | otm_2 | itm_1 | delta_XX |
                         pct_otm_XX | custom
        strike_custom: string     # If custom, describe
        expiry_selection: nearest_weekly | nearest_monthly |
                          days_XX | specific_dte | custom
        expiry_custom: string     # If custom, describe

      # --- Allocation for this leg ---
      allocation:
        method: fixed_pct | fixed_amount | equal_weight |
                volatility_target | from_sizing
        value: number | string    # e.g., 0.5 for 50%, or "match_other_leg"

  # --- Overall position sizing ---
  sizing:
    method: equal_weight | volatility_adjusted | risk_parity |
            kelly | fixed_fractional | custom
    params:
      target_volatility: number   # For volatility_adjusted
      max_risk_per_trade: number  # For risk-based
      kelly_fraction: number      # For kelly (usually fractional kelly)

  # --- Constraints ---
  constraints:
    max_positions: integer
    max_position_pct: number      # Max % of portfolio in single position
    max_sector_pct: number        # Max % in single sector
    max_leverage: number          # Max gross leverage
    max_concentration: number     # Max % in correlated positions

# ------------------------------------------------------------
# EXIT LOGIC (required for strategy_mode: simple)
# ------------------------------------------------------------
exit:
  paths:
    - name: string                # Identifier (e.g., "profit_target")

      type: signal_reversal | convergence | time_based |
            stop_loss | trailing_stop | take_profit |
            option_expiry | option_assignment |
            volatility_exit | custom

      # Type-specific parameters:
      params:
        # For signal_reversal:
        signal: string            # Which signal reverses

        # For convergence (pairs/stat arb):
        metric: string            # e.g., "zscore"
        threshold: number         # e.g., 0.5

        # For time_based:
        hold_days: integer
        # Or:
        hold_until: string        # e.g., "expiry", "earnings_after"

        # For stop_loss:
        stop_type: fixed_pct | atr_multiple | support_level | trailing
        stop_value: number

        # For trailing_stop:
        trail_type: pct | atr_multiple | chandelier
        trail_value: number
        activation: number        # Profit level to activate trail

        # For take_profit:
        target_type: fixed_pct | risk_multiple | resistance_level
        target_value: number

        # For option_expiry:
        action: let_expire | roll | close_before
        days_before: integer      # If close_before

        # For option_assignment:
        allow_assignment: boolean

        # For volatility_exit:
        condition: string         # e.g., "IV drops below 20"

      condition_description: string  # Human-readable
      action: string                 # What happens when triggered

  priority: first_triggered | by_order | simultaneous_eval

  fallback:                       # Default if nothing else triggers
    type: time_based
    hold_days: integer

# ------------------------------------------------------------
# POSITION MANAGEMENT (optional — for strategies that rebalance)
# ------------------------------------------------------------
position_management:
  enabled: boolean

  rules:
    - name: string
      trigger:
        type: threshold | time_interval | signal
        # For threshold:
        metric: string            # e.g., "delta", "weight_drift"
        condition: string         # e.g., "> 0.1"
        # For time_interval:
        frequency: string         # e.g., "daily", "weekly"
        # For signal:
        signal: string            # What signal triggers

      action:
        type: rebalance | hedge | roll | adjust | close_partial
        params:
          key: value

      description: string         # Human-readable

# ------------------------------------------------------------
# REGIME-ADAPTIVE CONFIGURATION (required if strategy_mode: regime_adaptive)
# ------------------------------------------------------------
regimes:
  detection:
    method: volatility_regime | trend_strength | moving_average_position |
            hmm | manual_indicator | custom
    params:
      # For volatility_regime:
      metric: vix | realized_vol | custom
      thresholds:
        low: number
        high: number
      # For trend_strength:
      indicator: adx | ma_slope | custom
      threshold: number
      # For moving_average_position:
      price_vs_ma: string         # e.g., "close vs sma_200"

    lookback: string              # e.g., "20 days"

  modes:
    - name: string                # e.g., "trending", "ranging", "crisis"
      condition: string           # When this mode is active

      # Each mode has its own entry/position/exit config
      entry: {}                   # Same structure as main entry section
      position: {}                # Same structure as main position section
      exit: {}                    # Same structure as main exit section

      # Or can specify no trading:
      action: trade | flat        # "flat" means no positions in this regime

  transitions:
    min_regime_duration: string   # e.g., "5 days" — prevent whipsaws
    signal_on_change: boolean     # Exit positions on regime change?

# ------------------------------------------------------------
# DATA REQUIREMENTS (required)
# ------------------------------------------------------------
data_requirements:
  price_data:
    - type: daily | intraday_1min | intraday_5min | tick
      instruments: from_universe | [list]
      history_required: string    # e.g., "2 years"

  fundamental_data:
    - field: string               # e.g., "roe", "debt_to_equity"
      frequency: quarterly | annual | ttm

  options_data:
    - data_type: chains | greeks | iv | volume

  calendar_data:
    - type: earnings | dividends | economic | splits | custom

  alternative_data:
    - source: string              # e.g., "social_sentiment"
      provider: string            # Optional — specific provider

  derived_calculations:
    - name: string                # e.g., "correlation_matrix"
      description: string
      inputs: [string]

# ------------------------------------------------------------
# ASSUMPTIONS AND RISKS (required)
# ------------------------------------------------------------
assumptions:
  - category: market | data | execution | model
    assumption: string
    impact_if_wrong: string       # What happens if assumption is violated

risks:
  - category: market | liquidity | execution | model | data |
              operational | regulatory
    risk: string
    severity: low | medium | high
    mitigation: string            # How the strategy addresses this

# ------------------------------------------------------------
# INGESTION QUALITY (populated by system during ingestion)
# ------------------------------------------------------------
ingestion_quality:
  # Specificity Score: Can we actually backtest this? (0-8, reject if < 4)
  specificity:
    has_entry_rules: boolean
    has_exit_rules: boolean
    has_position_sizing: boolean
    has_universe_definition: boolean
    has_backtest_period: boolean
    has_out_of_sample: boolean
    has_transaction_costs: boolean
    has_code_or_pseudocode: boolean
    score: integer                # Sum of above (0-8)

  # Trust Score (0-100, reject if < 50)
  trust_score:
    economic_rationale: integer   # 0-30: Is the "why" well-explained?
    out_of_sample_evidence: integer  # 0-25: Any OOS testing mentioned?
    implementation_realism: integer  # 0-20: Costs, capacity, execution addressed?
    source_credibility: integer   # 0-15: Track record, incentives, transparency
    novelty: integer              # 0-10: New alpha or repackaged factor?
    red_flag_penalty: integer     # Negative: -15 per red flag
    total: integer                # Sum of above

  # Red Flags (detected at ingestion)
  red_flags:
    - flag: string                # e.g., "sharpe_above_threshold"
      severity: hard | soft       # Hard = reject, Soft = investigate
      message: string             # Explanation

  # Ingestion Decision
  decision: accept | queue | archive | reject
  rejection_reason: string | null

# ------------------------------------------------------------
# BACKTEST PARAMETERS (optional — can override defaults)
# ------------------------------------------------------------
backtest_params:
  start_date: ISO-8601 | "default"
  end_date: ISO-8601 | "default"
  initial_capital: number | "default"
  commission: number | "default"  # Per-trade commission
  slippage: number | "default"    # Slippage assumption
  margin_requirement: number      # For leveraged strategies

# ------------------------------------------------------------
# VALIDATION RESULTS (populated by system — not user-editable)
# ------------------------------------------------------------
validation:
  status: null | pending | running | passed | failed
  run_date: ISO-8601 | null

  verification_tests:
    - test: string
      status: passed | failed | skipped
      message: string

  gates_applied:
    min_sharpe: number
    min_consistency: number
    max_drawdown: number
    min_trades: number

  results:
    sharpe: number
    cagr: number
    total_return: number
    consistency: number           # % of windows profitable
    max_drawdown: number
    total_trades: number
    win_rate: number
    profit_factor: number

  windows:
    - period: string              # e.g., "2020-01-01 to 2021-12-31"
      sharpe: number
      return: number
      max_drawdown: number
      trades: number

  notes: string                   # Any notes from validation
```

---

## Schema Validation Checklist

For each strategy, verify:

### Ingestion Quality (Gate 1)
- [ ] Specificity score >= 4 (can we actually test this?)
- [ ] Trust score >= 50 (is it worth testing?)
- [ ] No hard red flags triggered
- [ ] Soft red flags reviewed and accepted

### Strategy Definition (Gate 2)
- [ ] Metadata is complete
- [ ] Source credibility assessed
- [ ] Hypothesis clearly explains the edge
- [ ] **Edge "why" framework is complete:**
  - [ ] Mechanism explained
  - [ ] Category identified (structural/behavioral/informational/risk_premium)
  - [ ] Why edge exists (economic rationale)
  - [ ] Counterparty identified (who's losing)
  - [ ] Why edge persists (not arbitraged)
  - [ ] Decay conditions stated
- [ ] Universe is fully specified
- [ ] Entry logic is unambiguous
- [ ] Position structure handles all legs
- [ ] Exit paths cover all scenarios
- [ ] Data requirements are explicit
- [ ] Assumptions are stated
- [ ] Risks are identified

### Verification Tests (Gate 3 - before validation)
- [ ] Look-ahead bias check passed
- [ ] Survivorship bias check passed
- [ ] Position sizing validated
- [ ] Data availability confirmed
- [ ] Parameter sanity verified

### Validation (Gate 4 - walk-forward backtesting)
- [ ] Passes all configured gates (Sharpe, consistency, drawdown, etc.)

---

## Design Decisions

1. **Why `strategy_mode`?**
   - Simple strategies have one entry/exit logic
   - Regime-adaptive strategies switch between modes
   - This avoids overcomplicating simple strategies

2. **Why `instrument.source`?**
   - Static: Known symbol (SPY)
   - From universe: Selected from filtered universe
   - From signal: Determined by the signal (e.g., "the stock that triggered")
   - From research: Output of research phase (e.g., "correlated pair A")

3. **Why separate position_management?**
   - Most strategies are "enter, hold, exit"
   - Some need ongoing management (hedging, rebalancing)
   - Optional section keeps simple strategies simple

4. **Why explicit data_requirements?**
   - Validation can check data availability BEFORE attempting backtest
   - Documents what the strategy actually needs
   - Helps identify strategies that can't be tested with available data

5. **Why the "edge" framework in hypothesis?**
   - Personas unanimously agreed: "If you can't explain WHY the edge exists, it probably doesn't"
   - Capturing the mechanism, counterparty, and persistence reason is critical
   - Strategies without economic rationale are almost certainly noise

6. **Why ingestion_quality scoring?**
   - 90-95% of ingested strategies are noise
   - Early filtering saves validation compute
   - Specificity score ensures we can actually test it
   - Trust score prioritizes what to test first

---

## Red Flags: Ingestion vs. Verification vs. Validation

Different red flags are caught at different stages:

### Ingestion-Time Red Flags (Hard Reject)

These are detected from the source material before any testing:

| Flag ID | Condition | Why It's Fatal |
|---------|-----------|----------------|
| `sharpe_above_3` | Claimed Sharpe > 3.0 (non-HFT) | Almost certainly overfit or fraud |
| `no_losing_periods` | "Never had a losing month/year" | Statistically implausible |
| `works_all_conditions` | "Works in all market conditions" | Nothing does |
| `author_selling` | Author selling courses/signals/newsletters | Massive incentive bias |
| `convenient_start_date` | Backtest starts after known drawdown | Cherry-picked period |
| `excessive_parameters` | More than 5 tunable parameters | Overfitting machine |

**Note:** "No economic rationale" is NOT a hard reject. Sub-agents will attempt to infer the rationale. If none can be found, the strategy proceeds with `provenance.source: unknown` and lower trust weighting.

### Ingestion-Time Red Flags (Soft Warning)

These flag for investigation but don't auto-reject:

| Flag ID | Condition | Action |
|---------|-----------|--------|
| `unknown_rationale` | No rationale found even after sub-agent research | Lower trust weighting, extra scrutiny |
| `no_transaction_costs` | Source doesn't discuss costs/slippage | Model conservatively in validation |
| `no_drawdown_mentioned` | No drawdown discussed | May be hiding pain, investigate |
| `single_market` | Only tested in US equities | Require cross-market validation |
| `single_regime` | Only tested 2010-2020 | Require crisis period testing |
| `stopped_discussing` | Strategy no longer mentioned by source | May have stopped working |
| `high_leverage` | Requires leverage > 3x | Proceed with extreme caution |
| `crowded_factor` | Relies on well-known factor | Check for decay since publication |
| `small_sample` | Fewer than 30 independent observations | Statistically inconclusive |
| `magic_numbers` | Specific params without justification | Test parameter sensitivity |

### Verification-Time Red Flags

These are caught when analyzing the strategy document (existing verification tests):

| Test | What It Catches |
|------|-----------------|
| `look_ahead_bias` | Using future data in signals |
| `survivorship_bias` | Cherry-picked universe |
| `position_sizing` | Invalid sizes, over-leverage |
| `data_availability` | Using data before it exists |
| `parameter_sanity` | Unreasonable parameter values |
| `hardcoded_values` | Dates/values suggesting overfitting |

### Validation-Time Red Flags

These are caught during backtesting (validation gates):

| Condition | Meaning |
|-----------|---------|
| OOS Sharpe < 50% of IS Sharpe | Likely overfit |
| Max drawdown > threshold | Risk exceeds tolerance |
| Consistency < threshold | Doesn't work across windows |
| Win rate collapses in recent periods | Edge may be decaying |
| Returns concentrated in few trades | Not robust |

---

## The "Why" Framework: Required Format

Every strategy should answer this question during ingestion:

> "This strategy works because **[agent]** does **[behavior]** due to **[constraint/bias]**, creating predictable **[price pattern]** that persists because **[reason not arbitraged]**."

### Good Example (Accept)

```yaml
edge:
  mechanism: "Index funds must buy stocks added to S&P 500"
  category: structural
  why_exists: "Mandate constraints force buying regardless of price"
  counterparty: "Index funds paying premium for inclusion"
  why_persists: "Index funds cannot change their behavior"
  decay_conditions: "If index methodology changes or announcement lead time shrinks"
  capacity_estimate: "$50-100M per event"
```

### Bad Example (Reject)

```yaml
edge:
  mechanism: "Prices mean revert"
  category: other
  why_exists: "Historical backtest shows it works"
  counterparty: "Unknown"
  why_persists: "Not sure"
  decay_conditions: null
  capacity_estimate: null
```

If the edge section looks like the bad example, the strategy should be rejected or archived until the economic rationale can be established
