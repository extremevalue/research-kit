"""
Data Registry Management

Manages data sources for the research validation system.
Each data source is tracked with availability across different tiers:
- QC Native (QuantConnect built-in)
- QC Object Store (uploaded to QC cloud)
- Internal Purchased (paid data)
- Internal Curated (validated free data)
- Internal Experimental (unverified data)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DataAvailability:
    """Availability status for a data source."""
    available: bool
    source_tier: Optional[str] = None
    path: Optional[str] = None
    key: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class DataSource:
    """Represents a data source."""
    id: str
    name: str
    data_type: str
    description: Optional[str]
    availability: Dict[str, Any]
    coverage: Optional[Dict[str, Any]]
    columns: Optional[List[str]]
    usage_notes: Optional[str]
    aliases: Optional[List[str]] = None  # Alternative names that resolve to this source
    is_auto_recognized: bool = False  # True if auto-recognized from QC Native pattern

    def is_qc_native(self) -> bool:
        """Check if this source is QC Native data."""
        qc_native = self.availability.get("qc_native", {})
        if isinstance(qc_native, dict):
            return qc_native.get("available", False)
        return qc_native is True

    def is_available(self) -> bool:
        """Check if data is available in any tier."""
        tiers = ["qc_native", "qc_object_store", "internal_purchased",
                 "internal_curated", "internal_experimental"]
        for tier in tiers:
            tier_data = self.availability.get(tier, {})
            if isinstance(tier_data, dict) and tier_data.get("available", False):
                return True
            elif tier_data is True:
                return True
        return False

    def best_source(self) -> Optional[DataAvailability]:
        """Get the best available source (following hierarchy)."""
        tiers = [
            ("qc_native", "QC Native"),
            ("qc_object_store", "QC Object Store"),
            ("internal_purchased", "Internal Purchased"),
            ("internal_curated", "Internal Curated"),
            ("internal_experimental", "Internal Experimental")
        ]

        for tier_key, tier_name in tiers:
            tier_data = self.availability.get(tier_key, {})
            if isinstance(tier_data, dict) and tier_data.get("available", False):
                return DataAvailability(
                    available=True,
                    source_tier=tier_name,
                    path=tier_data.get("path"),
                    key=tier_data.get("key"),
                    notes=tier_data.get("notes")
                )
            elif tier_data is True:
                return DataAvailability(
                    available=True,
                    source_tier=tier_name
                )

        return DataAvailability(available=False)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "type": self.data_type,
            "description": self.description,
            "availability": self.availability,
            "coverage": self.coverage,
            "columns": self.columns,
            "usage_notes": self.usage_notes
        }
        if self.aliases:
            result["aliases"] = self.aliases
        if self.is_auto_recognized:
            result["is_auto_recognized"] = True
        return result


class DataRegistry:
    """
    Manages data source definitions and availability.

    The registry maintains a hierarchical view of data availability:
    1. QC Native - Always preferred when available
    2. QC Object Store - Data uploaded to QuantConnect
    3. Internal Purchased - Paid data (never delete)
    4. Internal Curated - Validated free data
    5. Internal Experimental - Unverified data

    Additionally, the registry auto-recognizes standard QuantConnect market data
    patterns (e.g., spy_prices, aapl_data) without requiring explicit registry entries.
    """

    HIERARCHY_ORDER = [
        "qc_native",
        "qc_object_store",
        "internal_purchased",
        "internal_curated",
        "internal_experimental"
    ]

    # Patterns that indicate standard market data available in QuantConnect
    # These don't need explicit registry entries - QC has comprehensive coverage
    QC_STANDARD_DATA_SUFFIXES = {"_prices", "_data", "_ohlcv", "_price", "_returns"}

    # Special data sources always available in QuantConnect
    QC_NATIVE_SPECIAL = {
        "risk_free_rate",      # Available via RiskFreeInterestRateModel
        "treasury_yields",     # Available via FRED data
        "options_data",        # QC has comprehensive options data
        "futures_data",        # QC has comprehensive futures data
        "forex_data",          # QC has forex data
        "crypto_data",         # QC has crypto data
    }

    # Mapping of semantic data requirement names to QC Native symbols/data types
    # This enables matching "vix_index" to QC's VIX cash index, etc.
    QC_NATIVE_ALIASES = {
        # Cash Indices (125+ available free in QC cloud)
        # See: https://www.quantconnect.com/docs/v2/writing-algorithms/datasets/quantconnect/cash-indices
        "vix": "VIX",
        "vix_index": "VIX",
        "vix_data": "VIX",
        "cboe_vix": "VIX",
        "volatility_index": "VIX",
        "spx": "SPX",
        "spx_index": "SPX",
        "sp500_index": "SPX",
        "sp500": "SPX",
        "s&p500": "SPX",
        "s&p_500": "SPX",
        "dxy": "DXY",
        "dxy_index": "DXY",
        "dollar_index": "DXY",
        "us_dollar_index": "DXY",
        "usdx": "DXY",
        "ndx": "NDX",
        "ndx_index": "NDX",
        "nasdaq_index": "NDX",
        "nasdaq100_index": "NDX",
        "nasdaq_100": "NDX",
        "rut": "RUT",
        "rut_index": "RUT",
        "russell_2000": "RUT",
        "russell2000": "RUT",
        "russell_index": "RUT",
        "djia": "DJI",
        "dji": "DJI",
        "dow_jones": "DJI",
        "dow_index": "DJI",

        # Forex (71+ pairs available free)
        # See: https://www.quantconnect.com/docs/v2/cloud-platform/datasets/quantconnect/forex
        "eurusd": "EURUSD",
        "eur_usd": "EURUSD",
        "eur_usd_prices": "EURUSD",
        "euro_dollar": "EURUSD",
        "gbpusd": "GBPUSD",
        "gbp_usd": "GBPUSD",
        "gbp_usd_prices": "GBPUSD",
        "pound_dollar": "GBPUSD",
        "usdjpy": "USDJPY",
        "usd_jpy": "USDJPY",
        "usd_jpy_prices": "USDJPY",
        "dollar_yen": "USDJPY",
        "audusd": "AUDUSD",
        "aud_usd": "AUDUSD",
        "aussie_dollar": "AUDUSD",
        "usdcad": "USDCAD",
        "usd_cad": "USDCAD",
        "usdchf": "USDCHF",
        "usd_chf": "USDCHF",
        "nzdusd": "NZDUSD",
        "nzd_usd": "NZDUSD",
        "eurgbp": "EURGBP",
        "eur_gbp": "EURGBP",
        "eurjpy": "EURJPY",
        "eur_jpy": "EURJPY",

        # Crypto (available in QC)
        "btcusd": "BTCUSD",
        "btc_usd": "BTCUSD",
        "bitcoin": "BTCUSD",
        "bitcoin_price": "BTCUSD",
        "ethusd": "ETHUSD",
        "eth_usd": "ETHUSD",
        "ethereum": "ETHUSD",
        "ethereum_price": "ETHUSD",

        # Common ETFs/Equities (all US equities free in QC)
        "spy": "SPY",
        "spy_etf": "SPY",
        "sp500_etf": "SPY",
        "qqq": "QQQ",
        "qqq_etf": "QQQ",
        "nasdaq_etf": "QQQ",
        "iwm": "IWM",
        "iwm_etf": "IWM",
        "russell_etf": "IWM",
        "dia": "DIA",
        "dia_etf": "DIA",
        "dow_etf": "DIA",
        "tlt": "TLT",
        "tlt_etf": "TLT",
        "treasury_bond_etf": "TLT",
        "gld": "GLD",
        "gld_etf": "GLD",
        "gold_etf": "GLD",
        "gold_prices": "GLD",
        "slv": "SLV",
        "slv_etf": "SLV",
        "silver_etf": "SLV",
        "eem": "EEM",
        "emerging_markets": "EEM",
        "vxx": "VXX",
        "vxx_etf": "VXX",
        "vix_etf": "VXX",
        "vixy": "VIXY",
        "vixy_etf": "VIXY",
        "uvxy": "UVXY",
        "uvxy_etf": "UVXY",
        "hyg": "HYG",
        "high_yield_bonds": "HYG",
        "lqd": "LQD",
        "investment_grade_bonds": "LQD",
        "xlf": "XLF",
        "financials_etf": "XLF",
        "xlk": "XLK",
        "technology_etf": "XLK",
        "xle": "XLE",
        "energy_etf": "XLE",
        "xlv": "XLV",
        "healthcare_etf": "XLV",
        "xli": "XLI",
        "industrials_etf": "XLI",
        "xlp": "XLP",
        "consumer_staples_etf": "XLP",
        "xly": "XLY",
        "consumer_discretionary_etf": "XLY",
        "xlb": "XLB",
        "materials_etf": "XLB",
        "xlu": "XLU",
        "utilities_etf": "XLU",
        "xlre": "XLRE",
        "real_estate_etf": "XLRE",
        "efa": "EFA",
        "international_developed": "EFA",
        "vgk": "VGK",
        "europe_etf": "VGK",
        "ewj": "EWJ",
        "japan_etf": "EWJ",
        "fxi": "FXI",
        "china_etf": "FXI",

        # Futures (most available in QC - CBOT, CME, COMEX, ICE, NYMEX)
        "es_futures": "ES",
        "sp500_futures": "ES",
        "e_mini_futures": "ES",
        "nq_futures": "NQ",
        "nasdaq_futures": "NQ",
        "cl_futures": "CL",
        "crude_oil_futures": "CL",
        "oil_futures": "CL",
        "gc_futures": "GC",
        "gold_futures": "GC",
        "si_futures": "SI",
        "silver_futures": "SI",
        "zn_futures": "ZN",
        "treasury_futures": "ZN",
        "10yr_futures": "ZN",
        "zb_futures": "ZB",
        "bond_futures": "ZB",
        "30yr_futures": "ZB",
        "zc_futures": "ZC",
        "corn_futures": "ZC",
        "zs_futures": "ZS",
        "soybean_futures": "ZS",
        "zw_futures": "ZW",
        "wheat_futures": "ZW",
        "ng_futures": "NG",
        "natural_gas_futures": "NG",
    }

    # Data types that are implicitly available in QC (no explicit symbol needed)
    QC_NATIVE_DATA_TYPES = {
        "us_equities",
        "equities",
        "stock_prices",
        "equity_prices",
        "stock_data",
        "equity_data",
        "market_data",
        "price_data",
        "ohlcv_data",
        "volume_data",
        "forex",
        "forex_prices",
        "fx_data",
        "currency_data",
        "crypto",
        "cryptocurrency",
        "crypto_prices",
        "futures",
        "futures_prices",
        "commodities",
        "commodity_prices",
        "options",
        "options_data",
        "fundamentals",
        "fundamental_data",
        "corporate_actions",
        "dividends",
        "splits",
    }

    def __init__(self, registry_path: Path):
        """
        Initialize data registry manager.

        Args:
            registry_path: Path to data-registry directory
        """
        self.registry_path = registry_path
        self.registry_file = registry_path / "registry.json"
        self.sources_path = registry_path / "sources"

    def ensure_structure(self):
        """Ensure registry directories exist."""
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.sources_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def is_qc_native_pattern(cls, source_id: str) -> bool:
        """
        Check if a source ID matches a QC Native data pattern.

        QuantConnect provides comprehensive market data coverage including:
        - All US equities and ETFs
        - International equities
        - Cash indices (VIX, SPX, DXY, etc.)
        - Futures, options, forex, crypto

        Args:
            source_id: Data source ID (will be normalized)

        Returns:
            True if likely available as QC Native data
        """
        # Normalize
        source_id = source_id.lower().replace("-", "_").replace(" ", "_")

        # Check known aliases first (vix_index -> VIX, eur_usd -> EURUSD, etc.)
        if source_id in cls.QC_NATIVE_ALIASES:
            return True

        # Check special data sources
        if source_id in cls.QC_NATIVE_SPECIAL:
            return True

        # Check generic data types (us_equities, forex_data, etc.)
        if source_id in cls.QC_NATIVE_DATA_TYPES:
            return True

        # Check for standard market data patterns (spy_prices, aapl_data, etc.)
        for suffix in cls.QC_STANDARD_DATA_SUFFIXES:
            if source_id.endswith(suffix):
                ticker = source_id[:-len(suffix)]
                # Basic validation: ticker should be 1-6 alphanumeric chars
                if ticker and len(ticker) <= 6 and ticker.replace("_", "").isalnum():
                    return True

        return False

    @classmethod
    def resolve_qc_native_symbol(cls, source_id: str) -> Optional[str]:
        """
        Resolve a semantic data requirement to its QC Native symbol.

        Args:
            source_id: Data source ID (will be normalized)

        Returns:
            QC symbol if resolvable, None otherwise
        """
        source_id = source_id.lower().replace("-", "_").replace(" ", "_")

        # Check known aliases
        if source_id in cls.QC_NATIVE_ALIASES:
            return cls.QC_NATIVE_ALIASES[source_id]

        # Check for standard market data patterns
        for suffix in cls.QC_STANDARD_DATA_SUFFIXES:
            if source_id.endswith(suffix):
                ticker = source_id[:-len(suffix)]
                if ticker and len(ticker) <= 6 and ticker.replace("_", "").isalnum():
                    return ticker.upper()

        return None

    @classmethod
    def create_qc_native_source(cls, source_id: str) -> DataSource:
        """
        Create a synthetic DataSource for auto-recognized QC Native data.

        Args:
            source_id: Normalized data source ID

        Returns:
            DataSource representing the QC Native data
        """
        # Resolve to QC symbol
        symbol = cls.resolve_qc_native_symbol(source_id)
        if not symbol:
            symbol = source_id.upper()

        # Determine data type and usage notes based on symbol
        normalized = source_id.lower().replace("-", "_").replace(" ", "_")

        # Check what type of data this is
        if normalized in cls.QC_NATIVE_ALIASES:
            # It's an alias - determine type from symbol characteristics
            if symbol in ("VIX", "SPX", "DXY", "NDX", "RUT", "DJI"):
                data_type = "cash_index"
                usage = f"Cash index - use self.add_data(Index, \"{symbol}\", Resolution.DAILY)"
            elif len(symbol) == 6 and symbol[:3].isalpha() and symbol[3:].isalpha():
                # Forex pair like EURUSD
                data_type = "forex"
                usage = f"Forex - use self.add_forex(\"{symbol}\", Resolution.DAILY)"
            elif symbol.endswith("USD") and len(symbol) <= 7:
                # Crypto like BTCUSD
                data_type = "crypto"
                usage = f"Crypto - use self.add_crypto(\"{symbol}\", Resolution.DAILY)"
            elif len(symbol) <= 2:
                # Futures like ES, NQ, CL
                data_type = "futures"
                usage = f"Futures - use self.add_future(Futures.Indices.{symbol}, Resolution.DAILY)"
            else:
                # Default to equity/ETF
                data_type = "equity"
                usage = f"Equity/ETF - use self.add_equity(\"{symbol}\", Resolution.DAILY)"
        elif normalized in cls.QC_NATIVE_DATA_TYPES:
            data_type = "generic"
            usage = "Generic QC data - available for all supported asset types"
        else:
            data_type = "equity"
            usage = f"Equity - use self.add_equity(\"{symbol}\", Resolution.DAILY)"

        return DataSource(
            id=source_id,
            name=f"{symbol} Data",
            data_type=data_type,
            description=f"QuantConnect native data for {symbol}",
            availability={
                "qc_native": {
                    "available": True,
                    "symbol": symbol,
                    "resolution": ["tick", "second", "minute", "hour", "daily"],
                }
            },
            coverage={
                "start_date": "1998-01-01",  # Conservative estimate
                "end_date": "present",
            },
            columns=["open", "high", "low", "close", "volume"],
            usage_notes=usage,
            is_auto_recognized=True
        )

    def _load_registry(self) -> Dict[str, Any]:
        """Load the registry file."""
        if not self.registry_file.exists():
            return {
                "version": "1.0",
                "last_updated": None,
                "hierarchy_order": self.HIERARCHY_ORDER,
                "data_sources": []
            }

        with open(self.registry_file, 'r') as f:
            return json.load(f)

    def _save_registry(self, registry: Dict[str, Any]):
        """Save the registry file."""
        registry["last_updated"] = datetime.utcnow().isoformat() + "Z"
        with open(self.registry_file, 'w') as f:
            json.dump(registry, f, indent=2)

    def list(self, available_only: bool = False) -> List[DataSource]:
        """
        List all data sources.

        Args:
            available_only: If True, only return sources with at least one available tier

        Returns:
            List of DataSource objects
        """
        registry = self._load_registry()
        sources = []

        for source_data in registry.get("data_sources", []):
            source = self._create_source_from_data(source_data)

            if available_only and not source.is_available():
                continue

            sources.append(source)

        return sources

    def get(self, source_id: str) -> Optional[DataSource]:
        """
        Get a specific data source by ID.

        Resolution order:
        1. Explicit registry entry by ID
        2. Explicit registry entry by alias
        3. QC Native pattern recognition (aliases, data types, suffixes)

        Args:
            source_id: Data source ID (will be normalized for matching)

        Returns:
            DataSource if found or recognized, None otherwise
        """
        # Normalize for comparison
        normalized_id = source_id.lower().replace("-", "_").replace(" ", "_")

        # First check explicit registry
        registry = self._load_registry()

        for source_data in registry.get("data_sources", []):
            # Check direct ID match
            if source_data["id"] == source_id or source_data["id"] == normalized_id:
                return self._create_source_from_data(source_data)

            # Check aliases
            aliases = source_data.get("aliases", [])
            for alias in aliases:
                alias_normalized = alias.lower().replace("-", "_").replace(" ", "_")
                if alias_normalized == normalized_id:
                    return self._create_source_from_data(source_data)

        # Fall back to QC Native pattern recognition
        if self.is_qc_native_pattern(normalized_id):
            return self.create_qc_native_source(normalized_id)

        return None

    def _create_source_from_data(self, source_data: Dict[str, Any]) -> DataSource:
        """Create a DataSource object from registry data."""
        return DataSource(
            id=source_data["id"],
            name=source_data.get("name", source_data["id"]),
            data_type=source_data.get("type", "unknown"),
            description=source_data.get("description"),
            availability=source_data.get("availability", {}),
            coverage=source_data.get("coverage"),
            columns=source_data.get("columns"),
            usage_notes=source_data.get("usage_notes"),
            aliases=source_data.get("aliases"),
            is_auto_recognized=False
        )

    def check_availability(self, source_ids: List[str]) -> Dict[str, DataAvailability]:
        """
        Check availability for multiple data sources.

        Args:
            source_ids: List of data source IDs to check

        Returns:
            Dict mapping source_id to DataAvailability
        """
        results = {}

        for source_id in source_ids:
            source = self.get(source_id)
            if source:
                results[source_id] = source.best_source()
            else:
                results[source_id] = DataAvailability(
                    available=False,
                    notes=f"Source not found in registry: {source_id}"
                )

        return results

    def add(
        self,
        source_id: str,
        name: str,
        data_type: str,
        description: Optional[str] = None,
        availability: Optional[Dict[str, Any]] = None,
        coverage: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        usage_notes: Optional[str] = None
    ) -> DataSource:
        """
        Add a new data source to the registry.

        Args:
            source_id: Unique identifier for the data source
            name: Human-readable name
            data_type: Type of data (e.g., 'price', 'breadth', 'fundamental')
            description: Description of the data source
            availability: Availability info by tier
            coverage: Coverage information (start_date, end_date, frequency)
            columns: List of column names
            usage_notes: Notes on using this data

        Returns:
            Created DataSource
        """
        registry = self._load_registry()

        # Check for existing
        for existing in registry.get("data_sources", []):
            if existing["id"] == source_id:
                raise ValueError(f"Data source already exists: {source_id}")

        source_data = {
            "id": source_id,
            "name": name,
            "type": data_type,
        }

        if description:
            source_data["description"] = description
        if availability:
            source_data["availability"] = availability
        if coverage:
            source_data["coverage"] = coverage
        if columns:
            source_data["columns"] = columns
        if usage_notes:
            source_data["usage_notes"] = usage_notes

        registry.setdefault("data_sources", []).append(source_data)
        self._save_registry(registry)

        return DataSource(
            id=source_id,
            name=name,
            data_type=data_type,
            description=description,
            availability=availability or {},
            coverage=coverage,
            columns=columns,
            usage_notes=usage_notes
        )

    def update_availability(
        self,
        source_id: str,
        tier: str,
        available: bool,
        path: Optional[str] = None,
        key: Optional[str] = None,
        notes: Optional[str] = None
    ):
        """
        Update availability for a specific tier.

        Args:
            source_id: Data source ID
            tier: Tier to update (qc_native, qc_object_store, etc.)
            available: Whether data is available
            path: Path to data (for internal tiers)
            key: Object store key (for qc_object_store)
            notes: Additional notes
        """
        if tier not in self.HIERARCHY_ORDER:
            raise ValueError(f"Invalid tier: {tier}. Valid: {self.HIERARCHY_ORDER}")

        registry = self._load_registry()

        for source in registry.get("data_sources", []):
            if source["id"] == source_id:
                if "availability" not in source:
                    source["availability"] = {}

                tier_data = {"available": available}
                if path:
                    tier_data["path"] = path
                if key:
                    tier_data["key"] = key
                if notes:
                    tier_data["notes"] = notes

                source["availability"][tier] = tier_data
                self._save_registry(registry)
                return

        raise ValueError(f"Data source not found: {source_id}")

    def search(self, query: str) -> List[DataSource]:
        """Search data sources by name or ID."""
        query_lower = query.lower()
        results = []

        for source in self.list():
            if query_lower in source.id.lower() or query_lower in source.name.lower():
                results.append(source)

        return results
