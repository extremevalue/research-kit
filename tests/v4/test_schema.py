"""Tests for V4 strategy schema models.

This module tests the V4 schema against all 5 test strategies from TEST-CASES.md:
1. Dividend Capture with Covered Call (TEST-001)
2. FX Correlation Mean Reversion (TEST-002)
3. Earnings Momentum + Sentiment (TEST-003)
4. Regime-Adaptive Trend/Mean Reversion (TEST-004)
5. Options Volatility Arbitrage (TEST-005)
"""

import copy
from datetime import datetime

import pytest

from research_system.schemas.v4 import (
    # Strategy models
    V4Strategy,
    StrategyMode,
    StrategyStatus,
    SourceType,
    AuthorTrackRecord,
    HypothesisType,
    AssetClass,
    Complexity,
    EdgeCategory,
    UniverseType,
    UniverseBase,
    EntryType,
    PositionType,
    Direction,
    InstrumentSource,
    InstrumentAssetType,
    ExitType,
    ExitPriority,
    RegimeDetectionMethod,
    RegimeAction,
    PriceDataType,
    # Ingestion models
    IngestionQuality,
    SpecificityScore,
    TrustScore,
    RedFlag,
    RedFlagSeverity,
    IngestionDecision,
    create_hard_red_flag,
    create_soft_red_flag,
    # Validation models
    Validation,
    ValidationStatus,
    ValidationResults,
    ValidationWindow,
    ValidationGates,
    VerificationTest,
    VerificationTestStatus,
    create_verification_test,
)


# =============================================================================
# TEST STRATEGY DATA
# =============================================================================

# Strategy 1: Dividend Capture with Covered Call
STRATEGY_1_DATA = {
    "id": "TEST-001",
    "name": "Dividend Capture with Covered Call",
    "created": "2026-01-23T10:00:00Z",
    "status": "pending",
    "source": {
        "reference": "Internal strategy development",
        "url": None,
        "excerpt": "Buy quality dividend stocks before ex-date, sell covered calls to enhance returns.",
        "hash": "sha256:example123",
        "extracted_date": "2026-01-23T10:00:00Z",
        "credibility": {
            "source_type": "personal",
            "author_track_record": "retail_verified",
            "author_skin_in_game": True,
            "author_conflicts": None,
            "claimed_performance": None,
        },
    },
    "lineage": None,
    "tags": {
        "hypothesis_type": ["income", "event_driven"],
        "asset_class": ["equity", "options"],
        "complexity": "complex",
    },
    "hypothesis": {
        "summary": "Capture dividends on quality stocks while enhancing returns with covered calls",
        "detail": "Dividend capture strategies attempt to profit from dividend payments.",
        "edge": {
            "mechanism": "Option premium + dividend income exceeds typical ex-date price drop",
            "category": "structural",
            "why_exists": "Covered call premium provides a buffer.",
            "counterparty": "Call buyers who want upside exposure.",
            "why_persists": "Requires operational complexity.",
            "decay_conditions": "If option premiums compress significantly.",
            "capacity_estimate": "$10-50M before market impact",
        },
    },
    "strategy_mode": "simple",
    "universe": {
        "type": "filtered",
        "base": "us_equities",
        "criteria": [
            {"field": "market_cap", "operator": "gte", "value": 10000000000},
            {"field": "roe", "operator": "gte", "value": 0.15},
        ],
        "requires": [{"requirement": "options_chain_available"}],
    },
    "entry": {
        "type": "compound",
        "compound": {
            "logic": "and",
            "conditions": [
                {
                    "type": "event_driven",
                    "config": {
                        "event_type": "ex_dividend",
                        "timing": {"reference": "before", "offset": "1 day"},
                    },
                },
                {
                    "type": "technical",
                    "config": {
                        "indicator": "price_trend",
                        "params": {"lookback_days": 60},
                        "condition": "slope >= 0",
                    },
                },
            ],
        },
        "filters": [{"name": "earnings_blackout", "description": "Avoid earnings", "condition": "days_to_earnings > 5"}],
        "timing": {"allowed_days": ["mon", "tue", "wed", "thu", "fri"], "allowed_hours": "09:30-15:30"},
    },
    "position": {
        "type": "multi_leg",
        "legs": [
            {
                "name": "stock_leg",
                "direction": "long",
                "instrument": {"source": "from_signal", "reference": "triggered_stock"},
                "asset_type": "equity",
                "allocation": {"method": "from_sizing"},
            },
            {
                "name": "call_leg",
                "direction": "short",
                "instrument": {"source": "from_signal", "reference": "triggered_stock"},
                "asset_type": "option",
                "option_params": {
                    "option_type": "call",
                    "strike_selection": "otm_1",
                    "expiry_selection": "nearest_monthly",
                },
                "allocation": {"method": "fixed_pct", "value": 1.0},
            },
        ],
        "sizing": {"method": "equal_weight", "params": {"target_positions": 10}},
        "constraints": {"max_positions": 15, "max_leverage": 1.0},
    },
    "exit": {
        "paths": [
            {"name": "time_exit", "type": "time_based", "params": {"hold_days": 5}},
            {"name": "call_assignment", "type": "option_assignment", "params": {"allow_assignment": True}},
        ],
        "priority": "first_triggered",
        "fallback": {"type": "time_based", "hold_days": 10},
    },
    "position_management": {"enabled": False},
    "data_requirements": {
        "price_data": [{"type": "daily", "instruments": "from_universe", "history_required": "1 year"}],
        "fundamental_data": [{"field": "roe", "frequency": "quarterly"}],
        "options_data": [{"data_type": "chains"}, {"data_type": "greeks"}],
        "calendar_data": [{"type": "dividends"}, {"type": "earnings"}],
    },
    "assumptions": [
        {"category": "market", "assumption": "Dividends are paid as announced", "impact_if_wrong": "Strategy unprofitable"},
    ],
    "risks": [
        {"category": "market", "risk": "Stock drops significantly", "severity": "high", "mitigation": "Quality filters"},
    ],
}

