# QuantConnect Cloud Data Inventory

**Last updated:** 2026-02-22
**Source:** [QuantConnect Datasets Documentation](https://www.quantconnect.com/docs/v2/cloud-platform/datasets)

This document catalogs all data available on QuantConnect Cloud, organized by asset class. It serves as the authoritative reference for what instruments and data feeds are available for strategy development.

---

## FREE Core Market Data

### 1. US Equities

| Field | Detail |
|-------|--------|
| **Provider** | AlgoSeek (price data) + QuantConnect (security master) |
| **Cost** | FREE |
| **Universe** | ~27,500 securities (all US listed + delisted equities, ETFs, ETNs, ADRs, warrants) |
| **History** | January 1998 to present |
| **Resolutions** | Tick, Second, Minute, Hour, Daily |
| **Source** | Full SIP feed via Equinix (all exchanges + FINRA) |
| **Survivorship Bias** | Survivorship bias-free (includes delisted securities) |
| **Excludes** | OTC trades |
| **Updates** | Nightly at 4am ET |

**API Usage:**
```python
# Add a single equity
self.spy = self.add_equity("SPY", Resolution.DAILY)

# Universe selection with fundamental filtering
self.universe.add(self.universe.fundamental(self.fundamental_filter))

def fundamental_filter(self, fundamental):
    return [f.symbol for f in fundamental
            if f.has_fundamental_data
            and f.market_cap > 1e9
            and f.valuation_ratios.pe_ratio > 0]
```

**Related free datasets:**
- **US Equity Security Master** — Splits, dividends, delistings, mergers, ticker changes. 27,500 securities since Jan 1998.
- **US Equity Coarse Universe** — Daily dollar volume and price for universe selection.
- **US ETF Constituents** — Constituents and weightings for 2,650 ETFs. Since June 2009 (monthly before Jan 2015, daily after). Can be delayed up to 1 week.
- **US Equities Short Availability** — Shares available for shorting + borrow costs. 10,500 equities since Jan 2018.

**ETF Constituents API:**
```python
# Subscribe to ETF constituents universe
spy = Symbol.create("SPY", SecurityType.EQUITY, Market.USA)
self.universe_settings.resolution = Resolution.DAILY
self.add_universe(self.universe.etf(spy, universe_filter_func=self.etf_filter))

def etf_filter(self, constituents):
    return [c.symbol for c in constituents if c.weight > 0.001]
```

**Short Availability API:**
```python
# Check shortable quantity (requires InteractiveBrokersShortableProvider)
quantity = security.shortable_provider.shortable_quantity(symbol, self.time)
```

### 2. US Equity Options

| Field | Detail |
|-------|--------|
| **Provider** | AlgoSeek |
| **Cost** | FREE |
| **Symbols** | ~4,000 underlyings |
| **History** | January 2012 to present |
| **Resolutions** | Minute, Hour, Daily |
| **Data Included** | Trade/quote data, prices, strikes, expiries, open interest |
| **Option Types** | American Standard and Weekly Equity Options |
| **Greeks/IV** | Available via US Equity Option Universe dataset |
| **Source** | Options Price Reporting Authority (OPRA) feed |

**API Usage:**
```python
# Add equity options
equity = self.add_equity("SPY", Resolution.DAILY)
option = self.add_option("SPY", Resolution.DAILY)
option.set_filter(-5, +5, 30, 60)  # strikes +-5, 30-60 DTE

# Access option chains
def on_data(self, slice):
    for symbol, chain in slice.option_chains.items():
        for contract in chain:
            self.log(f"{contract.symbol} strike={contract.strike} "
                     f"bid={contract.bid_price} ask={contract.ask_price} "
                     f"delta={contract.greeks.delta} iv={contract.implied_volatility}")
```

**Related free dataset:**
- **US Equity Option Universe** — Greeks, implied volatility, universe selection data.

**Limitations:**
- Minute resolution is the finest available (no tick/second for options)
- Data starts 2012 only (no pre-2012 options history)
- Daily resolution can have sparse option chain data for some symbols

### 3. US Index Options

| Field | Detail |
|-------|--------|
| **Provider** | AlgoSeek |
| **Cost** | FREE |
| **Indexes** | SPX (S&P 500), VIX, NDX (Nasdaq 100) |
| **History** | January 2012 to present |
| **Resolutions** | Minute, Hour, Daily |
| **Option Style** | European-style |
| **Greeks/IV** | Available via US Index Option Universe dataset |

**API Usage:**
```python
# Add SPX index options (SPXW = weeklys)
self.spx = self.add_index_option("SPX", "SPXW", Resolution.DAILY)
self.spx.set_filter(lambda universe:
    universe.include_weeklys()
    .strikes(-10, +10)
    .expiration(7, 60))

# Access chains
def on_data(self, slice):
    for symbol, chain in slice.option_chains.items():
        puts = [c for c in chain if c.right == OptionRight.PUT]
        calls = [c for c in chain if c.right == OptionRight.CALL]
```

**Note:** RUT (Russell 2000) may also be available but is not confirmed in dataset listings.

### 4. US Futures

| Field | Detail |
|-------|--------|
| **Provider** | AlgoSeek |
| **Cost** | FREE |
| **Contracts** | 162 most liquid contracts |
| **Exchanges** | CME, CBOT, COMEX, NYMEX (NOT CFE) |
| **History** | May 2009 to present |
| **Resolutions** | Tick, Second, Minute, Hour, Daily |

**API Usage:**
```python
# Add a futures contract
self.gold = self.add_future(Futures.Metals.GOLD, Resolution.DAILY)
self.gold.set_filter(0, 90)  # contracts expiring within 90 days

# Continuous futures (for backtesting with seamless rolls)
self.es = self.add_future(Futures.Indices.SP_500_E_MINI,
    Resolution.DAILY,
    data_normalization_mode=DataNormalizationMode.BACKWARDS_RATIO,
    data_mapping_mode=DataMappingMode.OPEN_INTEREST,
    contract_depth_offset=0)

# Access futures chains
def on_data(self, slice):
    for symbol, chain in slice.future_chains.items():
        for contract in chain:
            self.log(f"{contract.symbol} expiry={contract.expiry} price={contract.last_price}")
```

**Key contracts (non-exhaustive):**
- **Equity Index:** ES (E-mini S&P 500), NQ (E-mini Nasdaq 100), YM (E-mini Dow), RTY (E-mini Russell 2000)
- **Micro Index:** MES, MNQ, MYM, M2K
- **Treasury:** ZB (30Y Bond), ZN (10Y Note), ZF (5Y Note), ZT (2Y Note)
- **Energy:** CL (Crude Oil), NG (Natural Gas), RB (Gasoline), HO (Heating Oil)
- **Metals:** GC (Gold), SI (Silver), HG (Copper), PL (Platinum), MGC (Micro Gold)
- **Agriculture:** ZC (Corn), ZW (Wheat), ZS (Soybeans), ZM (Soybean Meal), ZL (Soybean Oil)
- **Currencies:** 6E (Euro), 6J (Yen), 6B (Pound), 6A (AUD), 6C (CAD)

**Common Futures enum values:**
```python
Futures.Indices.SP_500_E_MINI        # ES
Futures.Indices.NASDAQ_100_E_MINI    # NQ
Futures.Indices.DOW_30_E_MINI        # YM
Futures.Indices.RUSSELL_2000_E_MINI  # RTY
Futures.Financials.Y_30_TREASURY_BOND  # ZB
Futures.Financials.Y_10_TREASURY_NOTE  # ZN
Futures.Financials.Y_5_TREASURY_NOTE   # ZF
Futures.Financials.Y_2_TREASURY_NOTE   # ZT
Futures.Energies.CRUDE_OIL_WTI       # CL
Futures.Energies.NATURAL_GAS         # NG
Futures.Metals.GOLD                  # GC
Futures.Metals.SILVER                # SI
Futures.Metals.COPPER                # HG
Futures.Grains.CORN                  # ZC
Futures.Grains.WHEAT                 # ZW
Futures.Grains.SOYBEANS              # ZS
```

**CRITICAL: No CFE data.** VIX Futures (VX) are NOT available through QC data provider. Requires Interactive Brokers data feed.

**Related free datasets:**
- **US Futures Security Master** — Continuous futures construction, contract details.
- **US Future Universe** — Universe selection for futures chains.

### 5. US Future Options

| Field | Detail |
|-------|--------|
| **Provider** | AlgoSeek |
| **Cost** | FREE |
| **Contracts** | 16 monthly futures contracts |
| **Exchanges** | CME, CBOT, COMEX, NYMEX |
| **History** | January 2012 to present |
| **Resolutions** | Minute only |

**API Usage:**
```python
# Add future options on an existing futures contract
future = self.add_future(Futures.Indices.SP_500_E_MINI, Resolution.MINUTE)
future.set_filter(0, 90)
self.add_future_option(future.symbol, lambda universe: universe.strikes(-5, +5))

# Access via option chains in on_data
def on_data(self, slice):
    for symbol, chain in slice.option_chains.items():
        for contract in chain:
            self.log(f"FOP: {contract.symbol} strike={contract.strike}")
```

### 6. International Futures

| Field | Detail |
|-------|--------|
| **Provider** | TickData |
| **Cost** | FREE |
| **Contracts** | FESX (Euro Stoxx 50), HSI (Hang Seng), NKD (Nikkei 225) |
| **History** | July 1998 to present |
| **Resolutions** | Tick to Daily |

**API Usage:**
```python
self.fesx = self.add_future(Futures.Indices.EURO_STOXX_50, Resolution.DAILY)
self.hsi = self.add_future(Futures.Indices.HANG_SENG, Resolution.DAILY)
self.nkd = self.add_future(Futures.Indices.NIKKEI_225, Resolution.DAILY)
```

### 7. Forex

| Field | Detail |
|-------|--------|
| **Provider** | QuantConnect (sourced from OANDA) |
| **Cost** | FREE |
| **Pairs** | 71 pairs (OANDA), 13 pairs (FXCM) |
| **History** | April 2004 to present (OANDA), April 2007 (FXCM) |
| **Resolutions** | Tick, Second, Minute, Hour, Daily |
| **Data Type** | Quote data (bid/ask) |

**API Usage:**
```python
self.eurusd = self.add_forex("EURUSD", Resolution.DAILY, Market.OANDA)
self.gbpusd = self.add_forex("GBPUSD", Resolution.DAILY, Market.OANDA)

# Access quote data
def on_data(self, slice):
    if self.eurusd.symbol in slice.quote_bars:
        bar = slice.quote_bars[self.eurusd.symbol]
        mid = (bar.bid.close + bar.ask.close) / 2
```

### 8. Crypto

| Field | Detail |
|-------|--------|
| **Provider** | CoinAPI (price data) + QuantConnect (universe) |
| **Cost** | FREE |
| **Exchanges** | Binance, Binance US, Bitfinex, Bybit, Coinbase, Kraken |
| **History** | All available history (varies by exchange/pair) |
| **Resolutions** | Tick, Second, Minute, Hour, Daily |

**API Usage:**
```python
self.btc = self.add_crypto("BTCUSD", Resolution.DAILY, Market.COINBASE)
self.eth = self.add_crypto("ETHUSD", Resolution.DAILY, Market.COINBASE)

# Crypto universe selection
self.add_universe(CryptoUniverse.coinbase(self.universe_filter))

def universe_filter(self, data):
    return [d.symbol for d in data if d.volume_in_usd > 1e6]
```

### 9. Crypto Futures

| Field | Detail |
|-------|--------|
| **Provider** | CoinAPI + QuantConnect |
| **Cost** | FREE |
| **Exchanges** | Binance, Bybit, dYdX |
| **History** | All available history |
| **Resolutions** | Tick, Second, Minute, Hour, Daily |

**API Usage:**
```python
self.btc_future = self.add_crypto_future("BTCUSD", Resolution.DAILY, Market.BINANCE)
```

### 10. CFD

| Field | Detail |
|-------|--------|
| **Provider** | QuantConnect (sourced from OANDA) |
| **Cost** | FREE |
| **Instruments** | Various (indices, commodities, metals via OANDA CFDs) |
| **History** | All available history |
| **Resolutions** | Tick, Second, Minute, Hour, Daily |

**API Usage:**
```python
self.spx_cfd = self.add_cfd("SPX500USD", Resolution.DAILY, Market.OANDA)
self.gold_cfd = self.add_cfd("XAUUSD", Resolution.DAILY, Market.OANDA)
```

### 11. Cash Indices

| Field | Detail |
|-------|--------|
| **Provider** | QuantConnect |
| **Cost** | FREE |
| **Indices** | 125 US indices + 3 international (HSI, SX5E) |
| **History** | Various start dates from January 1998 |
| **Resolutions** | Minute to Daily |
| **Key Indices** | SPX, VIX, NDX, RUT |

**API Usage:**
```python
# Indices are for signal computation only — NOT directly tradeable
self.vix = self.add_index("VIX", Resolution.DAILY)
self.spx = self.add_index("SPX", Resolution.DAILY)

def on_data(self, slice):
    if self.vix.symbol in slice.bars:
        vix_level = slice.bars[self.vix.symbol].close
```

**Note:** Index data is for signal computation only — indices are not directly tradeable.

---

## FREE Fundamental & Macro Data

### 12. Morningstar US Fundamentals

| Field | Detail |
|-------|--------|
| **Cost** | FREE |
| **Coverage** | ~8,000 US equities |
| **Properties** | ~1,100 fundamental fields |
| **History** | January 1998 to present |
| **Exchanges** | NYSE, NASDAQ, AMEX, BATS |
| **Update Frequency** | Financial ratios daily; bulk monthly |

**API Usage:**
```python
# Access via fundamental universe selection
self.universe.add(self.universe.fundamental(self.fundamental_filter))

def fundamental_filter(self, fundamental):
    # Filter by multiple fundamental criteria
    filtered = [f for f in fundamental
                if f.has_fundamental_data
                and f.market_cap > 2e9
                and f.valuation_ratios.pe_ratio > 0
                and f.valuation_ratios.pe_ratio < 25
                and f.operation_ratios.roe.one_year > 0.10]

    # Sort by a factor and take top N
    sorted_by_value = sorted(filtered,
        key=lambda f: f.valuation_ratios.pe_ratio)
    return [f.symbol for f in sorted_by_value[:50]]

# Key field paths:
# f.market_cap
# f.valuation_ratios.pe_ratio
# f.valuation_ratios.pb_ratio
# f.valuation_ratios.ps_ratio
# f.valuation_ratios.ev_to_ebitda
# f.valuation_ratios.dividend_yield
# f.operation_ratios.roe.one_year
# f.operation_ratios.roa.one_year
# f.operation_ratios.total_debt_equity_ratio.one_year
# f.earning_reports.basic_eps.three_months
# f.asset_classification.morningstar_sector_code
# f.asset_classification.style_box  (1=LargeValue ... 9=SmallGrowth)
```

**Key field categories:**
- Valuation: PE, PB, PS, EV/EBITDA, dividend yield
- Financials: Income statement, balance sheet, cash flow (quarterly/annual)
- Classification: Morningstar sector/industry codes, market cap
- Growth: Revenue growth, earnings growth
- Quality: ROE, ROA, debt/equity, current ratio
- Per-share: EPS, book value, revenue, dividends

**Limitations:**
- Uses "As Originally Reported" figures (errors not retroactively corrected)
- Older symbols: filing dates approximated at 45 days post-reporting
- Fill-forward applied when no update on a given day

### 13. US Treasury Yield Curve

| Field | Detail |
|-------|--------|
| **Provider** | US Department of Treasury |
| **Cost** | FREE |
| **History** | January 1990 to present |
| **Frequency** | Daily |
| **Tenors** | 1mo, 3mo, 6mo, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y |

**API Usage:**
```python
# Add treasury yield curve data
self.yield_curve = self.add_data(USTreasuryYieldCurveRate, "USTYCR", Resolution.DAILY)

def on_data(self, slice):
    yc = slice.get(USTreasuryYieldCurveRate)
    if yc:
        ten_year = yc.ten_year
        two_year = yc.two_year
        one_month = yc.one_month
        spread_10y_2y = ten_year - two_year  # yield curve slope
        # Available tenors: one_month, three_month, six_month, one_year,
        # two_year, three_year, five_year, seven_year, ten_year,
        # twenty_year, thirty_year
```

### 14. FRED (Federal Reserve Economic Data)

| Field | Detail |
|-------|--------|
| **Provider** | Federal Reserve Bank of St. Louis |
| **Cost** | FREE (requires FRED API key) |
| **History** | January 1999 to present (varies by series) |
| **Series** | 560 datasets from 85+ sources |
| **Frequency** | Daily delivery; actual frequency varies |

**API Usage:**
```python
# Add FRED data series (examples)
self.recession = self.add_data(Fred,
    Fred.OECDRecessionIndicators.UNITED_STATES_FROM_PEAK_THROUGH_THE_TROUGH,
    Resolution.DAILY)

self.unemployment = self.add_data(Fred,
    Fred.ContinuedClaimsInsuredUnemployment.CCSA,
    Resolution.DAILY)

def on_data(self, slice):
    # Access via slice.get
    recession_data = slice.get(Fred, self.recession.symbol)
    if recession_data:
        value = recession_data.value

# Common FRED series:
# Fred.OECDRecessionIndicators.UNITED_STATES_FROM_PEAK_THROUGH_THE_TROUGH
# Fred.ContinuedClaimsInsuredUnemployment.CCSA
# Fred.ConsumerPriceIndex.*
# Fred.GrossDomesticProduct.*
# Fred.UnemploymentRate.*
# Fred.ConsumerSentiment.*
```

Key categories: GDP, CPI, unemployment, recession indicators, OECD indicators, treasury rates, exchange rates, consumer confidence.

### 15. US Interest Rate (FOMC)

| Field | Detail |
|-------|--------|
| **Provider** | Federal Reserve Bank of St. Louis |
| **Cost** | FREE |
| **History** | January 2003 to present |
| **Frequency** | Daily |
| **Content** | FOMC primary credit rate |

**API Usage:**
```python
self.interest_rate = self.add_data(FedRateDecision, "FOMC", Resolution.DAILY)

def on_data(self, slice):
    rate = slice.get(FedRateDecision)
    if rate:
        self.log(f"Fed rate: {rate.value}")
```

### 16. EIA Energy Data

| Field | Detail |
|-------|--------|
| **Provider** | US Energy Information Administration |
| **Cost** | FREE |
| **History** | January 1991 to present |
| **Series** | 190 datasets |
| **Content** | Oil production/consumption, supply/demand |

**API Usage:**
```python
self.crude_storage = self.add_data(
    USEnergy,
    USEnergy.Petroleum.UnitedStates.WEEKLY_ENDING_STOCKS_OF_CRUDE_OIL,
    Resolution.DAILY)
```

### 17. VIX Central Contango

| Field | Detail |
|-------|--------|
| **Provider** | VIX Central (cached by QC) |
| **Cost** | FREE |
| **History** | June 2010 to present |
| **Frequency** | Daily |
| **Content** | VIX Futures (VX) contango rates for 12 nearest-to-expiration contracts |

**API Usage:**
```python
self.vix_contango = self.add_data(VIXCentralContango, "VX", Resolution.DAILY)

def on_data(self, slice):
    contango = slice.get(VIXCentralContango)
    if contango:
        # Front-month contango (F2 - F1) / F1
        front_contango = contango.contango_f_2_minus_f_1
        # Available: contango_f_2_minus_f_1 through contango_f_12_minus_f_11
        # Positive = contango (normal), Negative = backwardation (stress)
```

---

## FREE Corporate Event & Alternative Data

### 18. EOD Historical Data Suite (All FREE)

| Dataset | Coverage | Start Date | Frequency |
|---------|----------|------------|-----------|
| Upcoming Earnings | US Equities | Jan 1998 | Daily (7:30am) |
| Upcoming Dividends | US Equities | Jan 2015 | Daily (7:30am) |
| Upcoming Splits | US Equities | Jan 2010 | Daily (7:30am) |
| Upcoming IPOs | US Equities | Feb 2013 | Daily |
| Economic Events | Global | Jan 2019 | Daily (7:30am) |
| Macroeconomic Indicators | Global | Varies | Daily |

**API Usage:**
```python
# Upcoming Earnings universe — fires when earnings are approaching
self.add_universe(EODHDUpcomingEarnings, self.earnings_filter)

def earnings_filter(self, data):
    return [d.symbol for d in data if d.report_date is not None]

# Upcoming Dividends
self.add_data(EODHDUpcomingDividends, "dividends")

# Upcoming Splits
self.add_data(EODHDUpcomingSplits, "splits")

# Upcoming IPOs
self.add_data(EODHDUpcomingIPOs, "ipos")
```

### 19. SEC Filings

| Field | Detail |
|-------|--------|
| **Cost** | FREE |
| **Coverage** | ~15,000 US equities |
| **History** | January 1998 to present |
| **Filing Types** | 8-K, 10-Q, 10-K |
| **Note** | Semi-parsed; contents range from plain text to XBRL |

**API Usage:**
```python
# Add SEC filing data for a specific equity
equity = self.add_equity("AAPL", Resolution.DAILY)
self.add_data(SECReport8K, equity.symbol)   # Current reports (material events)
self.add_data(SECReport10K, equity.symbol)  # Annual reports
self.add_data(SECReport10Q, equity.symbol)  # Quarterly reports

def on_data(self, slice):
    # Access filing data
    reports = slice.get(SECReport8K)
    if reports:
        for report in reports.values():
            self.log(f"8-K filed: {report.report.document}")
```

### 20. Tiingo News Feed

| Field | Detail |
|-------|--------|
| **Cost** | FREE |
| **Coverage** | 10,000 US equities |
| **Sources** | 120+ news providers |
| **History** | January 2014 to present |
| **Frequency** | Live streaming, second-level |

**API Usage:**
```python
# Add news for a specific equity
equity = self.add_equity("AAPL", Resolution.DAILY)
self.tiingo_symbol = self.add_data(TiingoNews, equity.symbol).symbol

def on_data(self, slice):
    if self.tiingo_symbol in slice:
        article = slice[self.tiingo_symbol]
        self.log(f"News: {article.title} | Source: {article.source}")
```

### 21. Quiver Insider Trading

| Field | Detail |
|-------|--------|
| **Cost** | FREE |
| **Coverage** | US equities |
| **Content** | SEC insider disclosures (executive buys/sells) |
| **Frequency** | Daily |

**API Usage:**
```python
# Per-symbol insider trading data
equity = self.add_equity("AAPL", Resolution.DAILY)
self.add_data(QuiverInsiderTrading, equity.symbol)

# Universe-wide insider trading (all filings)
self.add_universe(QuiverInsiderTradingUniverse, self.insider_filter)

def insider_filter(self, data):
    # Filter for large insider purchases
    return [d.symbol for d in data
            if d.shares is not None and d.shares > 10000
            and d.direction == OrderDirection.BUY]
```

### 22. Bitcoin Metadata

| Field | Detail |
|-------|--------|
| **Cost** | FREE |
| **Coverage** | Bitcoin blockchain |
| **History** | January 2009 to present |
| **Metrics** | 23 (hash rate, fees, addresses, block size, etc.) |

**API Usage:**
```python
self.btc_metadata = self.add_data(BitcoinMetadata, "BTC", Resolution.DAILY)

def on_data(self, slice):
    data = slice.get(BitcoinMetadata)
    if data:
        self.log(f"Hash rate: {data.hash_rate}, Addresses: {data.address_count}")
```

### 23. CoinGecko Crypto Market Cap

| Field | Detail |
|-------|--------|
| **Cost** | FREE |
| **Coverage** | 620 cryptocurrencies |
| **History** | April 2013 to present |
| **Frequency** | Daily |

**API Usage:**
```python
self.add_universe(CoinGecko, self.crypto_filter)

def crypto_filter(self, data):
    return [d.symbol for d in data if d.market_cap > 1e9]
```

---

## Paid Data

### Sentiment & NLP

| Dataset | Provider | Price | Coverage | Start |
|---------|----------|-------|----------|-------|
| Brain Sentiment Indicator | Brain | $25/mo | 4,500 US equities | Aug 2016 |
| Brain Language Metrics | Brain | $25/mo | 5,000 US equities | Jan 2010 |
| Benzinga News Feed | Benzinga | $120/mo | 8,000 US equities | Jan 2016 |

### ML & Factor Models

| Dataset | Provider | Price | Coverage | Start |
|---------|----------|-------|----------|-------|
| Brain ML Stock Ranking | Brain | $25/mo | 1,000 US equities | Jan 2010 |
| ExtractAlpha Cross Asset Model | ExtractAlpha | $75/mo | 3,000+ US equities | Jul 2005 |
| ExtractAlpha True Beats | ExtractAlpha | $75/mo | 4,000-5,000 US equities | Jan 2000 |
| Kavout Composite Factors | Kavout | $39/mo | All NYSE/NASDAQ | Since 2003 |

### Earnings Estimates

| Dataset | Provider | Price | Coverage | Start |
|---------|----------|-------|----------|-------|
| Estimize Crowdsourced | ExtractAlpha | $75/mo | 2,800+ US equities | Jan 2011 |

### Social & Political

| Dataset | Provider | Price | Coverage | Start |
|---------|----------|-------|----------|-------|
| WallStreetBets | Quiver | $5/mo | 6,000 US equities | Aug 2018 |
| US Congress Trading | Quiver | $5/mo | 1,800 US equities | Jan 2016 |
| CNBC Trading | Quiver | $5/mo | 1,500+ US equities | Dec 2020 |
| Corporate Lobbying | Quiver | $5/mo | US equities | Varies |
| US Government Contracts | Quiver | $5/mo | 700+ US equities | Oct 2019 |

### Corporate Actions

| Dataset | Provider | Price | Coverage | Start |
|---------|----------|-------|----------|-------|
| Corporate Buybacks (intentions) | Smart Insider | $10/mo | 3,000 US equities | May 2015 |
| Corporate Buybacks (transactions) | Smart Insider | $10/mo | 3,000 US equities | May 2015 |

### Regulatory

| Dataset | Provider | Price | Coverage | Start |
|---------|----------|-------|----------|-------|
| US Regulatory Alerts | RegAlytics | $10/mo | 2.5M+ alerts | Jan 2020 |

### Other

| Dataset | Provider | Price | Coverage |
|---------|----------|-------|----------|
| Nasdaq Data Link | Nasdaq | Varies | Millions of series from 400+ sources |

---

## Known Gaps

1. **VIX Futures (CFE)** — Not available via QC data provider. Requires IB data feed.
2. **International equities** — No European, Asian, or EM stock-level data.
3. **International futures** — Only 3 contracts (FESX, HSI, NKD).
4. **Options before 2012** — No pre-2012 options history.
5. **Sub-minute options** — Minute is the finest resolution for options.
6. **Individual bonds** — No bond-level data. Treasury yield curve and futures only.
7. **Daily options chain sparsity** — Some symbols have sparse chains at daily resolution. Minute resolution recommended for options.

---

## Sources

- [QuantConnect Datasets Documentation](https://www.quantconnect.com/docs/v2/cloud-platform/datasets)
- [QuantConnect Pricing](https://www.quantconnect.com/pricing/)
- [QuantConnect Tier Features](https://www.quantconnect.com/docs/v2/cloud-platform/organizations/tier-features)
