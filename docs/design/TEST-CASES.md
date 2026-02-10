# Test Strategies

**Purpose:** Validate the strategy schema against complex, real-world strategies.
**Date:** 2026-01-23

---

## Strategy 1: Dividend Capture with Covered Call

**Complexity type:** Event-driven + options + fundamentals

```yaml
# ============================================================
# STRATEGY 1: DIVIDEND CAPTURE WITH COVERED CALL
# ============================================================

id: TEST-001
name: Dividend Capture with Covered Call
created: 2026-01-23T10:00:00Z
status: pending

source:
  reference: "Internal strategy development"
  url: null
  excerpt: |
    Buy quality dividend stocks before ex-date, sell covered calls
    to enhance returns. Targets Buffett-style companies with
    consistent dividend history.
  hash: sha256:example123
  extracted_date: 2026-01-23T10:00:00Z

  # Source credibility assessment (for ingestion filtering)
  credibility:
    source_type: personal
    author_track_record: retail_verified
    author_skin_in_game: true
    author_conflicts: null
    claimed_performance:
      sharpe: null  # No specific claims made
      cagr: null
      max_drawdown: null
      sample_period: null
      is_out_of_sample: null

lineage: null

tags:
  hypothesis_type: [income, event_driven]
  asset_class: [equity, options]
  complexity: complex

# ------------------------------------------------------------
hypothesis:
  summary: "Capture dividends on quality stocks while enhancing returns with covered calls"
  detail: |
    Dividend capture strategies attempt to profit from dividend payments by
    owning stock through the ex-dividend date. The stock typically drops by
    approximately the dividend amount on ex-date, making pure dividend capture
    marginal. By selling covered calls, we collect premium that can offset
    any stock price decline and enhance overall returns. We target high-quality,
    Buffett-style companies to minimize the risk of adverse price movements.

  # THE "WHY" FRAMEWORK (required for ingestion quality)
  edge:
    mechanism: "Option premium + dividend income exceeds typical ex-date price drop"
    category: structural
    why_exists: |
      Covered call premium provides a buffer because option sellers are compensated
      for giving up upside. Dividend dates are known in advance, allowing systematic
      positioning. Quality filters reduce risk of large adverse moves.
    counterparty: |
      Call buyers who want upside exposure without owning stock. They pay premium
      for leverage. Market makers who need to hedge inventory.
    why_persists: |
      Requires operational complexity (coordinating stock + options).
      Margin requirements limit capacity. Small edge per trade requires scale.
      Most retail investors don't have options access or knowledge.
    decay_conditions: |
      If option premiums compress significantly (low IV environment).
      If dividend policies become less predictable.
      If the strategy becomes widely automated and crowded.
    capacity_estimate: "$10-50M before market impact becomes significant"

# ------------------------------------------------------------
strategy_mode: simple

# ------------------------------------------------------------
universe:
  type: filtered
  base: us_equities

  criteria:
    - field: market_cap
      operator: gte
      value: 10000000000  # $10B+
      description: "Large cap stocks only"

    - field: roe
      operator: gte
      value: 0.15
      description: "Return on equity > 15% (quality indicator)"

    - field: debt_to_equity
      operator: lte
      value: 0.5
      description: "Conservative balance sheet"

    - field: dividend_consecutive_quarters
      operator: gte
      value: 4
      description: "At least 4 consecutive quarters of dividends"

    - field: dividend_yield
      operator: gte
      value: 0.02
      description: "Dividend yield at least 2%"

  requires:
    - requirement: options_chain_available
    - requirement: options_liquidity_minimum
      params:
        min_daily_volume: 100

# ------------------------------------------------------------
entry:
  type: compound

  compound:
    logic: and
    conditions:
      - type: event_driven
        config:
          event_type: ex_dividend
          timing:
            reference: before
            offset: "1 day"

      - type: technical
        config:
          indicator: price_trend
          params:
            lookback_days: 60
            method: linear_regression_slope
          condition: "slope >= 0 (not in downtrend)"

  filters:
    - name: earnings_blackout
      description: "Avoid if earnings within 5 days"
      condition: "days_to_earnings > 5 OR days_since_earnings > 2"

  timing:
    allowed_days: [mon, tue, wed, thu, fri]
    allowed_hours: "09:30-15:30"
    blackout_periods: []

# ------------------------------------------------------------
position:
  type: multi_leg

  legs:
    - name: stock_leg
      direction: long
      instrument:
        source: from_signal
        reference: "triggered_stock"  # The stock that met entry criteria
      asset_type: equity
      allocation:
        method: from_sizing
        value: null  # Determined by sizing rules

    - name: call_leg
      direction: short
      instrument:
        source: from_signal
        reference: "triggered_stock"
      asset_type: option
      option_params:
        option_type: call
        strike_selection: otm_1  # One strike out of the money
        expiry_selection: nearest_monthly
      allocation:
        method: fixed_pct
        value: 1.0  # 1 call per 100 shares

  sizing:
    method: equal_weight
    params:
      target_positions: 10  # Spread across ~10 positions

  constraints:
    max_positions: 15
    max_position_pct: 0.15
    max_sector_pct: 0.30
    max_leverage: 1.0  # No leverage (covered calls are covered)

# ------------------------------------------------------------
exit:
  paths:
    - name: time_exit
      type: time_based
      params:
        hold_days: 5
      condition_description: "Exit 5 days after entry if call not assigned"
      action: "Close stock position, buy back call if has value"

    - name: call_assignment
      type: option_assignment
      params:
        allow_assignment: true
      condition_description: "If call is exercised, stock is called away"
      action: "Position closed via assignment, profit = premium + (strike - entry)"

    - name: dividend_cut_stop
      type: custom
      params:
        signal: dividend_announcement
        condition: "announced_dividend < expected_dividend * 0.8"
      condition_description: "Exit if dividend is cut by >20%"
      action: "Close all legs immediately"

  priority: first_triggered

  fallback:
    type: time_based
    hold_days: 10

# ------------------------------------------------------------
position_management:
  enabled: false  # Simple hold until exit

# ------------------------------------------------------------
data_requirements:
  price_data:
    - type: daily
      instruments: from_universe
      history_required: "1 year"

  fundamental_data:
    - field: roe
      frequency: quarterly
    - field: debt_to_equity
      frequency: quarterly
    - field: market_cap
      frequency: daily

  options_data:
    - data_type: chains
    - data_type: greeks

  calendar_data:
    - type: dividends
    - type: earnings

  alternative_data: []

  derived_calculations:
    - name: price_trend
      description: "60-day price trend via linear regression"
      inputs: [price_daily]

# ------------------------------------------------------------
assumptions:
  - category: market
    assumption: "Dividends are paid as announced"
    impact_if_wrong: "Expected income not received, strategy unprofitable"

  - category: execution
    assumption: "Can execute at or near quoted prices"
    impact_if_wrong: "Slippage erodes thin margins"

  - category: execution
    assumption: "Options have sufficient liquidity for entry/exit"
    impact_if_wrong: "Wide spreads make strategy uneconomic"

  - category: model
    assumption: "Quality filters reduce risk of large price drops"
    impact_if_wrong: "Stock drops more than dividend + premium, net loss"

# ------------------------------------------------------------
risks:
  - category: market
    risk: "Stock drops significantly more than dividend value"
    severity: high
    mitigation: "Quality filters, diversification across positions"

  - category: market
    risk: "Dividend cut or suspension"
    severity: medium
    mitigation: "Dividend history filter, exit on cut announcement"

  - category: execution
    risk: "Early assignment of call option"
    severity: low
    mitigation: "Accept assignment as valid exit path"

  - category: model
    risk: "Strategy returns don't exceed transaction costs"
    severity: medium
    mitigation: "Only trade when premium + dividend exceeds cost threshold"
```