# Strategy 2: FX Correlation Mean Reversion
STRATEGY_2_DATA = {
    "id": "TEST-002",
    "name": "FX Correlation Mean Reversion",
    "created": "2026-01-23T10:00:00Z",
    "status": "pending",
    "source": {
        "reference": "Currency flow research hypothesis",
        "url": None,
        "excerpt": "Currency flows may predict movements.",
        "hash": "sha256:example456",
        "extracted_date": "2026-01-23T10:00:00Z",
    },
    "tags": {
        "hypothesis_type": ["statistical_arbitrage", "mean_reversion", "relative_value"],
        "asset_class": ["fx"],
        "complexity": "complex",
    },
    "hypothesis": {
        "summary": "Historically correlated FX pairs will mean-revert when they diverge",
        "detail": "FX pairs that share economic drivers tend to move together.",
        "edge_source": "1. Economic linkages create persistent correlations",
    },
    "strategy_mode": "simple",
    "universe": {
        "type": "research_derived",
        "research": {
            "description": "Identify highly correlated FX pairs",
            "method": "correlation_analysis",
            "inputs": {
                "starting_universe": "fx_majors",
                "data_required": ["price_daily"],
                "lookback": "252 days",
            },
            "parameters": {"correlation_method": "pearson", "rolling_window": 60},
            "outputs": [{"name": "correlated_pairs", "description": "Pairs with correlation > 0.7", "selection_rule": "abs(correlation) > 0.7"}],
            "tradeable": "correlated_pairs",
        },
    },
    "entry": {
        "type": "statistical",
        "statistical": {
            "metric": "zscore",
            "params": {"lookback_days": 20},
            "threshold": {"entry": 2.0, "direction": "outside_band"},
        },
        "filters": [{"name": "regime_filter", "description": "Avoid during stress", "condition": "vix < 35"}],
    },
    "position": {
        "type": "pairs",
        "legs": [
            {
                "name": "diverged_down",
                "direction": "long",
                "instrument": {"source": "from_signal", "reference": "pair_with_negative_zscore"},
                "asset_type": "fx",
                "allocation": {"method": "volatility_target", "value": "match_other_leg"},
            },
            {
                "name": "diverged_up",
                "direction": "short",
                "instrument": {"source": "from_signal", "reference": "pair_with_positive_zscore"},
                "asset_type": "fx",
                "allocation": {"method": "volatility_target", "value": 0.5},
            },
        ],
        "sizing": {"method": "volatility_adjusted", "params": {"target_volatility": 0.10}},
        "constraints": {"max_positions": 5, "max_leverage": 3.0},
    },
    "exit": {
        "paths": [
            {"name": "convergence", "type": "convergence", "params": {"metric": "zscore", "threshold": 0.5}},
            {"name": "stop_loss", "type": "stop_loss", "params": {"stop_type": "fixed_pct", "stop_value": 0.05}},
        ],
        "priority": "first_triggered",
        "fallback": {"type": "time_based", "hold_days": 30},
    },
    "data_requirements": {
        "price_data": [{"type": "daily", "instruments": ["EUR/USD", "GBP/USD"], "history_required": "3 years"}],
        "derived_calculations": [{"name": "correlation_matrix", "description": "Rolling correlation", "inputs": ["price_daily"]}],
    },
}

