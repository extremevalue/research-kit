# region imports
from AlgorithmImports import *
from datetime import timedelta
# endregion


class DemoMeanrev(QCAlgorithm):
    """
    Demo Mean Reversion

    Demo strategy showing mean reversion template

    Strategy ID: DEMO-MEANREV
    Strategy Type: mean_reversion
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
        self._threshold = -2.0

        # Position sizing parameters
        self._leverage = 1.0

        # Schedule rebalancing
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen("SPY", 30),
            self.Rebalance
        )

        # Strategy-specific initialization
        # Mean reversion specific tracking
        self._positions = {}  # Track current mean reversion positions


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

            # Calculate Z-score
            zscore = self.CalculateZScore(symbol)

            if zscore is None:
                continue

            # Entry: Z-score below negative threshold (oversold)
            if zscore < self._threshold:
                target_weights[symbol] = 1.0 / len(self._symbols)

            # Exit: Z-score above zero (returned to mean)
            elif zscore > 0 and symbol in self._positions:
                # Will be liquidated by ExecuteTargetWeights
                pass

            # Hold existing positions that haven't mean-reverted
            elif symbol in self._positions and self._positions[symbol]:
                target_weights[symbol] = self._positions[symbol]

        # Track positions for next iteration
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

    def CalculateZScore(self, symbol: Symbol) -> float:
        """Calculate Z-score of current price vs historical mean.

        Args:
            symbol: The symbol to calculate Z-score for

        Returns:
            Z-score value, or None if insufficient data
        """
        history = self.History(symbol, self._lookback_days, Resolution.Daily)
        if history.empty or len(history) < self._lookback_days // 2:
            return None

        close_prices = history['close']
        mean = close_prices.mean()
        std = close_prices.std()

        if std == 0:
            return None

        current_price = self.Securities[symbol].Price
        return (current_price - mean) / std