---

## Strategy 2: FX Correlation Mean Reversion

**Complexity type:** Research-derived universe + pairs trading + statistical

```yaml
# ============================================================
# STRATEGY 2: FX CORRELATION MEAN REVERSION
# ============================================================

id: TEST-002
name: FX Correlation Mean Reversion
created: 2026-01-23T10:00:00Z
status: pending

source:
  reference: "Currency flow research hypothesis"
  url: null
  excerpt: |
    Currency flows may predict movements. Correlated FX pairs that
    diverge from historical relationship should mean-revert.
    Identify pairs through correlation analysis, trade divergence.
  hash: sha256:example456
  extracted_date: 2026-01-23T10:00:00Z

lineage: null

tags:
  hypothesis_type: [statistical_arbitrage, mean_reversion, relative_value]
  asset_class: [fx]
  complexity: complex

# ------------------------------------------------------------
hypothesis:
  summary: "Historically correlated FX pairs will mean-revert when they diverge"
  detail: |
    Foreign exchange pairs that share economic drivers (e.g., EUR/USD and GBP/USD
    both reflect USD strength) tend to move together. When they diverge beyond
    historical norms, the divergence often corrects. By identifying highly
    correlated pairs through rolling correlation analysis, we can trade
    divergences with a statistical edge.
  edge_source: |
    1. Economic linkages create persistent correlations
    2. Short-term divergences often driven by temporary flows/noise
    3. Statistical framework provides objective entry/exit

# ------------------------------------------------------------
strategy_mode: simple

# ------------------------------------------------------------
universe:
  type: research_derived

  research:
    description: "Identify highly correlated FX pairs through correlation analysis"
    method: correlation_analysis

    inputs:
      starting_universe: fx_majors  # EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CHF, USD/CAD, NZD/USD
      data_required: [price_daily]
      lookback: "252 days"

    parameters:
      correlation_method: pearson
      rolling_window: 60
      min_data_points: 200

    outputs:
      - name: correlated_pairs
        description: "Pairs with correlation > 0.7"
        selection_rule: "abs(correlation) > 0.7"

      - name: uncorrelated_pairs
        description: "Pairs with low correlation for potential diversification"
        selection_rule: "abs(correlation) < 0.3"

    tradeable: correlated_pairs

# ------------------------------------------------------------
entry:
  type: statistical

  statistical:
    metric: zscore
    params:
      lookback_days: 20
      spread_calculation: "log(pair_A) - beta * log(pair_B)"
      beta_window: 60
    threshold:
      entry: 2.0
      direction: outside_band  # Enter when |zscore| > 2.0

  filters:
    - name: regime_filter
      description: "Avoid during extreme market stress"
      condition: "vix < 35"

    - name: correlation_stability
      description: "Only trade if correlation has been stable"
      condition: "correlation_std_20d < 0.15"

  timing:
    allowed_days: [mon, tue, wed, thu, fri]
    allowed_hours: "all"  # FX trades 24/5
    blackout_periods: ["major_central_bank_announcements"]

# ------------------------------------------------------------
position:
  type: pairs

  legs:
    - name: diverged_down
      direction: long
      instrument:
        source: from_signal
        reference: "pair_with_negative_zscore"
      asset_type: fx
      allocation:
        method: volatility_target
        value: "match_other_leg"

    - name: diverged_up
      direction: short
      instrument:
        source: from_signal
        reference: "pair_with_positive_zscore"
      asset_type: fx
      allocation:
        method: volatility_target
        value: 0.5  # 50% of risk budget per leg

  sizing:
    method: volatility_adjusted
    params:
      target_volatility: 0.10  # 10% annualized vol target
      lookback_for_vol: 20

  constraints:
    max_positions: 5  # Max 5 pair trades at once
    max_leverage: 3.0  # FX typically uses leverage
    max_concentration: 0.4  # Max 40% in single pair trade

# ------------------------------------------------------------
exit:
  paths:
    - name: convergence
      type: convergence
      params:
        metric: zscore
        threshold: 0.5
      condition_description: "Z-score returns within 0.5 of mean"
      action: "Close both legs"

    - name: stop_loss
      type: stop_loss
      params:
        stop_type: fixed_pct
        stop_value: 0.05  # 5% loss on the spread
      condition_description: "Divergence continues, correlation may have broken"
      action: "Close both legs at loss"

    - name: zscore_blowout
      type: custom
      params:
        metric: zscore
        threshold: 3.5
      condition_description: "Z-score exceeds 3.5, relationship may be broken"
      action: "Close at loss, flag pair for review"

    - name: time_stop
      type: time_based
      params:
        hold_days: 20
      condition_description: "No convergence within 20 days"
      action: "Close and reassess"

  priority: first_triggered

  fallback:
    type: time_based
    hold_days: 30

# ------------------------------------------------------------
position_management:
  enabled: false  # No rebalancing during hold

# ------------------------------------------------------------
data_requirements:
  price_data:
    - type: daily
      instruments: [EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CHF, USD/CAD, NZD/USD]
      history_required: "3 years"

  fundamental_data: []

  options_data: []

  calendar_data:
    - type: economic
      description: "Central bank meetings, major economic releases"

  alternative_data: []

  derived_calculations:
    - name: correlation_matrix
      description: "Rolling correlation between all FX pairs"
      inputs: [price_daily]

    - name: pair_spread_zscore
      description: "Z-score of spread between correlated pairs"
      inputs: [price_daily, correlation_matrix]

# ------------------------------------------------------------
assumptions:
  - category: market
    assumption: "Historical correlations persist in the medium term"
    impact_if_wrong: "Divergences don't converge, strategy loses"

  - category: model
    assumption: "Z-score is appropriate measure of divergence"
    impact_if_wrong: "Entry/exit signals are suboptimal"

  - category: market
    assumption: "Mean reversion occurs within reasonable timeframe"
    impact_if_wrong: "Capital tied up in non-converging trades"

# ------------------------------------------------------------
risks:
  - category: market
    risk: "Correlation regime change (correlations break down)"
    severity: high
    mitigation: "Stop loss, z-score blowout exit, position limits"

  - category: market
    risk: "Central bank intervention causes persistent divergence"
    severity: medium
    mitigation: "Avoid trading around major central bank events"

  - category: model
    risk: "Lookback period for correlation is wrong"
    severity: medium
    mitigation: "Test multiple lookback periods, use stability filter"

  - category: execution
    risk: "Execution slippage in fast markets"
    severity: low
    mitigation: "FX majors have high liquidity"
```

