# region imports
from AlgorithmImports import *
from datetime import timedelta
# endregion


class DemoTrend(QCAlgorithm):
    """
    Demo Trend Following

    Demo strategy showing trend following template

    Strategy ID: DEMO-TREND
    Strategy Type: trend_following
    Schema Version: 2.0
    """

    def Initialize(self):
        """Initialize the algorithm.

        NOTE: Start/end dates are set by the framework, NOT in this code.
        This ensures proper walk-forward validation without date injection bugs.
        """
        # Capital - can be overridden by framework
        self.SetCash(100000)

        # Warmup period based on signal lookback
        self.SetWarmUp(timedelta(days=200))

        # Universe setup
        self._symbols = []
        self._symbols.append(self.AddEquity("SPY", Resolution.Daily).Symbol)
        self._symbols.append(self.AddEquity("QQQ", Resolution.Daily).Symbol)
        self._symbols.append(self.AddEquity("IWM", Resolution.Daily).Symbol)

        # Defensive symbols for risk-off
        self._defensive_symbols = []
        self._defensive_symbols.append(self.AddEquity("TLT", Resolution.Daily).Symbol)

        # Signal parameters
        self._lookback_days = 200
        self._threshold = 0.0  # No buffer

        # Position sizing parameters
        self._leverage = 1.0

        # Schedule rebalancing
        self.Schedule.On(
            self.DateRules.Every(DayOfWeek.Monday),
            self.TimeRules.AfterMarketOpen("SPY", 30),
            self.Rebalance
        )

        # Strategy-specific initialization


    def Rebalance(self):
        """Execute the rebalancing logic."""
        if self.IsWarmingUp:
            return

        # Get target weights from signal
        target_weights = self.CalculateTargetWeights()

        # Execute trades
        self.ExecuteTargetWeights(target_weights)

    def CalculateTargetWeights(self) -> dict:
        """Calculate target portfolio weights based on signal.

        Returns:
            Dictionary mapping Symbol to target weight (0.0 to 1.0)
        """
        target_weights = {}
        trending_symbols = []

        for symbol in self._symbols:
            if not self.Securities[symbol].HasData:
                continue

            # Check if price is above moving average
            if self.IsTrending(symbol):
                trending_symbols.append(symbol)

        if not trending_symbols:
            return self.GetDefensiveWeights()

        # Weight allocation
        weight = 1.0 / len(trending_symbols)
        return {symbol: weight for symbol in trending_symbols}

    def ExecuteTargetWeights(self, target_weights: dict):
        """Execute trades to achieve target weights.

        Args:
            target_weights: Dictionary mapping Symbol to target weight
        """
        # Liquidate positions not in target
        for holding in self.Portfolio.Values:
            if holding.Invested and holding.Symbol not in target_weights:
                self.Liquidate(holding.Symbol)

        # Set target weights with leverage
        for symbol, weight in target_weights.items():
            adjusted_weight = weight * self._leverage
            self.SetHoldings(symbol, adjusted_weight)

    def GetHistoricalReturns(self, symbol: Symbol, lookback: int) -> float:
        """Calculate total return over lookback period.

        Args:
            symbol: The symbol to calculate returns for
            lookback: Number of days to look back

        Returns:
            Total return as decimal (e.g., 0.05 for 5%)
        """
        history = self.History(symbol, lookback, Resolution.Daily)
        if history.empty or len(history) < 2:
            return 0.0

        close_prices = history['close']
        return (close_prices.iloc[-1] / close_prices.iloc[0]) - 1.0

    def GetVolatility(self, symbol: Symbol, lookback: int) -> float:
        """Calculate annualized volatility over lookback period.

        Args:
            symbol: The symbol to calculate volatility for
            lookback: Number of days to look back

        Returns:
            Annualized volatility as decimal
        """
        history = self.History(symbol, lookback, Resolution.Daily)
        if history.empty or len(history) < 2:
            return float('inf')

        returns = history['close'].pct_change().dropna()
        return returns.std() * (252 ** 0.5)

    def IsTrending(self, symbol: Symbol) -> bool:
        """Check if symbol is in uptrend (price > SMA).

        Args:
            symbol: The symbol to check

        Returns:
            True if in uptrend, False otherwise
        """
        history = self.History(symbol, self._lookback_days, Resolution.Daily)
        if history.empty or len(history) < self._lookback_days // 2:
            return False

        sma = history['close'].mean()
        current_price = self.Securities[symbol].Price

        # Price must be above SMA by threshold percentage
        threshold_price = sma * (1 + self._threshold)
        return current_price > threshold_price

    def GetMovingAverage(self, symbol: Symbol) -> float:
        """Get simple moving average.

        Args:
            symbol: The symbol to calculate SMA for

        Returns:
            SMA value or None if insufficient data
        """
        history = self.History(symbol, self._lookback_days, Resolution.Daily)
        if history.empty:
            return None
        return history['close'].mean()

    def GetDefensiveWeights(self) -> dict:
        """Get weights for defensive allocation when no trends."""
        if not self._defensive_symbols:
            return {}
        weight = 1.0 / len(self._defensive_symbols)
        return {symbol: weight for symbol in self._defensive_symbols}

