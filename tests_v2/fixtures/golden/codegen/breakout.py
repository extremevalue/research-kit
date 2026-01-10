# region imports
from AlgorithmImports import *
from datetime import timedelta
# endregion


class DemoBreakout(QCAlgorithm):
    """
    Demo Breakout

    Demo strategy showing breakout template

    Strategy ID: DEMO-BREAKOUT
    Strategy Type: breakout
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
        self.SetWarmUp(timedelta(days=20))

        # Universe setup
        self._symbols = []
        self._symbols.append(self.AddEquity("SPY", Resolution.Daily).Symbol)

        # Signal parameters
        self._lookback_days = 20
        self._selection_n = 1
        self._threshold = 0.05

        # Position sizing parameters
        self._leverage = 1.0

        # Schedule rebalancing
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen("SPY", 30),
            self.Rebalance
        )

        # Strategy-specific initialization
        # Track entry prices for trailing stop
        self._entry_prices = {}
        self._highest_since_entry = {}
        self._positions = {}


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

        for symbol in self._symbols:
            if not self.Securities[symbol].HasData:
                continue

            current_price = self.Securities[symbol].Price

            # Check for breakout entry
            if symbol not in self._entry_prices:
                if self.IsBreakout(symbol):
                    target_weights[symbol] = 1.0 / len(self._symbols)
                    self._entry_prices[symbol] = current_price
                    self._highest_since_entry[symbol] = current_price
            else:
                # Already in position - check for exit
                self._highest_since_entry[symbol] = max(
                    self._highest_since_entry[symbol],
                    current_price
                )

                # Trailing stop check
                trailing_stop = self._highest_since_entry[symbol] * (1 - abs(self._threshold))

                if current_price > trailing_stop:
                    # Continue holding
                    target_weights[symbol] = self._positions.get(symbol, 1.0 / len(self._symbols))
                else:
                    # Exit - trailing stop hit
                    del self._entry_prices[symbol]
                    del self._highest_since_entry[symbol]

        # Track current positions
        self._positions = dict(target_weights)

        return target_weights

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

    def IsBreakout(self, symbol: Symbol) -> bool:
        """Check if current price breaks above recent high.

        Args:
            symbol: The symbol to check

        Returns:
            True if breakout detected
        """
        history = self.History(symbol, self._lookback_days, Resolution.Daily)
        if history.empty or len(history) < self._lookback_days // 2:
            return False

        # Recent high (excluding today)
        recent_high = history['high'][:-1].max() if len(history) > 1 else history['high'].max()

        current_price = self.Securities[symbol].Price

        # Breakout if current price exceeds recent high
        return current_price > recent_high

    def GetRecentHigh(self, symbol: Symbol) -> float:
        """Get the recent high price.

        Args:
            symbol: The symbol to get high for

        Returns:
            Recent high price or None
        """
        history = self.History(symbol, self._lookback_days, Resolution.Daily)
        if history.empty:
            return None
        return history['high'].max()