---

## Strategy 3: Earnings Momentum + Sentiment

**Complexity type:** Event-driven + alternative data + compound signals

```yaml
# ============================================================
# STRATEGY 3: EARNINGS MOMENTUM + SENTIMENT
# ============================================================

id: TEST-003
name: Earnings Beat with Positive Sentiment
created: 2026-01-23T10:00:00Z
status: pending

source:
  reference: "Earnings momentum research"
  url: null
  excerpt: |
    Stocks that beat earnings AND have positive social sentiment
    in the following 24 hours tend to continue upward momentum.
    Combine fundamental catalyst with sentiment confirmation.
  hash: sha256:example789
  extracted_date: 2026-01-23T10:00:00Z

lineage: null

tags:
  hypothesis_type: [momentum, event_driven]
  asset_class: [equity]
  complexity: moderate

# ------------------------------------------------------------
hypothesis:
  summary: "Earnings beats with positive sentiment confirmation lead to continued momentum"
  detail: |
    Post-earnings announcement drift (PEAD) is well-documented — stocks that
    beat expectations tend to continue moving in that direction. However,
    not all beats lead to sustained moves. By adding a sentiment confirmation
    filter (positive social/news sentiment in the 24 hours after the beat),
    we filter for beats that have captured market attention and are more
    likely to see follow-through.
  edge_source: |
    1. PEAD is a known anomaly with persistent alpha
    2. Sentiment filter selects beats with market attention
    3. Combination reduces false positives from pure earnings screen

# ------------------------------------------------------------
strategy_mode: simple

# ------------------------------------------------------------
universe:
  type: filtered
  base: us_equities

  criteria:
    - field: market_cap
      operator: gte
      value: 1000000000  # $1B+
      description: "Mid to large cap"

    - field: avg_daily_volume
      operator: gte
      value: 500000
      description: "Sufficient liquidity"

    - field: has_earnings_upcoming_7d
      operator: eq
      value: true
      description: "Has earnings in next 7 days"

  requires:
    - requirement: sentiment_data_available

# ------------------------------------------------------------
entry:
  type: compound

  compound:
    logic: and
    conditions:
      - type: fundamental
        config:
          metrics: [earnings_surprise_pct]
          condition: "earnings_surprise_pct > 5"  # Beat by more than 5%

      - type: alternative_data
        config:
          data_source: sentiment
          metric: "24h_post_earnings_sentiment_score"
          condition: "sentiment_score > 0.6"  # 0-1 scale, above 0.6 is positive

  filters:
    - name: guidance_check
      description: "Avoid if guidance was lowered"
      condition: "guidance_change != 'lowered'"

    - name: gap_limit
      description: "Avoid if stock already gapped >15%"
      condition: "overnight_gap_pct < 15"

  timing:
    allowed_days: [mon, tue, wed, thu, fri]
    allowed_hours: "09:30-11:00"  # Enter in first 90 min after sentiment confirms
    blackout_periods: []

# ------------------------------------------------------------
position:
  type: single_leg

  legs:
    - name: equity_position
      direction: long
      instrument:
        source: from_signal
        reference: "triggered_stock"
      asset_type: equity
      allocation:
        method: from_sizing

  sizing:
    method: equal_weight
    params:
      target_positions: 10

  constraints:
    max_positions: 15
    max_position_pct: 0.10
    max_sector_pct: 0.30
    max_leverage: 1.0

# ------------------------------------------------------------
exit:
  paths:
    - name: momentum_fade
      type: custom
      params:
        indicator: rsi
        period: 14
        threshold: 70
      condition_description: "RSI reaches overbought (70+)"
      action: "Close position"

    - name: time_exit
      type: time_based
      params:
        hold_days: 10
      condition_description: "Exit after 10 trading days"
      action: "Close position"

    - name: stop_loss
      type: stop_loss
      params:
        stop_type: fixed_pct
        stop_value: 0.08  # 8% stop loss
      condition_description: "Stock drops 8% from entry"
      action: "Close at loss"

    - name: sentiment_reversal
      type: custom
      params:
        data_source: sentiment
        condition: "sentiment_score < 0.4"
      condition_description: "Sentiment turns negative"
      action: "Close position"

  priority: first_triggered

  fallback:
    type: time_based
    hold_days: 15

# ------------------------------------------------------------
position_management:
  enabled: false

# ------------------------------------------------------------
data_requirements:
  price_data:
    - type: daily
      instruments: from_universe
      history_required: "1 year"

  fundamental_data:
    - field: earnings_surprise
      frequency: quarterly
    - field: revenue_surprise
      frequency: quarterly
    - field: guidance
      frequency: quarterly

  options_data: []

  calendar_data:
    - type: earnings

  alternative_data:
    - source: social_sentiment
      provider: "social media aggregator"
    - source: news_sentiment
      provider: "news sentiment service"

  derived_calculations:
    - name: combined_sentiment_score
      description: "Weighted average of social and news sentiment"
      inputs: [social_sentiment, news_sentiment]

# ------------------------------------------------------------
assumptions:
  - category: market
    assumption: "Post-earnings drift continues to exist"
    impact_if_wrong: "Strategy has no edge"

  - category: data
    assumption: "Sentiment data is timely (within hours of earnings)"
    impact_if_wrong: "Can't confirm sentiment before signal stale"

  - category: model
    assumption: "Sentiment is predictive of follow-through"
    impact_if_wrong: "Filter adds noise rather than signal"

# ------------------------------------------------------------
risks:
  - category: market
    risk: "Earnings beat is priced in, no follow-through"
    severity: medium
    mitigation: "Sentiment filter, stop loss"

  - category: data
    risk: "Sentiment data is noisy or manipulated"
    severity: medium
    mitigation: "Use multiple sentiment sources, threshold filter"

  - category: execution
    risk: "Gap up prevents good entry"
    severity: low
    mitigation: "Gap limit filter (avoid >15% gaps)"
```