# Strategy 3: Earnings Momentum + Sentiment
STRATEGY_3_DATA = {
    "id": "TEST-003",
    "name": "Earnings Beat with Positive Sentiment",
    "created": "2026-01-23T10:00:00Z",
    "status": "pending",
    "source": {
        "reference": "Earnings momentum research",
        "url": None,
        "excerpt": "Stocks that beat earnings AND have positive social sentiment.",
        "hash": "sha256:example789",
        "extracted_date": "2026-01-23T10:00:00Z",
    },
    "tags": {
        "hypothesis_type": ["momentum", "event_driven"],
        "asset_class": ["equity"],
        "complexity": "moderate",
    },
    "hypothesis": {
        "summary": "Earnings beats with positive sentiment confirmation lead to continued momentum",
        "detail": "Post-earnings announcement drift (PEAD) is well-documented.",
    },
    "strategy_mode": "simple",
    "universe": {
        "type": "filtered",
        "base": "us_equities",
        "criteria": [
            {"field": "market_cap", "operator": "gte", "value": 1000000000},
            {"field": "avg_daily_volume", "operator": "gte", "value": 500000},
        ],
        "requires": [{"requirement": "sentiment_data_available"}],
    },
    "entry": {
        "type": "compound",
        "compound": {
            "logic": "and",
            "conditions": [
                {"type": "fundamental", "config": {"metrics": ["earnings_surprise_pct"], "condition": "earnings_surprise_pct > 5"}},
                {"type": "alternative_data", "config": {"data_source": "sentiment", "metric": "24h_post_earnings_sentiment_score", "condition": "sentiment_score > 0.6"}},
            ],
        },
    },
    "position": {
        "type": "single_leg",
        "legs": [
            {
                "name": "equity_position",
                "direction": "long",
                "instrument": {"source": "from_signal", "reference": "triggered_stock"},
                "asset_type": "equity",
                "allocation": {"method": "from_sizing"},
            },
        ],
        "sizing": {"method": "equal_weight", "params": {"target_positions": 10}},
        "constraints": {"max_positions": 15, "max_leverage": 1.0},
    },
    "exit": {
        "paths": [
            {"name": "time_exit", "type": "time_based", "params": {"hold_days": 10}},
            {"name": "stop_loss", "type": "stop_loss", "params": {"stop_type": "fixed_pct", "stop_value": 0.08}},
        ],
        "priority": "first_triggered",
        "fallback": {"type": "time_based", "hold_days": 15},
    },
    "data_requirements": {
        "price_data": [{"type": "daily", "instruments": "from_universe", "history_required": "1 year"}],
        "fundamental_data": [{"field": "earnings_surprise", "frequency": "quarterly"}],
        "alternative_data": [{"source": "social_sentiment", "provider": "social media aggregator"}],
    },
}

# Strategy 4: Regime-Adaptive Trend/Mean Reversion
STRATEGY_4_DATA = {
    "id": "TEST-004",
    "name": "Regime-Adaptive Trend and Mean Reversion",
    "created": "2026-01-23T10:00:00Z",
    "status": "pending",
    "source": {
        "reference": "Regime-based strategy research",
        "url": None,
        "excerpt": "Use trend-following in trending markets, mean-reversion in ranging markets.",
        "hash": "sha256:exampleabc",
        "extracted_date": "2026-01-23T10:00:00Z",
    },
    "tags": {
        "hypothesis_type": ["regime_adaptive", "trend_following", "mean_reversion"],
        "asset_class": ["equity", "etf"],
        "complexity": "complex",
    },
    "hypothesis": {
        "summary": "Different market regimes favor different strategies; adapt to the regime",
        "detail": "Trend-following strategies perform well in trending markets.",
    },
    "strategy_mode": "regime_adaptive",
    "universe": {
        "type": "static",
        "instruments": [
            {"symbol": "SPY", "asset_type": "etf"},
            {"symbol": "QQQ", "asset_type": "etf"},
            {"symbol": "IWM", "asset_type": "etf"},
            {"symbol": "DIA", "asset_type": "etf"},
        ],
    },
    "regimes": {
        "detection": {
            "method": "manual_indicator",
            "params": {
                "indicators": [
                    {"name": "vix", "source": "^VIX"},
                    {"name": "adx", "source": "SPY", "period": 14},
                ],
                "rules": {
                    "crisis": "vix > 30",
                    "trending": "vix <= 30 AND adx > 25",
                    "ranging": "vix <= 30 AND adx <= 25",
                },
            },
            "lookback": "1 day",
        },
        "modes": [
            {
                "name": "trending",
                "condition": "adx > 25 AND vix <= 30",
                "entry": {
                    "type": "technical",
                    "technical": {
                        "indicator": "ema_crossover",
                        "params": {"fast_period": 10, "slow_period": 30},
                        "condition": "fast crosses above slow",
                    },
                },
                "position": {
                    "type": "single_leg",
                    "legs": [
                        {
                            "name": "trend_position",
                            "direction": "long",
                            "instrument": {"source": "from_signal", "reference": "instrument_with_crossover"},
                            "asset_type": "etf",
                            "allocation": {"method": "from_sizing"},
                        },
                    ],
                    "sizing": {"method": "volatility_adjusted", "params": {"target_volatility": 0.15}},
                    "constraints": {"max_positions": 4, "max_leverage": 1.0},
                },
                "exit": {
                    "paths": [
                        {"name": "trend_reversal", "type": "signal_reversal", "params": {"signal": "fast crosses below slow"}},
                        {"name": "trailing_stop", "type": "trailing_stop", "params": {"trail_type": "atr_multiple", "trail_value": 2.5}},
                    ],
                },
                "action": "trade",
            },
            {
                "name": "ranging",
                "condition": "adx <= 25 AND vix <= 30",
                "entry": {
                    "type": "technical",
                    "technical": {
                        "indicator": "rsi",
                        "params": {"period": 14},
                        "condition": "RSI < 30",
                    },
                },
                "position": {
                    "type": "single_leg",
                    "legs": [
                        {
                            "name": "mean_rev_position",
                            "direction": "long",
                            "instrument": {"source": "from_signal", "reference": "instrument_oversold"},
                            "asset_type": "etf",
                            "allocation": {"method": "from_sizing"},
                        },
                    ],
                    "sizing": {"method": "equal_weight", "params": {"target_positions": 4}},
                    "constraints": {"max_positions": 4, "max_leverage": 1.0},
                },
                "exit": {
                    "paths": [
                        {"name": "overbought", "type": "custom", "params": {"indicator": "rsi", "threshold": 70}},
                        {"name": "stop_loss", "type": "stop_loss", "params": {"stop_type": "fixed_pct", "stop_value": 0.05}},
                    ],
                },
                "action": "trade",
            },
            {
                "name": "crisis",
                "condition": "vix > 30",
                "action": "flat",
            },
        ],
        "transitions": {"min_regime_duration": "3 days", "signal_on_change": True},
    },
    "entry": None,
    "position": None,
    "exit": None,
    "data_requirements": {
        "price_data": [{"type": "daily", "instruments": ["SPY", "QQQ", "IWM", "DIA", "^VIX"], "history_required": "2 years"}],
        "derived_calculations": [{"name": "adx", "description": "Average Directional Index", "inputs": ["price_daily"]}],
    },
}

