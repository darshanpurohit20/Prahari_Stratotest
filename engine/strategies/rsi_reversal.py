# engine/strategies/rsi_reversal.py
import pandas as pd
from engine.strategies.base import BaseStrategy

class RSIReversalStrategy(BaseStrategy):
    """
    Strategy 2 — RSI Reversal
    Buy when RSI drops below oversold level
    """
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        period    = self.entry.get("period", 14)
        threshold = self.entry.get("value", 30)
        rsi       = self._rsi(df["Close"], period)
        # Buy when RSI crosses back above oversold from below
        return (rsi > threshold) & (rsi.shift(1) <= threshold)

    def get_indicators(self, df: pd.DataFrame) -> dict:
        period = self.entry.get("period", 14)
        return {"RSI": self._rsi(df["Close"], period)}