---

## Strategy 4: Regime-Adaptive Trend/Mean Reversion

**Complexity type:** Meta-strategy + regime detection + strategy switching

```yaml
# ============================================================
# STRATEGY 4: REGIME-ADAPTIVE STRATEGY
# ============================================================

id: TEST-004
name: Regime-Adaptive Trend and Mean Reversion
created: 2026-01-23T10:00:00Z
status: pending

source:
  reference: "Regime-based strategy research"
  url: null
  excerpt: |
    Use trend-following in trending markets, mean-reversion in ranging
    markets, and go flat in crisis. Detect regime using VIX and ADX.
  hash: sha256:exampleabc
  extracted_date: 2026-01-23T10:00:00Z

lineage: null

tags:
  hypothesis_type: [regime_adaptive, trend_following, mean_reversion]
  asset_class: [equity, etf]
  complexity: complex

# ------------------------------------------------------------
hypothesis:
  summary: "Different market regimes favor different strategies; adapt to the regime"
  detail: |
    Trend-following strategies perform well in trending markets but get
    whipsawed in ranging markets. Mean-reversion strategies work in ranging
    markets but fail in strong trends. By detecting the current market regime
    and switching strategies accordingly, we can improve risk-adjusted returns.
    In crisis regimes (high VIX), we go flat to preserve capital.
  edge_source: |
    1. Regime detection reduces strategy mismatch
    2. Going flat in crisis avoids worst drawdowns
    3. Each sub-strategy has edge in its appropriate regime

# ------------------------------------------------------------
strategy_mode: regime_adaptive

# ------------------------------------------------------------
universe:
  type: static
  instruments:
    - symbol: SPY
      asset_type: etf
    - symbol: QQQ
      asset_type: etf
    - symbol: IWM
      asset_type: etf
    - symbol: DIA
      asset_type: etf

# ------------------------------------------------------------
regimes:
  detection:
    method: manual_indicator
    params:
      indicators:
        - name: vix
          source: "^VIX"
        - name: adx
          source: "SPY"
          period: 14

      # Regime classification rules
      rules:
        crisis: "vix > 30"
        trending: "vix <= 30 AND adx > 25"
        ranging: "vix <= 30 AND adx <= 25"

    lookback: "1 day"  # Check daily

  modes:
    # ---- TRENDING REGIME ----
    - name: trending
      condition: "adx > 25 AND vix <= 30"

      entry:
        type: technical
        technical:
          indicator: ema_crossover
          params:
            fast_period: 10
            slow_period: 30
          condition: "fast crosses above slow = long, fast crosses below slow = exit"

      position:
        type: single_leg
        legs:
          - name: trend_position
            direction: long  # Only long in this version
            instrument:
              source: from_signal
              reference: "instrument_with_crossover"
            asset_type: etf
            allocation:
              method: from_sizing

        sizing:
          method: volatility_adjusted
          params:
            target_volatility: 0.15

        constraints:
          max_positions: 4
          max_leverage: 1.0

      exit:
        paths:
          - name: trend_reversal
            type: signal_reversal
            params:
              signal: "fast crosses below slow"
            condition_description: "EMA crosses back"
            action: "Close position"

          - name: trailing_stop
            type: trailing_stop
            params:
              trail_type: atr_multiple
              trail_value: 2.5
              activation: 0.05  # Activate after 5% profit
            condition_description: "Price falls 2.5 ATR from high"
            action: "Close position"

    # ---- RANGING REGIME ----
    - name: ranging
      condition: "adx <= 25 AND vix <= 30"

      entry:
        type: technical
        technical:
          indicator: rsi
          params:
            period: 14
          condition: "RSI < 30 = long (oversold), RSI > 70 = exit"

      position:
        type: single_leg
        legs:
          - name: mean_rev_position
            direction: long
            instrument:
              source: from_signal
              reference: "instrument_oversold"
            asset_type: etf
            allocation:
              method: from_sizing

        sizing:
          method: equal_weight
          params:
            target_positions: 4

        constraints:
          max_positions: 4
          max_leverage: 1.0

      exit:
        paths:
          - name: overbought
            type: custom
            params:
              indicator: rsi
              threshold: 70
            condition_description: "RSI reaches overbought"
            action: "Close position"

          - name: stop_loss
            type: stop_loss
            params:
              stop_type: fixed_pct
              stop_value: 0.05
            condition_description: "5% stop loss"
            action: "Close at loss"

          - name: time_stop
            type: time_based
            params:
              hold_days: 10
            condition_description: "No mean reversion in 10 days"
            action: "Close position"

    # ---- CRISIS REGIME ----
    - name: crisis
      condition: "vix > 30"
      action: flat  # No trading

  transitions:
    min_regime_duration: "3 days"  # Stay in regime at least 3 days
    signal_on_change: true  # Close positions when regime changes

# ------------------------------------------------------------
# Entry/Position/Exit at top level not needed for regime_adaptive
entry: null
position: null
exit: null

# ------------------------------------------------------------
position_management:
  enabled: false

# ------------------------------------------------------------
data_requirements:
  price_data:
    - type: daily
      instruments: [SPY, QQQ, IWM, DIA, ^VIX]
      history_required: "2 years"

  fundamental_data: []
  options_data: []
  calendar_data: []
  alternative_data: []

  derived_calculations:
    - name: adx
      description: "Average Directional Index for trend strength"
      inputs: [price_daily]

    - name: rsi
      description: "Relative Strength Index"
      inputs: [price_daily]

    - name: ema_crossover
      description: "EMA 10/30 crossover signals"
      inputs: [price_daily]

# ------------------------------------------------------------
assumptions:
  - category: model
    assumption: "VIX and ADX are good regime indicators"
    impact_if_wrong: "Regime detection is wrong, strategies misapplied"

  - category: market
    assumption: "Regimes persist long enough to be tradeable"
    impact_if_wrong: "Whipsawed by rapid regime changes"

  - category: model
    assumption: "Sub-strategies have edge in their regimes"
    impact_if_wrong: "Even correct regime detection doesn't help"

# ------------------------------------------------------------
risks:
  - category: model
    risk: "Regime detection lags actual regime change"
    severity: high
    mitigation: "Min regime duration, trailing stops in trend mode"

  - category: market
    risk: "Rapid regime changes cause whipsaws"
    severity: medium
    mitigation: "3-day minimum regime duration"

  - category: market
    risk: "Crisis regime lasts extended period, missing opportunities"
    severity: low
    mitigation: "Accept as cost of capital preservation"
```

---

## Strategy 5: Options Volatility Arbitrage

**Complexity type:** Pure options + Greeks + dynamic management

