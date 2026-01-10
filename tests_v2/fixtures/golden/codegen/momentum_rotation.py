# region imports
from AlgorithmImports import *
from datetime import timedelta
# endregion


class DemoMomentum(QCAlgorithm):
    """
    Demo Momentum Rotation

    Demo strategy showing momentum rotation template

    Strategy ID: DEMO-MOMENTUM
    Strategy Type: momentum_rotation
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
        self.SetWarmUp(timedelta(days=126))

        # Universe setup
        self._symbols = []
        self._symbols.append(self.AddEquity("SPY", Resolution.Daily).Symbol)
        self._symbols.append(self.AddEquity("TLT", Resolution.Daily).Symbol)
        self._symbols.append(self.AddEquity("GLD", Resolution.Daily).Symbol)
        self._symbols.append(self.AddEquity("VNQ", Resolution.Daily).Symbol)

        # Defensive symbols for risk-off
        self._defensive_symbols = []
        self._defensive_symbols.append(self.AddEquity("SHY", Resolution.Daily).Symbol)
        self._defensive_symbols.append(self.AddEquity("BIL", Resolution.Daily).Symbol)

        # Signal parameters
        self._lookback_days = 126
        self._selection_n = 2

        # Position sizing parameters
        self._leverage = 1.0

        # Schedule rebalancing
        self.Schedule.On(
            self.DateRules.MonthStart(),
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
        # Calculate momentum for each symbol
        momentum_scores = {}
        for symbol in self._symbols:
            if not self.Securities[symbol].HasData:
                continue
            momentum = self.GetHistoricalReturns(symbol, self._lookback_days)
            momentum_scores[symbol] = momentum

        if not momentum_scores:
            # No valid momentum scores - go to defensive
            return self.GetDefensiveWeights()

        # Rank by momentum (highest first)
        ranked = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)

        # Select top N
        selected = ranked[:self._selection_n]


        # Equal weight among selected
        weight = 1.0 / len(selected)
        return {symbol: weight for symbol, _ in selected}

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

    def GetDefensiveWeights(self) -> dict:
        """Get weights for defensive allocation."""
        if not self._defensive_symbols:
            return {}
        weight = 1.0 / len(self._defensive_symbols)
        return {symbol: weight for symbol in self._defensive_symbols}


