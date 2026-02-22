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

**Related free datasets:**
- **US Equity Security Master** — Splits, dividends, delistings, mergers, ticker changes. 27,500 securities since Jan 1998.
- **US Equity Coarse Universe** — Daily dollar volume and price for universe selection.
- **US ETF Constituents** — Constituents and weightings for 2,650 ETFs. Since June 2009 (monthly before Jan 2015, daily after). Can be delayed up to 1 week.
- **US Equities Short Availability** — Shares available for shorting + borrow costs. 10,500 equities since Jan 2018.

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

**Key contracts (non-exhaustive):**
- **Equity Index:** ES (E-mini S&P 500), NQ (E-mini Nasdaq 100), YM (E-mini Dow), RTY (E-mini Russell 2000)
- **Micro Index:** MES, MNQ, MYM, M2K
- **Treasury:** ZB (30Y Bond), ZN (10Y Note), ZF (5Y Note), ZT (2Y Note)
- **Energy:** CL (Crude Oil), NG (Natural Gas), RB (Gasoline), HO (Heating Oil)
- **Metals:** GC (Gold), SI (Silver), HG (Copper), PL (Platinum), MGC (Micro Gold)
- **Agriculture:** ZC (Corn), ZW (Wheat), ZS (Soybeans), ZM (Soybean Meal), ZL (Soybean Oil)
- **Currencies:** 6E (Euro), 6J (Yen), 6B (Pound), 6A (AUD), 6C (CAD)

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

### 6. International Futures

| Field | Detail |
|-------|--------|
| **Provider** | TickData |
| **Cost** | FREE |
| **Contracts** | FESX (Euro Stoxx 50), HSI (Hang Seng), NKD (Nikkei 225) |
| **History** | July 1998 to present |
| **Resolutions** | Tick to Daily |

### 7. Forex

| Field | Detail |
|-------|--------|
| **Provider** | QuantConnect (sourced from OANDA) |
| **Cost** | FREE |
| **Pairs** | 71 pairs (OANDA), 13 pairs (FXCM) |
| **History** | April 2004 to present (OANDA), April 2007 (FXCM) |
| **Resolutions** | Tick, Second, Minute, Hour, Daily |
| **Data Type** | Quote data (bid/ask) |

### 8. Crypto

| Field | Detail |
|-------|--------|
| **Provider** | CoinAPI (price data) + QuantConnect (universe) |
| **Cost** | FREE |
| **Exchanges** | Binance, Binance US, Bitfinex, Bybit, Coinbase, Kraken |
| **History** | All available history (varies by exchange/pair) |
| **Resolutions** | Tick, Second, Minute, Hour, Daily |

### 9. Crypto Futures

| Field | Detail |
|-------|--------|
| **Provider** | CoinAPI + QuantConnect |
| **Cost** | FREE |
| **Exchanges** | Binance, Bybit, dYdX |
| **History** | All available history |
| **Resolutions** | Tick, Second, Minute, Hour, Daily |

### 10. CFD

| Field | Detail |
|-------|--------|
| **Provider** | QuantConnect (sourced from OANDA) |
| **Cost** | FREE |
| **Instruments** | Various (indices, commodities, metals via OANDA CFDs) |
| **History** | All available history |
| **Resolutions** | Tick, Second, Minute, Hour, Daily |

### 11. Cash Indices

| Field | Detail |
|-------|--------|
| **Provider** | QuantConnect |
| **Cost** | FREE |
| **Indices** | 125 US indices + 3 international (HSI, SX5E) |
| **History** | Various start dates from January 1998 |
| **Resolutions** | Minute to Daily |
| **Key Indices** | SPX, VIX, NDX, RUT |
| **Access** | `self.add_index("VIX", Resolution.DAILY)` |

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

### 14. FRED (Federal Reserve Economic Data)

| Field | Detail |
|-------|--------|
| **Provider** | Federal Reserve Bank of St. Louis |
| **Cost** | FREE (requires FRED API key) |
| **History** | January 1999 to present (varies by series) |
| **Series** | 560 datasets from 85+ sources |
| **Frequency** | Daily delivery; actual frequency varies |

Key categories: GDP, CPI, unemployment, recession indicators, OECD indicators, treasury rates, exchange rates, consumer confidence.

### 15. US Interest Rate (FOMC)

| Field | Detail |
|-------|--------|
| **Provider** | Federal Reserve Bank of St. Louis |
| **Cost** | FREE |
| **History** | January 2003 to present |
| **Frequency** | Daily |
| **Content** | FOMC primary credit rate |

### 16. EIA Energy Data

| Field | Detail |
|-------|--------|
| **Provider** | US Energy Information Administration |
| **Cost** | FREE |
| **History** | January 1991 to present |
| **Series** | 190 datasets |
| **Content** | Oil production/consumption, supply/demand |

### 17. VIX Central Contango

| Field | Detail |
|-------|--------|
| **Provider** | VIX Central (cached by QC) |
| **Cost** | FREE |
| **History** | June 2010 to present |
| **Frequency** | Daily |
| **Content** | VIX Futures (VX) contango rates for 12 nearest-to-expiration contracts |

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

### 19. SEC Filings

| Field | Detail |
|-------|--------|
| **Cost** | FREE |
| **Coverage** | ~15,000 US equities |
| **History** | January 1998 to present |
| **Filing Types** | 8-K, 10-Q, 10-K |
| **Note** | Semi-parsed; contents range from plain text to XBRL |

### 20. Tiingo News Feed

| Field | Detail |
|-------|--------|
| **Cost** | FREE |
| **Coverage** | 10,000 US equities |
| **Sources** | 120+ news providers |
| **History** | January 2014 to present |
| **Frequency** | Live streaming, second-level |

### 21. Quiver Insider Trading

| Field | Detail |
|-------|--------|
| **Cost** | FREE |
| **Coverage** | US equities |
| **Content** | SEC insider disclosures (executive buys/sells) |
| **Frequency** | Daily |

### 22. Bitcoin Metadata

| Field | Detail |
|-------|--------|
| **Cost** | FREE |
| **Coverage** | Bitcoin blockchain |
| **History** | January 2009 to present |
| **Metrics** | 23 (hash rate, fees, addresses, block size, etc.) |

### 23. CoinGecko Crypto Market Cap

| Field | Detail |
|-------|--------|
| **Cost** | FREE |
| **Coverage** | 620 cryptocurrencies |
| **History** | April 2013 to present |
| **Frequency** | Daily |

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