# Strategy 5: Options Volatility Arbitrage
STRATEGY_5_DATA = {
    "id": "TEST-005",
    "name": "Implied vs Realized Volatility Arbitrage",
    "created": "2026-01-23T10:00:00Z",
    "status": "pending",
    "source": {
        "reference": "Volatility arbitrage research",
        "url": None,
        "excerpt": "Sell options when implied volatility is high relative to realized volatility.",
        "hash": "sha256:exampledef",
        "extracted_date": "2026-01-23T10:00:00Z",
    },
    "tags": {
        "hypothesis_type": ["volatility", "statistical_arbitrage"],
        "asset_class": ["options"],
        "complexity": "complex",
    },
    "hypothesis": {
        "summary": "Implied volatility consistently exceeds realized volatility; capture this premium",
        "detail": "Options are typically priced with IV that exceeds subsequent RV.",
    },
    "strategy_mode": "simple",
    "universe": {
        "type": "static",
        "instruments": [{"symbol": "SPY", "asset_type": "etf"}],
    },
    "entry": {
        "type": "statistical",
        "statistical": {
            "metric": "iv_rv_ratio",
            "params": {"iv_source": "30d_atm_iv", "rv_source": "30d_realized_vol"},
            "threshold": {"entry": 1.2, "direction": "above"},
        },
        "filters": [{"name": "minimum_iv", "description": "Don't sell when IV is too low", "condition": "atm_iv > 15"}],
    },
    "position": {
        "type": "multi_leg",
        "legs": [
            {
                "name": "short_straddle",
                "direction": "short",
                "instrument": {"source": "static", "symbol": "SPY"},
                "asset_type": "option",
                "option_params": {
                    "option_type": "straddle",
                    "strike_selection": "atm",
                    "expiry_selection": "days_30",
                },
                "allocation": {"method": "fixed_pct", "value": 1.0},
            },
            {
                "name": "delta_hedge",
                "direction": "dynamic",
                "instrument": {"source": "static", "symbol": "SPY"},
                "asset_type": "etf",
                "allocation": {"method": "delta_neutral", "value": "hedge to zero delta"},
            },
        ],
        "sizing": {"method": "risk_parity", "params": {"max_vega_exposure": 1000}},
        "constraints": {"max_positions": 1, "max_leverage": 2.0},
    },
    "exit": {
        "paths": [
            {"name": "profit_target", "type": "take_profit", "params": {"target_type": "fixed_pct", "target_value": 0.5}},
            {"name": "loss_limit", "type": "stop_loss", "params": {"stop_type": "fixed_pct", "stop_value": 1.0}},
            {"name": "iv_spike", "type": "volatility_exit", "params": {"condition": "current_iv > entry_iv * 1.5"}},
        ],
        "priority": "first_triggered",
        "fallback": {"type": "time_based", "hold_days": 25},
    },
    "position_management": {
        "enabled": True,
        "rules": [
            {
                "name": "delta_rebalance",
                "trigger": {"type": "threshold", "metric": "portfolio_delta", "condition": "abs(delta) > 10"},
                "action": {"type": "hedge", "params": {"target_delta": 0}},
                "description": "Rebalance hedge when delta drifts",
            },
        ],
    },
    "data_requirements": {
        "price_data": [
            {"type": "daily", "instruments": ["SPY"], "history_required": "2 years"},
            {"type": "intraday_5min", "instruments": ["SPY"], "history_required": "30 days"},
        ],
        "options_data": [{"data_type": "chains"}, {"data_type": "greeks"}, {"data_type": "iv", "description": "IV surface"}],
        "calendar_data": [{"type": "earnings"}, {"type": "economic", "description": "FOMC, major releases"}],
    },
}


