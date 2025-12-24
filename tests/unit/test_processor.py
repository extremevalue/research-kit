"""Tests for ingest processor, focusing on QC Native data recognition."""

import pytest
from pathlib import Path

from research_system.ingest.processor import IngestProcessor


class TestQCNativeDataRecognition:
    """Test auto-recognition of QuantConnect Native data sources."""

    @pytest.fixture
    def processor(self, temp_workspace):
        """Create a processor with a test workspace."""
        return IngestProcessor(temp_workspace, llm_client=None)

    # Standard equity/ETF patterns
    def test_recognizes_any_ticker_prices(self, processor):
        """Any valid ticker with _prices suffix should be recognized."""
        tickers = ["spy", "aapl", "msft", "tsla", "goog", "nvda", "amzn"]
        for ticker in tickers:
            assert processor._is_qc_native_data(f"{ticker}_prices") is True, f"{ticker}_prices not recognized"

    def test_recognizes_any_ticker_data(self, processor):
        """Any valid ticker with _data suffix should be recognized."""
        tickers = ["spy", "aapl", "btc", "eth", "eurusd"]
        for ticker in tickers:
            assert processor._is_qc_native_data(f"{ticker}_data") is True, f"{ticker}_data not recognized"

    def test_recognizes_etfs(self, processor):
        """Common ETFs should be recognized."""
        etfs = ["iwm", "qqq", "dia", "efa", "eem", "gld", "tlt", "vti", "voo"]
        for etf in etfs:
            assert processor._is_qc_native_data(f"{etf}_prices") is True, f"{etf}_prices not recognized"

    def test_recognizes_sector_etfs(self, processor):
        """Sector ETFs should be recognized."""
        sectors = ["xlk", "xlf", "xlv", "xle", "xli", "xly", "xlp", "xlu", "xlb", "xlc", "xlre"]
        for sector in sectors:
            assert processor._is_qc_native_data(f"{sector}_prices") is True, f"{sector}_prices not recognized"

    def test_recognizes_international_etfs(self, processor):
        """International ETFs should be recognized."""
        intl = ["efa", "eem", "vgk", "ewj", "vpl", "vwo"]
        for etf in intl:
            assert processor._is_qc_native_data(f"{etf}_prices") is True, f"{etf}_prices not recognized"

    def test_recognizes_futures_symbols(self, processor):
        """Futures symbols should be recognized."""
        futures = ["es", "nq", "cl", "gc", "zb", "zn"]
        for fut in futures:
            assert processor._is_qc_native_data(f"{fut}_prices") is True, f"{fut}_prices not recognized"

    def test_recognizes_crypto(self, processor):
        """Crypto symbols should be recognized."""
        crypto = ["btc", "eth", "sol", "ada"]
        for coin in crypto:
            assert processor._is_qc_native_data(f"{coin}_prices") is True, f"{coin}_prices not recognized"

    def test_recognizes_forex(self, processor):
        """Forex pairs should be recognized."""
        forex = ["eurusd", "gbpusd", "usdjpy"]
        for pair in forex:
            assert processor._is_qc_native_data(f"{pair}_prices") is True, f"{pair}_prices not recognized"

    # Special data sources
    def test_recognizes_risk_free_rate(self, processor):
        """Risk free rate should be recognized as special QC Native."""
        assert processor._is_qc_native_data("risk_free_rate") is True

    def test_recognizes_treasury_yields(self, processor):
        """Treasury yields should be recognized as special QC Native."""
        assert processor._is_qc_native_data("treasury_yields") is True

    def test_recognizes_options_data(self, processor):
        """Options data should be recognized."""
        assert processor._is_qc_native_data("options_data") is True

    def test_recognizes_futures_data(self, processor):
        """Futures data should be recognized."""
        assert processor._is_qc_native_data("futures_data") is True

    def test_recognizes_forex_data(self, processor):
        """Forex data should be recognized."""
        assert processor._is_qc_native_data("forex_data") is True

    def test_recognizes_crypto_data(self, processor):
        """Crypto data should be recognized."""
        assert processor._is_qc_native_data("crypto_data") is True

    # Edge cases and validation
    def test_rejects_no_suffix(self, processor):
        """Bare tickers without suffix should not be recognized."""
        assert processor._is_qc_native_data("spy") is False
        assert processor._is_qc_native_data("aapl") is False

    def test_rejects_invalid_suffix(self, processor):
        """Invalid suffixes should not be recognized."""
        assert processor._is_qc_native_data("spy_indicator") is False
        assert processor._is_qc_native_data("spy_custom") is False

    def test_rejects_very_long_tickers(self, processor):
        """Very long ticker names should not be auto-recognized."""
        # Tickers > 6 chars need explicit registry entry
        assert processor._is_qc_native_data("verylongticker_prices") is False

    def test_rejects_empty_ticker(self, processor):
        """Empty ticker should not be recognized."""
        assert processor._is_qc_native_data("_prices") is False

    def test_specialized_data_not_auto_recognized(self, processor):
        """Specialized data sources should NOT be auto-recognized."""
        # These need explicit registry entries
        assert processor._is_qc_native_data("mcclellan_oscillator") is False
        assert processor._is_qc_native_data("tick_order_flow") is False
        assert processor._is_qc_native_data("proprietary_indicator") is False


