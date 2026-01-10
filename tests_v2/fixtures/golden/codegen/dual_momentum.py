# region imports
from AlgorithmImports import *
from datetime import timedelta
# endregion


class DemoDualmom(QCAlgorithm):
    """
    Demo Dual Momentum

    Demo strategy showing dual momentum template

    Strategy ID: DEMO-DUALMOM
    Strategy Type: dual_momentum
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
        self.SetWarmUp(timedelta(days=252))

        # Universe setup
        self._symbols = []
        self._symbols.append(self.AddEquity("SPY", Resolution.Daily).Symbol)
        self._symbols.append(self.AddEquity("EFA", Resolution.Daily).Symbol)
        self._symbols.append(self.AddEquity("EEM", Resolution.Daily).Symbol)

        # Defensive symbols for risk-off
        self._defensive_symbols = []
        self._defensive_symbols.append(self.AddEquity("AGG", Resolution.Daily).Symbol)

        # Signal parameters
        self._lookback_days = 252
        self._selection_n = 1
        self._abs_momentum_threshold = 0.0

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
        # Step 1: Calculate relative momentum for all symbols
        momentum_scores = {}
        for symbol in self._symbols:
            if not self.Securities[symbol].HasData:
                continue
            momentum = self.GetHistoricalReturns(symbol, self._lookback_days)
            momentum_scores[symbol] = momentum

        if not momentum_scores:
            return self.GetDefensiveWeights()

        # Step 2: Rank by relative momentum
        ranked = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        top_n = ranked[:self._selection_n]

        # Step 3: Apply absolute momentum filter
        # Only invest if the selected asset has positive absolute momentum
        selected = []
        for symbol, momentum in top_n:
            if momentum > self._abs_momentum_threshold:
                selected.append(symbol)

        if not selected:
            return self.GetDefensiveWeights()

        # Step 4: Weight allocation
        weight = 1.0 / len(selected)
        return {symbol: weight for symbol in selected}

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
        """Get weights for defensive allocation.

        Used when no assets pass the dual momentum filter.
        """
        if not self._defensive_symbols:
            return {}

        # Check if defensive assets have positive momentum too
        valid_defensive = []
        for symbol in self._defensive_symbols:
            if not self.Securities[symbol].HasData:
                continue
            momentum = self.GetHistoricalReturns(symbol, self._lookback_days)
            if momentum > 0:
                valid_defensive.append(symbol)

        # If no defensive assets have positive momentum, use all of them
        if not valid_defensive:
            valid_defensive = [s for s in self._defensive_symbols
                              if self.Securities[s].HasData]

        if not valid_defensive:
            return {}

        weight = 1.0 / len(valid_defensive)
        return {symbol: weight for symbol in valid_defensive}