# =============================================================================
# STRATEGY PARSING TESTS
# =============================================================================


class TestStrategyParsing:
    """Test parsing of all 5 test strategies."""

    def test_parse_strategy_1_dividend_capture(self):
        """Test parsing Strategy 1: Dividend Capture with Covered Call."""
        strategy = V4Strategy(**STRATEGY_1_DATA)

        assert strategy.id == "TEST-001"
        assert strategy.name == "Dividend Capture with Covered Call"
        assert strategy.status == StrategyStatus.PENDING
        assert strategy.strategy_mode == StrategyMode.SIMPLE

        # Check source
        assert strategy.source.credibility is not None
        assert strategy.source.credibility.source_type == SourceType.PERSONAL
        assert strategy.source.credibility.author_track_record == AuthorTrackRecord.RETAIL_VERIFIED
        assert strategy.source.credibility.author_skin_in_game is True

        # Check tags
        assert HypothesisType.INCOME in strategy.tags.hypothesis_type
        assert HypothesisType.EVENT_DRIVEN in strategy.tags.hypothesis_type
        assert AssetClass.EQUITY in strategy.tags.asset_class
        assert AssetClass.OPTIONS in strategy.tags.asset_class
        assert strategy.tags.complexity == Complexity.COMPLEX

        # Check hypothesis
        assert strategy.hypothesis.edge is not None
        assert strategy.hypothesis.edge.category == EdgeCategory.STRUCTURAL

        # Check universe
        assert strategy.universe.type == UniverseType.FILTERED
        assert strategy.universe.base == UniverseBase.US_EQUITIES
        assert len(strategy.universe.criteria) == 2
        assert len(strategy.universe.requires) == 1

        # Check entry
        assert strategy.entry is not None
        assert strategy.entry.type == EntryType.COMPOUND
        assert strategy.entry.compound is not None
        assert len(strategy.entry.compound.conditions) == 2

        # Check position
        assert strategy.position is not None
        assert strategy.position.type == PositionType.MULTI_LEG
        assert len(strategy.position.legs) == 2
        assert strategy.position.legs[0].name == "stock_leg"
        assert strategy.position.legs[0].direction == Direction.LONG
        assert strategy.position.legs[1].name == "call_leg"
        assert strategy.position.legs[1].direction == Direction.SHORT
        assert strategy.position.legs[1].option_params is not None

        # Check exit
        assert strategy.exit is not None
        assert len(strategy.exit.paths) == 2
        assert strategy.exit.priority == ExitPriority.FIRST_TRIGGERED

    def test_parse_strategy_2_fx_correlation(self):
        """Test parsing Strategy 2: FX Correlation Mean Reversion."""
        strategy = V4Strategy(**STRATEGY_2_DATA)

        assert strategy.id == "TEST-002"
        assert strategy.name == "FX Correlation Mean Reversion"
        assert strategy.strategy_mode == StrategyMode.SIMPLE

        # Check tags
        assert HypothesisType.STATISTICAL_ARBITRAGE in strategy.tags.hypothesis_type
        assert HypothesisType.MEAN_REVERSION in strategy.tags.hypothesis_type
        assert AssetClass.FX in strategy.tags.asset_class

        # Check research-derived universe
        assert strategy.universe.type == UniverseType.RESEARCH_DERIVED
        assert strategy.universe.research is not None
        assert strategy.universe.research.method.value == "correlation_analysis"
        assert strategy.universe.research.tradeable == "correlated_pairs"

        # Check statistical entry
        assert strategy.entry is not None
        assert strategy.entry.type == EntryType.STATISTICAL
        assert strategy.entry.statistical is not None
        assert strategy.entry.statistical.metric == "zscore"
        assert strategy.entry.statistical.threshold.entry == 2.0

        # Check pairs position
        assert strategy.position is not None
        assert strategy.position.type == PositionType.PAIRS
        assert len(strategy.position.legs) == 2
        assert strategy.position.constraints.max_leverage == 3.0

    def test_parse_strategy_3_earnings_sentiment(self):
        """Test parsing Strategy 3: Earnings Momentum + Sentiment."""
        strategy = V4Strategy(**STRATEGY_3_DATA)

        assert strategy.id == "TEST-003"
        assert strategy.name == "Earnings Beat with Positive Sentiment"
        assert strategy.tags.complexity == Complexity.MODERATE

        # Check compound entry with fundamental + alternative data
        assert strategy.entry is not None
        assert strategy.entry.type == EntryType.COMPOUND
        assert len(strategy.entry.compound.conditions) == 2

        # Check single leg position
        assert strategy.position is not None
        assert strategy.position.type == PositionType.SINGLE_LEG
        assert len(strategy.position.legs) == 1

        # Check alternative data requirement
        assert len(strategy.data_requirements.alternative_data) == 1
        assert strategy.data_requirements.alternative_data[0].source == "social_sentiment"

    def test_parse_strategy_4_regime_adaptive(self):
        """Test parsing Strategy 4: Regime-Adaptive Trend/Mean Reversion."""
        strategy = V4Strategy(**STRATEGY_4_DATA)

        assert strategy.id == "TEST-004"
        assert strategy.name == "Regime-Adaptive Trend and Mean Reversion"
        assert strategy.strategy_mode == StrategyMode.REGIME_ADAPTIVE

        # Check regime detection
        assert strategy.regimes is not None
        assert strategy.regimes.detection.method == RegimeDetectionMethod.MANUAL_INDICATOR
        assert len(strategy.regimes.detection.params.indicators) == 2

        # Check regime modes
        assert len(strategy.regimes.modes) == 3

        # Check trending mode
        trending_mode = strategy.regimes.modes[0]
        assert trending_mode.name == "trending"
        assert trending_mode.action == RegimeAction.TRADE
        assert trending_mode.entry is not None
        assert trending_mode.position is not None
        assert trending_mode.exit is not None

        # Check ranging mode
        ranging_mode = strategy.regimes.modes[1]
        assert ranging_mode.name == "ranging"
        assert ranging_mode.action == RegimeAction.TRADE

        # Check crisis mode
        crisis_mode = strategy.regimes.modes[2]
        assert crisis_mode.name == "crisis"
        assert crisis_mode.action == RegimeAction.FLAT
        assert crisis_mode.entry is None

        # Check transitions
        assert strategy.regimes.transitions is not None
        assert strategy.regimes.transitions.min_regime_duration == "3 days"
        assert strategy.regimes.transitions.signal_on_change is True

        # Simple mode entry/position/exit should be None
        assert strategy.entry is None
        assert strategy.position is None
        assert strategy.exit is None

    def test_parse_strategy_5_volatility_arbitrage(self):
        """Test parsing Strategy 5: Options Volatility Arbitrage."""
        strategy = V4Strategy(**STRATEGY_5_DATA)

        assert strategy.id == "TEST-005"
        assert strategy.name == "Implied vs Realized Volatility Arbitrage"
        assert strategy.strategy_mode == StrategyMode.SIMPLE

        # Check tags
        assert HypothesisType.VOLATILITY in strategy.tags.hypothesis_type
        assert AssetClass.OPTIONS in strategy.tags.asset_class

        # Check static universe
        assert strategy.universe.type == UniverseType.STATIC
        assert len(strategy.universe.instruments) == 1

        # Check statistical entry
        assert strategy.entry is not None
        assert strategy.entry.statistical.metric == "iv_rv_ratio"

        # Check multi-leg with options and dynamic direction
        assert strategy.position is not None
        assert strategy.position.type == PositionType.MULTI_LEG
        assert len(strategy.position.legs) == 2
        assert strategy.position.legs[0].option_params is not None
        assert strategy.position.legs[1].direction == Direction.DYNAMIC

        # Check position management
        assert strategy.position_management.enabled is True
        assert len(strategy.position_management.rules) == 1
        assert strategy.position_management.rules[0].name == "delta_rebalance"

        # Check exit with volatility exit
        assert strategy.exit is not None
        exit_types = [p.type for p in strategy.exit.paths]
        assert ExitType.TAKE_PROFIT in exit_types
        assert ExitType.VOLATILITY_EXIT in exit_types


