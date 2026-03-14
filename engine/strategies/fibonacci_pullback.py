# engine/strategies/fibonacci_pullback.py
import pandas as pd
import numpy as np
from engine.strategies.base import BaseStrategy

class FibonacciPullbackStrategy(BaseStrategy):
    """
    Strategy 3 — Fibonacci Pullback
    Buy when price pulls back to key Fib level in uptrend
    """
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fib_level  = self.entry.get("fib_level", 0.618)
        ema200     = self._ema(df["Close"], 200)
        signals    = pd.Series(False, index=df.index)
        swing_size = 10

        swing_highs, swing_lows = [], []

        for i in range(swing_size, len(df) - swing_size):
            # Detect swing high
            if df["High"].iloc[i] == df["High"].iloc[i-swing_size:i+swing_size+1].max():
                swing_highs.append((i, df["High"].iloc[i]))
            # Detect swing low
            if df["Low"].iloc[i] == df["Low"].iloc[i-swing_size:i+swing_size+1].min():
                swing_lows.append((i, df["Low"].iloc[i]))

        for i in range(200, len(df)):
            # Only in uptrend
            if df["Close"].iloc[i] < ema200.iloc[i]:
                continue

            recent_lows  = [s for s in swing_lows  if s[0] < i]
            recent_highs = [s for s in swing_highs if s[0] < i]

            if len(recent_lows) < 1 or len(recent_highs) < 1:
                continue

            sl_idx, sl_price = recent_lows[-1]
            sh_idx, sh_price = recent_highs[-1]

            # Uptrend: low must come before high
            if sl_idx >= sh_idx:
                continue

            diff      = sh_price - sl_price
            fib_price = sh_price - (diff * fib_level)
            tolerance = diff * 0.02

            # Price tapping fib level and closing above it
            candle = df.iloc[i]
            at_fib = (candle["Low"] <= fib_price + tolerance and
                      candle["High"] >= fib_price - tolerance)
            confirmed = candle["Close"] > fib_price

            if at_fib and confirmed:
                signals.iloc[i] = True

        return signals

    def get_indicators(self, df: pd.DataFrame) -> dict:
        return {"EMA_200": self._ema(df["Close"], 200)}

    def get_zones(self, df: pd.DataFrame) -> dict:
        """Returns fibonacci level lines for chart"""
        fib_level  = self.entry.get("fib_level", 0.618)
        swing_size = 10
        swing_highs, swing_lows = [], []

        for i in range(swing_size, len(df) - swing_size):
            if df["High"].iloc[i] == df["High"].iloc[i-swing_size:i+swing_size+1].max():
                swing_highs.append((i, df["High"].iloc[i]))
            if df["Low"].iloc[i] == df["Low"].iloc[i-swing_size:i+swing_size+1].min():
                swing_lows.append((i, df["Low"].iloc[i]))

        if not swing_highs or not swing_lows:
            return {}

        sl_price = swing_lows[-1][1]
        sh_price = swing_highs[-1][1]
        diff     = sh_price - sl_price

        return {
            "fibonacci": {
                "swing_low":  sl_price,
                "swing_high": sh_price,
                "levels": {
                    "0.236": round(sh_price - diff * 0.236, 4),
                    "0.382": round(sh_price - diff * 0.382, 4),
                    "0.500": round(sh_price - diff * 0.500, 4),
                    "0.618": round(sh_price - diff * 0.618, 4),
                    "0.786": round(sh_price - diff * 0.786, 4),
                }
            }
        }