class TestCheckDataRequirements:
    """Test data requirement checking with QC Native recognition."""

    @pytest.fixture
    def processor(self, temp_workspace):
        """Create a processor with a test workspace."""
        return IngestProcessor(temp_workspace, llm_client=None)

    def test_all_standard_market_data_returns_empty(self, processor):
        """Standard market data requirements should return empty missing list."""
        reqs = ["spy_prices", "aapl_prices", "msft_prices", "btc_data", "eurusd_prices"]
        missing = processor._check_data_requirements(reqs)
        assert missing == [], f"Expected no missing, got {missing}"

    def test_individual_stocks_recognized(self, processor):
        """Individual stock tickers should be recognized."""
        reqs = ["aapl_prices", "msft_prices", "goog_prices", "nvda_prices", "tsla_prices"]
        missing = processor._check_data_requirements(reqs)
        assert missing == [], f"Expected no missing, got {missing}"

    def test_returns_truly_unavailable_data(self, processor):
        """Should return data that is truly unavailable (specialized sources)."""
        reqs = ["spy_prices", "mcclellan_oscillator", "tick_order_flow"]
        missing = processor._check_data_requirements(reqs)
        assert "spy_prices" not in missing
        assert "mcclellan_oscillator" in missing
        assert "tick_order_flow" in missing

    def test_normalizes_input(self, processor):
        """Should normalize data requirement IDs."""
        reqs = ["SPY_PRICES", "spy-prices", "spy prices"]
        missing = processor._check_data_requirements(reqs)
        assert missing == []

    def test_handles_empty_requirements(self, processor):
        """Should handle empty or None requirements gracefully."""
        assert processor._check_data_requirements([]) == []
        assert processor._check_data_requirements(["", None, "spy_prices"]) == []

    def test_sector_rotation_strategy_requirements(self, processor):
        """Real-world test: sector rotation strategy requirements from issue #12."""
        reqs = [
            "spy_prices", "iwm_prices", "efa_prices", "eem_prices",
            "vgk_prices", "ewj_prices", "vpl_prices", "vnq_prices",
            "gld_prices", "tlt_prices", "tip_prices", "dbc_prices",
            "agg_prices", "shy_prices", "xlk_prices", "xlf_prices",
            "xlv_prices", "xle_prices", "xli_prices", "xly_prices",
            "xlp_prices", "xlu_prices", "xlb_prices", "xlre_prices",
            "xlc_prices", "risk_free_rate"
        ]
        missing = processor._check_data_requirements(reqs)
        assert missing == [], f"Expected no missing data, got: {missing}"

    def test_mixed_standard_and_specialized(self, processor):
        """Mix of standard market data and specialized sources."""
        reqs = [
            "spy_prices",           # Standard - should pass
            "aapl_prices",          # Standard - should pass
            "risk_free_rate",       # Special - should pass
            "mcclellan_oscillator", # Specialized - needs registry
            "custom_breadth_data",  # Specialized - needs registry
        ]
        missing = processor._check_data_requirements(reqs)
        assert "spy_prices" not in missing
        assert "aapl_prices" not in missing
        assert "risk_free_rate" not in missing
        # These should be in missing (unless in registry)
        assert "mcclellan_oscillator" in missing or "custom_breadth_data" in missing