class TestStrategyValidation:
    """Test validation of strategy models."""

    def test_simple_mode_requires_entry(self):
        """Test that simple mode requires entry, position, and exit."""
        data = copy.deepcopy(STRATEGY_1_DATA)
        data["entry"] = None
        data["position"] = None
        data["exit"] = None

        with pytest.raises(ValueError, match="Simple mode strategy must have entry"):
            V4Strategy(**data)

    def test_regime_adaptive_requires_regimes(self):
        """Test that regime_adaptive mode requires regimes."""
        data = copy.deepcopy(STRATEGY_4_DATA)
        data["regimes"] = None

        with pytest.raises(ValueError, match="Regime-adaptive strategy must have regimes"):
            V4Strategy(**data)

    def test_position_requires_legs(self):
        """Test that position requires at least one leg."""
        data = copy.deepcopy(STRATEGY_1_DATA)
        data["position"]["legs"] = []

        with pytest.raises(ValueError):
            V4Strategy(**data)


# =============================================================================
# INGESTION QUALITY TESTS
# =============================================================================


class TestIngestionQuality:
    """Test ingestion quality scoring models."""

    def test_specificity_score_calculation(self):
        """Test specificity score calculation."""
        score = SpecificityScore(
            has_entry_rules=True,
            has_exit_rules=True,
            has_position_sizing=True,
            has_universe_definition=True,
            has_backtest_period=False,
            has_out_of_sample=False,
            has_transaction_costs=False,
            has_code_or_pseudocode=False,
        )

        assert score.score == 4
        assert score.passes_threshold(4) is True
        assert score.passes_threshold(5) is False

    def test_trust_score_calculation(self):
        """Test trust score calculation."""
        score = TrustScore(
            economic_rationale=25,
            out_of_sample_evidence=20,
            implementation_realism=15,
            source_credibility=10,
            novelty=5,
            red_flag_penalty=-15,
        )

        assert score.total == 60
        assert score.passes_threshold(50) is True
        assert score.passes_threshold(70) is False

    def test_trust_score_bounds(self):
        """Test trust score respects bounds."""
        # Test lower bound
        score_low = TrustScore(red_flag_penalty=-200)
        assert score_low.total == 0

        # Test upper bound (components at max)
        score_high = TrustScore(
            economic_rationale=30,
            out_of_sample_evidence=25,
            implementation_realism=20,
            source_credibility=15,
            novelty=10,
        )
        assert score_high.total == 100

    def test_red_flag_creation(self):
        """Test red flag creation."""
        hard_flag = create_hard_red_flag("sharpe_above_3")
        assert hard_flag.severity == RedFlagSeverity.HARD
        assert "Sharpe > 3.0" in hard_flag.message

        soft_flag = create_soft_red_flag("crowded_factor")
        assert soft_flag.severity == RedFlagSeverity.SOFT
        assert "well-known factor" in soft_flag.message

    def test_ingestion_quality_hard_rejection(self):
        """Test that hard red flags cause rejection."""
        quality = IngestionQuality(
            specificity=SpecificityScore(
                has_entry_rules=True,
                has_exit_rules=True,
                has_position_sizing=True,
                has_universe_definition=True,
            ),
            trust_score=TrustScore(
                economic_rationale=25,
                out_of_sample_evidence=20,
            ),
            red_flags=[create_hard_red_flag("sharpe_above_3")],
        )

        decision = quality.compute_decision()
        assert decision == IngestionDecision.REJECT
        assert quality.has_hard_red_flags() is True

    def test_ingestion_quality_archive_low_specificity(self):
        """Test that low specificity causes archive."""
        quality = IngestionQuality(
            specificity=SpecificityScore(
                has_entry_rules=True,
                has_exit_rules=False,
            ),
            trust_score=TrustScore(economic_rationale=25),
        )

        decision = quality.compute_decision()
        assert decision == IngestionDecision.ARCHIVE
        assert "Specificity score" in quality.rejection_reason

    def test_ingestion_quality_archive_low_trust(self):
        """Test that low trust causes archive."""
        quality = IngestionQuality(
            specificity=SpecificityScore(
                has_entry_rules=True,
                has_exit_rules=True,
                has_position_sizing=True,
                has_universe_definition=True,
            ),
            trust_score=TrustScore(economic_rationale=10),
        )

        decision = quality.compute_decision()
        assert decision == IngestionDecision.ARCHIVE
        assert "Trust score" in quality.rejection_reason

    def test_ingestion_quality_accept_with_warnings(self):
        """Test that soft red flags cause accept with warnings."""
        quality = IngestionQuality(
            specificity=SpecificityScore(
                has_entry_rules=True,
                has_exit_rules=True,
                has_position_sizing=True,
                has_universe_definition=True,
            ),
            trust_score=TrustScore(
                economic_rationale=25,
                out_of_sample_evidence=20,
                source_credibility=10,
            ),
            red_flags=[create_soft_red_flag("single_market")],
        )

        decision = quality.compute_decision()
        assert decision == IngestionDecision.ACCEPT
        assert len(quality.warnings) == 1

    def test_ingestion_quality_full_accept(self):
        """Test clean acceptance without warnings."""
        quality = IngestionQuality(
            specificity=SpecificityScore(
                has_entry_rules=True,
                has_exit_rules=True,
                has_position_sizing=True,
                has_universe_definition=True,
                has_backtest_period=True,
                has_out_of_sample=True,
            ),
            trust_score=TrustScore(
                economic_rationale=28,
                out_of_sample_evidence=22,
                implementation_realism=18,
                source_credibility=12,
            ),
        )

        decision = quality.compute_decision()
        assert decision == IngestionDecision.ACCEPT
        assert len(quality.warnings) == 0