```yaml
# ============================================================
# STRATEGY 5: VOLATILITY ARBITRAGE (IV vs RV)
# ============================================================

id: TEST-005
name: Implied vs Realized Volatility Arbitrage
created: 2026-01-23T10:00:00Z
status: pending

source:
  reference: "Volatility arbitrage research"
  url: null
  excerpt: |
    Sell options when implied volatility is high relative to realized
    volatility. Delta-hedge to isolate the volatility premium.
    Profit from volatility risk premium.
  hash: sha256:exampledef
  extracted_date: 2026-01-23T10:00:00Z

lineage: null

tags:
  hypothesis_type: [volatility, statistical_arbitrage]
  asset_class: [options]
  complexity: complex

# ------------------------------------------------------------
hypothesis:
  summary: "Implied volatility consistently exceeds realized volatility; capture this premium"
  detail: |
    Options are typically priced with implied volatility (IV) that exceeds
    subsequent realized volatility (RV). This "volatility risk premium"
    compensates option sellers for bearing tail risk. By systematically
    selling options when IV is elevated relative to RV, and delta-hedging
    to neutralize directional exposure, we can capture this premium.
  edge_source: |
    1. Volatility risk premium is well-documented and persistent
    2. Delta-hedging isolates the volatility component
    3. Systematic approach avoids timing mistakes

# ------------------------------------------------------------
strategy_mode: simple

# ------------------------------------------------------------
universe:
  type: static
  instruments:
    - symbol: SPY
      asset_type: etf

# ------------------------------------------------------------
entry:
  type: statistical

  statistical:
    metric: iv_rv_ratio
    params:
      iv_source: "30d_atm_iv"
      rv_source: "30d_realized_vol"
      rv_lookback: 30
    threshold:
      entry: 1.2  # IV is 20%+ higher than RV
      direction: above

  filters:
    - name: minimum_iv
      description: "Don't sell options when IV is too low"
      condition: "atm_iv > 15"  # At least 15% IV

    - name: earnings_avoidance
      description: "Avoid selling through earnings"
      condition: "days_to_earnings > expiry_days OR days_to_earnings > 10"

  timing:
    allowed_days: [mon, tue, wed, thu, fri]
    allowed_hours: "09:45-15:45"
    blackout_periods: []

# ------------------------------------------------------------
position:
  type: multi_leg

  legs:
    - name: short_straddle
      direction: short
      instrument:
        source: static
        symbol: SPY
      asset_type: option
      option_params:
        option_type: straddle  # Short both call and put at same strike
        strike_selection: atm
        expiry_selection: days_30  # ~30 DTE
      allocation:
        method: fixed_pct
        value: 1.0

    - name: delta_hedge
      direction: dynamic  # Direction changes based on delta
      instrument:
        source: static
        symbol: SPY
      asset_type: etf
      allocation:
        method: delta_neutral
        value: "hedge to zero delta"

  sizing:
    method: risk_parity
    params:
      max_vega_exposure: 1000  # Dollar vega limit
      max_gamma_exposure: 50   # Dollar gamma limit

  constraints:
    max_positions: 1  # One SPY position at a time
    max_leverage: 2.0  # Margin for short options

# ------------------------------------------------------------
exit:
  paths:
    - name: profit_target
      type: take_profit
      params:
        target_type: fixed_pct
        target_value: 0.5  # Take 50% of max profit (theta decay)
      condition_description: "Captured 50% of premium"
      action: "Close straddle, unwind hedge"

    - name: loss_limit
      type: stop_loss
      params:
        stop_type: fixed_pct
        stop_value: 1.0  # Max loss = 100% of premium collected
      condition_description: "Loss equals premium collected"
      action: "Close at loss"

    - name: time_exit
      type: time_based
      params:
        hold_until: "5 days before expiry"
      condition_description: "Close before gamma explodes near expiry"
      action: "Close straddle"

    - name: iv_spike
      type: volatility_exit
      params:
        condition: "current_iv > entry_iv * 1.5"
      condition_description: "IV spikes 50% above entry level"
      action: "Close to avoid further losses"

  priority: first_triggered

  fallback:
    type: time_based
    hold_days: 25

# ------------------------------------------------------------
position_management:
  enabled: true

  rules:
    - name: delta_rebalance
      trigger:
        type: threshold
        metric: portfolio_delta
        condition: "abs(delta) > 10"  # Delta exposure > $10 per 1% move
      action:
        type: hedge
        params:
          target_delta: 0
          instrument: underlying
      description: "Rebalance hedge when delta drifts"

    - name: gamma_check
      trigger:
        type: threshold
        metric: portfolio_gamma
        condition: "gamma > 100"  # Getting dangerous near expiry
      action:
        type: close_partial
        params:
          close_pct: 0.5
      description: "Reduce position if gamma gets too high"

# ------------------------------------------------------------
data_requirements:
  price_data:
    - type: daily
      instruments: [SPY]
      history_required: "2 years"

    - type: intraday_5min  # For delta hedging
      instruments: [SPY]
      history_required: "30 days"

  fundamental_data: []

  options_data:
    - data_type: chains
    - data_type: greeks
    - data_type: iv
      description: "Implied volatility surface"

  calendar_data:
    - type: earnings
    - type: economic
      description: "FOMC, major economic releases"

  alternative_data: []

  derived_calculations:
    - name: realized_volatility
      description: "30-day rolling realized volatility"
      inputs: [price_daily]

    - name: iv_rv_ratio
      description: "Ratio of implied to realized volatility"
      inputs: [options_iv, realized_volatility]

# ------------------------------------------------------------
assumptions:
  - category: market
    assumption: "Volatility risk premium persists"
    impact_if_wrong: "Strategy has no edge"

  - category: execution
    assumption: "Can delta-hedge efficiently"
    impact_if_wrong: "Hedging costs erode profits"

  - category: model
    assumption: "IV and RV are measured correctly"
    impact_if_wrong: "Entry signals are wrong"

# ------------------------------------------------------------
risks:
  - category: market
    risk: "Large market move causes significant loss"
    severity: high
    mitigation: "Loss limit, gamma monitoring, hedge rebalancing"

  - category: market
    risk: "Volatility explodes (vol of vol risk)"
    severity: high
    mitigation: "IV spike exit, loss limit"

  - category: execution
    risk: "Hedging slippage during fast markets"
    severity: medium
    mitigation: "Avoid trading during high vol events"

  - category: model
    risk: "Greeks miscalculated, hedge is wrong"
    severity: medium
    mitigation: "Use reliable options data provider"

  - category: operational
    risk: "Assignment risk on short options"
    severity: low
    mitigation: "Close before expiry, monitor ITM options"
```

---

## Schema Validation Summary

