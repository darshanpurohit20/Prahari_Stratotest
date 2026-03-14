# engine/strategies/ma_crossover.py
import pandas as pd
from engine.strategies.base import BaseStrategy

class MACrossoverStrategy(BaseStrategy):
    """
    Strategy 1 — MA / EMA Crossover
    Buy when fast MA crosses above slow MA
    """
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast_p = self.entry.get("fast_period", 50)
        slow_p = self.entry.get("slow_period", 200)
        ind    = self.entry.get("indicator", "EMA")

        if ind == "SMA":
            fast = self._sma(df["Close"], fast_p)
            slow = self._sma(df["Close"], slow_p)
        else:
            fast = self._ema(df["Close"], fast_p)
            slow = self._ema(df["Close"], slow_p)

        # Crossover: today fast > slow, yesterday fast <= slow
        return (fast > slow) & (fast.shift(1) <= slow.shift(1))

    def get_indicators(self, df: pd.DataFrame) -> dict:
        fast_p = self.entry.get("fast_period", 50)
        slow_p = self.entry.get("slow_period", 200)
        ind    = self.entry.get("indicator", "EMA")

        if ind == "SMA":
            fast = self._sma(df["Close"], fast_p)
            slow = self._sma(df["Close"], slow_p)
        else:
            fast = self._ema(df["Close"], fast_p)
            slow = self._ema(df["Close"], slow_p)

        return {
            f"{ind}_{fast_p}": fast,
            f"{ind}_{slow_p}": slow
        }