# =============================================================================
# VALIDATION TESTS
# =============================================================================


class TestValidation:
    """Test validation result models."""

    def test_validation_gates(self):
        """Test validation gates checking."""
        gates = ValidationGates(
            min_sharpe=0.5,
            min_consistency=0.6,
            max_drawdown=0.3,
            min_trades=30,
        )

        assert gates.check_sharpe(0.6) is True
        assert gates.check_sharpe(0.4) is False
        assert gates.check_consistency(0.7) is True
        assert gates.check_drawdown(0.25) is True
        assert gates.check_drawdown(0.35) is False
        assert gates.check_trades(50) is True
        assert gates.check_trades(20) is False

    def test_verification_test_creation(self):
        """Test verification test creation."""
        passed_test = create_verification_test(
            "look_ahead_bias", True, "No look-ahead bias detected"
        )
        assert passed_test.status == VerificationTestStatus.PASSED

        failed_test = create_verification_test(
            "survivorship_bias", False, "Survivorship bias detected"
        )
        assert failed_test.status == VerificationTestStatus.FAILED

    def test_validation_status_checks(self):
        """Test validation status helper methods."""
        validation = Validation(
            status=ValidationStatus.PASSED,
            run_date=datetime.now(),
            verification_tests=[
                create_verification_test("look_ahead_bias", True, "OK"),
                create_verification_test("survivorship_bias", True, "OK"),
            ],
            results=ValidationResults(
                sharpe=0.8,
                consistency=0.7,
                max_drawdown=0.2,
                total_trades=100,
            ),
        )

        assert validation.is_validated() is True
        assert validation.all_verification_tests_passed() is True
        assert validation.passes_gates() is True

    def test_validation_failed_verification(self):
        """Test validation with failed verification tests."""
        validation = Validation(
            status=ValidationStatus.FAILED,
            verification_tests=[
                create_verification_test("look_ahead_bias", False, "Bias found"),
            ],
        )

        assert validation.is_validated() is False
        assert validation.all_verification_tests_passed() is False
        assert len(validation.get_failed_verification_tests()) == 1

    def test_validation_window_metrics(self):
        """Test validation window metrics."""
        window = ValidationWindow(
            period="2020-01-01 to 2021-12-31",
            sharpe=0.9,
            return_pct=0.15,
            max_drawdown=0.12,
            trades=50,
        )

        assert window.period == "2020-01-01 to 2021-12-31"
        assert window.sharpe == 0.9
        assert window.return_pct == 0.15

    def test_compute_consistency(self):
        """Test consistency computation from windows."""
        validation = Validation(
            status=ValidationStatus.RUNNING,
            windows=[
                ValidationWindow(period="W1", return_pct=0.1, sharpe=0.5),
                ValidationWindow(period="W2", return_pct=-0.05, sharpe=-0.2),
                ValidationWindow(period="W3", return_pct=0.08, sharpe=0.4),
                ValidationWindow(period="W4", return_pct=0.12, sharpe=0.6),
            ],
        )

        consistency = validation.compute_consistency()
        assert consistency == 0.75  # 3 out of 4 windows profitable