| Strategy | Maps Fully? | Gaps/Issues |
|----------|-------------|-------------|
| 1. Dividend Capture | ✓ Yes | None |
| 2. FX Correlation | ✓ Yes | None (from_signal reference works) |
| 3. Earnings + Sentiment | ✓ Yes | None |
| 4. Regime-Adaptive | ✓ Yes | Regime modes contain full sub-configs |
| 5. Volatility Arb | ✓ Yes | position_management handles hedging |

**All 5 strategies successfully map to the schema.**

---

## Notes for Implementation

1. **Straddle option_type** — Added to handle short straddle (both call and put)
2. **Dynamic direction** — The delta_hedge leg uses `direction: dynamic`
3. **delta_neutral allocation** — Special allocation method for hedging
4. **Option types needed**: call, put, straddle, strangle, spread (future)

---

## Ingestion Quality Filter Test Cases

These test cases validate the new ingestion quality filtering system. They test red flag detection, specificity scoring, and trust scoring.

---

### Test Case: PASS — Well-Documented Strategy from Academic Source

**Expected Outcome:** ACCEPT (high trust score, no red flags)

```yaml
# ============================================================
# INGESTION TEST: SHOULD PASS — Academic Momentum Strategy
# ============================================================

id: INGEST-TEST-PASS-001
name: Cross-Sectional Momentum (Jegadeesh-Titman)
created: 2026-01-23T10:00:00Z
status: pending

source:
  reference: "Jegadeesh & Titman (1993) - Returns to Buying Winners and Selling Losers"
  url: "https://doi.org/10.1111/j.1540-6261.1993.tb04702.x"
  excerpt: |
    Stocks that have performed well over the past 3-12 months continue
    to outperform over the next 3-12 months. Strategy: Buy top decile
    performers, sell bottom decile, hold for 3-12 months.
  hash: sha256:academic001
  extracted_date: 2026-01-23T10:00:00Z

  credibility:
    source_type: academic
    author_track_record: academic
    author_skin_in_game: false  # Academics typically don't trade
    author_conflicts: null
    claimed_performance:
      sharpe: 0.6
      cagr: 0.12
      max_drawdown: -0.35
      sample_period: "1965-1989"
      is_out_of_sample: true  # Multiple papers have replicated

hypothesis:
  summary: "Past winners continue to outperform; past losers continue to underperform"
  detail: |
    Cross-sectional momentum is one of the most robust anomalies in finance.
    Stocks in the top decile of 12-month returns (excluding the most recent month)
    outperform stocks in the bottom decile by approximately 1% per month.

  edge:
    mechanism: "Investor underreaction to news causes prices to drift"
    category: behavioral
    why_exists: |
      Investors underreact to new information. Good news takes time to be
      fully reflected in prices. Anchoring bias causes slow adjustment.
    counterparty: |
      Contrarian investors who sell winners too early and buy losers too early.
      Value investors who avoid "expensive" momentum stocks.
    why_persists: |
      Behavioral biases are persistent human traits. Strategy has capacity
      constraints (momentum crashes). Requires discipline to hold through
      drawdowns. Career risk for institutional managers.
    decay_conditions: |
      If investor behavior becomes more rational (unlikely).
      If too much capital chases momentum (crowding).
      Momentum crashes during sharp reversals (2009).
    capacity_estimate: "$10B+ across all momentum strategies globally"

# Specificity Score: 8/8 (all fields present)
# Trust Score: ~85/100
#   - Economic rationale: 28/30 (well-documented behavioral explanation)
#   - Out-of-sample evidence: 25/25 (extensively replicated)
#   - Implementation realism: 18/20 (transaction costs discussed in literature)
#   - Source credibility: 14/15 (top-tier academic journal)
#   - Novelty: 0/10 (well-known, but that's fine)
#   - Red flags: 0

# EXPECTED DECISION: ACCEPT
```

---

### Test Case: FAIL — Too-Good-To-Be-True Claims

**Expected Outcome:** REJECT (hard red flag: Sharpe > 3.0)

```yaml
# ============================================================
# INGESTION TEST: SHOULD FAIL — Unrealistic Performance Claims
# ============================================================

id: INGEST-TEST-FAIL-001
name: "Secret AI Trading System"
created: 2026-01-23T10:00:00Z
status: pending

source:
  reference: "Trading Guru Podcast Episode 147"
  url: "https://example.com/podcast/147"
  excerpt: |
    My proprietary AI system has generated 400% returns annually with
    a Sharpe ratio of 4.2. It works in all market conditions and has
    never had a losing month. I'm sharing this because I want to help
    regular people achieve financial freedom.
  hash: sha256:toogood001
  extracted_date: 2026-01-23T10:00:00Z

  credibility:
    source_type: podcast
    author_track_record: unknown
    author_skin_in_game: false  # Claims to trade but unverified
    author_conflicts: "Selling $997 course"
    claimed_performance:
      sharpe: 4.2  # RED FLAG: > 3.0
      cagr: 4.0    # RED FLAG: 400% annually
      max_drawdown: 0  # RED FLAG: "Never had a losing month"
      sample_period: "2020-2024"
      is_out_of_sample: false

hypothesis:
  summary: "AI predicts market direction with high accuracy"
  detail: |
    Machine learning model trained on price patterns predicts
    next-day market direction with 85% accuracy.

  edge:
    mechanism: "AI finds patterns humans can't see"  # VAGUE - no economic rationale
    category: other
    why_exists: "The AI just works"  # RED FLAG: No explanation
    counterparty: "Everyone else who doesn't have AI"  # VAGUE
    why_persists: "Nobody else has this technology"  # IMPLAUSIBLE
    decay_conditions: null  # Not addressed
    capacity_estimate: null  # Not addressed

# Red Flags Triggered:
#   - sharpe_above_3: Claimed Sharpe of 4.2 (HARD REJECT)
#   - no_losing_periods: "Never had a losing month" (HARD REJECT)
#   - no_economic_rationale: "AI just works" (HARD REJECT)
#   - author_selling: Selling $997 course (HARD REJECT)
#   - works_all_conditions: "Works in all market conditions" (HARD REJECT)

# EXPECTED DECISION: REJECT
# REJECTION REASON: Multiple hard red flags (Sharpe > 3, no rationale, selling course)
```

---

### Test Case: ACCEPT WITH WARNING — No Stated Rationale (Sub-Agent Infers)

**Expected Outcome:** ACCEPT with soft warning (sub-agent attempts to infer rationale)

```yaml
# ============================================================
# INGESTION TEST: SHOULD PROCESS — Pattern Without Explanation
# Sub-agent will attempt to infer rationale; proceed with lower trust
# ============================================================

id: INGEST-TEST-WARN-002
name: "Golden Cross Strategy"
created: 2026-01-23T10:00:00Z
status: pending

source:
  reference: "Technical Analysis Blog Post"
  url: "https://example.com/blog/golden-cross"
  excerpt: |
    When the 50-day moving average crosses above the 200-day moving average,
    buy. When it crosses below, sell. This pattern has predicted major market
    moves for decades. Backtest shows 12% annual returns.
  hash: sha256:goldencross001
  extracted_date: 2026-01-23T10:00:00Z

  credibility:
    source_type: blog
    author_track_record: retail_unverified
    author_skin_in_game: false
    author_conflicts: "Affiliate links to brokerage"
    claimed_performance:
      sharpe: 0.8
      cagr: 0.12
      max_drawdown: -0.25
      sample_period: "2000-2024"
      is_out_of_sample: false  # Just one long backtest

hypothesis:
  summary: "50/200 MA crossover predicts market direction"
  detail: |
    The golden cross is a well-known technical pattern. When the 50-day
    moving average crosses above the 200-day, it signals bullish momentum.

  edge:
    # SOURCE PROVIDED NO RATIONALE — Sub-agent researched and inferred:
    mechanism: "Trend-following signal captures sustained price movements"
    category: behavioral
    why_exists: |
      [INFERRED] Moving average crossovers may capture momentum effects.
      Investors underreact to information, causing trends to persist.
      However, this is a weak/speculative connection.
    counterparty: |
      [INFERRED] Mean-reversion traders and contrarians who fade trends.
    why_persists: |
      [INFERRED] Behavioral biases are persistent, though this specific
      implementation may be too well-known to retain edge.
    decay_conditions: |
      [INFERRED] Likely already decayed due to widespread knowledge.
      Simple moving average strategies are among the most backtested.
    capacity_estimate: null

    # PROVENANCE TRACKING
    provenance:
      source: inferred  # Sub-agent had to research/hypothesize
      confidence: low   # Weak connection to known factors
      research_notes: |
        Source provided no economic rationale. Sub-agent attempted to connect
        to momentum/trend-following literature. Connection is weak because:
        1. Simple MA crossovers are extremely well-known
        2. No clear counterparty mechanism stated
        3. Strategy is likely already arbitraged
        Proceeding with low confidence.
      factor_alignment: "time_series_momentum"
      factor_alignment_tested: false  # Should test if returns correlate with TSMOM

# Soft Warnings Triggered:
#   - unknown_rationale: Source gave no rationale, sub-agent inferred with low confidence
#   - crowded_factor: Extremely well-known strategy
#   - no_transaction_costs: Costs not addressed in source

# Specificity Score: 6/8 (PASSES)

# Trust Score: ~40/100 (below threshold, but NOT rejected)
#   - Economic rationale: 10/30 (inferred, low confidence)
#   - Out-of-sample evidence: 5/25 (no true OOS)
#   - Implementation realism: 10/20 (costs not addressed)
#   - Source credibility: 5/15 (anonymous blog with affiliate links)
#   - Novelty: 0/10 (extremely well-known)
#   - Red flags: -10 (soft warnings only)

# EXPECTED DECISION: ACCEPT with WARNINGS
# WARNINGS: [unknown_rationale, crowded_factor, no_transaction_costs]
# NOTE: Validation will be the real test. If it passes walk-forward with
#       realistic costs, it works regardless of our ability to explain it.
#       But low trust score means extra human scrutiny before deployment.
```

---

### Test Case: ARCHIVE — Too Vague to Test

**Expected Outcome:** ARCHIVE (specificity score < 4)

```yaml
# ============================================================
# INGESTION TEST: SHOULD ARCHIVE — Not Specific Enough
# ============================================================

id: INGEST-TEST-ARCHIVE-001
name: "Buy Quality Companies"
created: 2026-01-23T10:00:00Z
status: pending

source:
  reference: "Value Investing Podcast Episode 52"
  url: "https://example.com/podcast/52"
  excerpt: |
    I look for quality companies with strong moats, good management,
    and reasonable valuations. When I find one, I buy and hold for
    the long term. This approach has served me well over 20 years.
  hash: sha256:vague001
  extracted_date: 2026-01-23T10:00:00Z

  credibility:
    source_type: podcast
    author_track_record: verified_fund_manager  # Actually credible
    author_skin_in_game: true
    author_conflicts: null
    claimed_performance:
      sharpe: 0.7
      cagr: 0.15
      max_drawdown: -0.40
      sample_period: "2004-2024"
      is_out_of_sample: true

hypothesis:
  summary: "Buy quality companies at reasonable prices for long-term gains"
  detail: |
    Quality investing focuses on companies with durable competitive
    advantages, strong balance sheets, and competent management.

  edge:
    mechanism: "Quality companies compound value over time"
    category: behavioral
    why_exists: |
      Investors undervalue predictable, boring businesses.
      Prefer lottery-ticket stocks with high potential.
    counterparty: "Investors chasing high-growth, speculative names"
    why_persists: "Requires patience most investors lack"
    decay_conditions: "If quality becomes overvalued as a factor"
    capacity_estimate: "$1B+"

# Specificity Score: 2/8 (BELOW THRESHOLD)
#   - has_entry_rules: NO (what defines "quality"? what price is "reasonable"?)
#   - has_exit_rules: NO ("hold long term" is not a rule)
#   - has_position_sizing: NO
#   - has_universe_definition: NO (which stocks? what market cap?)
#   - has_backtest_period: YES
#   - has_out_of_sample: YES
#   - has_transaction_costs: NO
#   - has_code_or_pseudocode: NO

# Trust Score: ~55/100 (would pass, but specificity fails)

# EXPECTED DECISION: ARCHIVE
# ARCHIVE REASON: Specificity score 2/8 < 4 threshold (cannot backtest)
```

---

### Test Case: ARCHIVE — Low Trust Score

**Expected Outcome:** ARCHIVE (trust score < 50)