# =============================================================================
# EDGE CASES AND SERIALIZATION
# =============================================================================


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_minimal_simple_strategy(self):
        """Test minimal valid simple strategy."""
        data = {
            "id": "MIN-001",
            "name": "Minimal Strategy",
            "created": "2026-01-23T10:00:00Z",
            "source": {
                "reference": "Test",
                "excerpt": "Test strategy",
                "hash": "sha256:test",
                "extracted_date": "2026-01-23T10:00:00Z",
            },
            "hypothesis": {
                "summary": "Test hypothesis",
                "detail": "Test detail",
            },
            "strategy_mode": "simple",
            "universe": {
                "type": "static",
                "instruments": [{"symbol": "SPY", "asset_type": "etf"}],
            },
            "entry": {
                "type": "technical",
                "technical": {
                    "indicator": "sma_crossover",
                    "params": {},
                    "condition": "fast > slow",
                },
            },
            "position": {
                "type": "single_leg",
                "legs": [
                    {
                        "name": "main",
                        "direction": "long",
                        "instrument": {"source": "from_signal"},
                        "asset_type": "etf",
                    }
                ],
            },
            "exit": {
                "paths": [
                    {"name": "time", "type": "time_based", "params": {"hold_days": 5}}
                ],
            },
        }

        strategy = V4Strategy(**data)
        assert strategy.id == "MIN-001"

    def test_strategy_serialization_roundtrip(self):
        """Test that strategies can be serialized and deserialized."""
        strategy = V4Strategy(**STRATEGY_1_DATA)

        # Serialize to dict
        data = strategy.model_dump()

        # Deserialize back
        strategy2 = V4Strategy(**data)

        assert strategy2.id == strategy.id
        assert strategy2.name == strategy.name
        assert strategy2.strategy_mode == strategy.strategy_mode

    def test_optional_fields_default_correctly(self):
        """Test that optional fields have correct defaults."""
        quality = IngestionQuality()

        assert quality.specificity.score == 0
        assert quality.trust_score.total == 0
        assert quality.red_flags == []
        assert quality.decision == IngestionDecision.QUEUE

    def test_enum_string_values(self):
        """Test that enums serialize to string values."""
        strategy = V4Strategy(**STRATEGY_1_DATA)
        data = strategy.model_dump()

        # Check that enums are serialized as strings
        assert data["status"] == "pending"
        assert data["strategy_mode"] == "simple"
        assert data["tags"]["complexity"] == "complex"