```yaml
# ============================================================
# INGESTION TEST: SHOULD ARCHIVE — Low Trust Score
# ============================================================

id: INGEST-TEST-ARCHIVE-002
name: "Reddit WSB YOLO Strategy"
created: 2026-01-23T10:00:00Z
status: pending

source:
  reference: "Reddit WallStreetBets Post"
  url: "https://reddit.com/r/wallstreetbets/..."
  excerpt: |
    Buy weekly OTM calls on meme stocks when they're trending on social
    media. Sell when you double your money or lose it all. YOLO.
    Made $50k last month doing this.
  hash: sha256:wsb001
  extracted_date: 2026-01-23T10:00:00Z

  credibility:
    source_type: blog  # Reddit post
    author_track_record: retail_unverified
    author_skin_in_game: true  # Claims to trade
    author_conflicts: null
    claimed_performance:
      sharpe: null
      cagr: null
      max_drawdown: null
      sample_period: "Last month"
      is_out_of_sample: false

hypothesis:
  summary: "Buy meme stock options when social media momentum is high"
  detail: |
    Social media attention drives retail buying, which can cause
    short squeezes and momentum in certain stocks.

  edge:
    mechanism: "Social media attention drives buying pressure"
    category: behavioral
    why_exists: |
      Retail investors pile into stocks discussed on social media.
      Short squeezes can cause explosive moves.
    counterparty: "Short sellers and market makers"
    why_persists: |
      Social media dynamics are unpredictable.
      Timing is crucial and hard to systematize.
    decay_conditions: "If retail participation declines or platforms change"
    capacity_estimate: "$10k max - any more moves the options"

# Specificity Score: 5/8 (passes threshold)
#   - has_entry_rules: YES (buy when trending)
#   - has_exit_rules: YES (double or lose all)
#   - has_position_sizing: NO
#   - has_universe_definition: PARTIAL (meme stocks - vague)
#   - has_backtest_period: NO
#   - has_out_of_sample: NO
#   - has_transaction_costs: NO
#   - has_code_or_pseudocode: NO

# Trust Score: 35/100 (BELOW THRESHOLD)
#   - Economic rationale: 15/30 (some behavioral explanation)
#   - Out-of-sample evidence: 0/25 (none - "last month")
#   - Implementation realism: 5/20 (no costs, timing unclear)
#   - Source credibility: 2/15 (anonymous Reddit post)
#   - Novelty: 5/10 (timely but well-known)
#   - Red flags: -15 + (small_sample: "last month")

# EXPECTED DECISION: ARCHIVE
# ARCHIVE REASON: Trust score 35/100 < 50 threshold
```

---

### Test Case: SOFT WARNING — Single Market, Needs Investigation

**Expected Outcome:** ACCEPT with WARNING (soft red flag)

```yaml
# ============================================================
# INGESTION TEST: SHOULD PASS WITH WARNING — Needs Investigation
# ============================================================

id: INGEST-TEST-WARN-001
name: "Small Cap Value Momentum"
created: 2026-01-23T10:00:00Z
status: pending

source:
  reference: "Quantitative Finance Blog"
  url: "https://example.com/quant-blog/small-cap-value"
  excerpt: |
    Combining value and momentum in small caps produces Sharpe of 0.9
    in US markets from 2000-2020. Long stocks with low P/E and positive
    12-month momentum, equal weight, rebalance monthly.
  hash: sha256:smallcap001
  extracted_date: 2026-01-23T10:00:00Z

  credibility:
    source_type: practitioner
    author_track_record: retail_verified  # Published track record
    author_skin_in_game: true
    author_conflicts: null
    claimed_performance:
      sharpe: 0.9
      cagr: 0.18
      max_drawdown: -0.45
      sample_period: "2000-2020"
      is_out_of_sample: false  # Single backtest

hypothesis:
  summary: "Value + Momentum in small caps outperforms"
  detail: |
    Combining two well-documented factors (value and momentum) in the
    small cap space where inefficiencies are greater.

  edge:
    mechanism: "Factor combination captures multiple sources of alpha"
    category: behavioral
    why_exists: |
      Value works due to overreaction to bad news.
      Momentum works due to underreaction to good news.
      Small caps have less analyst coverage.
    counterparty: "Investors who can't access small caps at scale"
    why_persists: |
      Capacity-constrained (small caps).
      Requires operational complexity.
      Institutional career risk.
    decay_conditions: "If small cap liquidity improves and gets crowded"
    capacity_estimate: "$50-100M"

# Specificity Score: 7/8 (PASSES)

# Trust Score: 68/100 (PASSES)
#   - Economic rationale: 25/30
#   - Out-of-sample evidence: 10/25 (no OOS, but factors are documented)
#   - Implementation realism: 15/20
#   - Source credibility: 10/15
#   - Novelty: 8/10
#   - Red flags: 0

# Soft Red Flags:
#   - single_market: Only tested in US markets (INVESTIGATE)
#   - single_regime: Only tested 2000-2020 (INVESTIGATE)

# EXPECTED DECISION: ACCEPT with WARNINGS
# WARNINGS: [single_market, single_regime]
# ACTION: Require cross-market validation and crisis period testing during verification
```

---

## Ingestion Quality Test Summary

| Test ID | Name | Expected Decision | Key Reason |
|---------|------|-------------------|------------|
| INGEST-TEST-PASS-001 | Academic Momentum | ACCEPT | High trust, documented edge |
| INGEST-TEST-FAIL-001 | Secret AI System | REJECT | Sharpe > 3, selling course, "never loses" |
| INGEST-TEST-WARN-002 | Golden Cross | ACCEPT + WARN | No stated rationale, but sub-agent infers (low confidence) |
| INGEST-TEST-ARCHIVE-001 | Buy Quality Companies | ARCHIVE | Specificity < 4 (too vague to test) |
| INGEST-TEST-ARCHIVE-002 | WSB YOLO Strategy | ARCHIVE | Trust score < 50 |
| INGEST-TEST-WARN-001 | Small Cap Value Momentum | ACCEPT + WARN | Passes, but needs cross-market validation |

**Key Change:** "No economic rationale" is no longer a hard rejection. Sub-agents attempt to infer the rationale, and provenance is tracked. Validation is the real test.

---

## Red Flag Reference

### Hard Rejection Flags

| Flag | Condition |
|------|-----------|
| `sharpe_above_3` | Claimed Sharpe > 3.0 (non-HFT) |
| `no_losing_periods` | "Never had a losing month/year" |
| `works_all_conditions` | "Works in all market conditions" |
| `author_selling` | Author selling courses/signals/newsletters |
| `excessive_parameters` | More than 5 tunable parameters |
| `convenient_start_date` | Backtest starts after known drawdown |

### Soft Warning Flags

| Flag | Condition | Action |
|------|-----------|--------|
| `unknown_rationale` | No rationale found after sub-agent research | Lower trust, extra human scrutiny |
| `no_transaction_costs` | No discussion of costs/slippage | Model conservatively in validation |
| `no_drawdown_mentioned` | No drawdown discussed | May be hiding pain |
| `single_market` | Only tested in one geography | Require cross-market validation |
| `single_regime` | Only tested in bull market | Require crisis period testing |
| `small_sample` | < 30 independent observations | Flag as statistically inconclusive |
| `high_leverage` | Requires > 3x leverage | Proceed with caution |
| `crowded_factor` | Well-known factor strategy | Check for post-publication decay |
| `magic_numbers` | Specific params without justification | Test parameter sensitivity |

**Key Principle:** Missing rationale is NOT a rejection. Sub-agents will attempt to infer, and validation will determine if the strategy actually works. Provenance tracking ensures appropriate trust calibration.
