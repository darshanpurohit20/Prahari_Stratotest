# engine/strategies/base.py
# Base class all strategies inherit from
# Add new strategies easily by inheriting this

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from engine.friction import calculate_trade_friction, get_pip_size


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.
    Every strategy must implement:
      - generate_signals(df) → pd.Series of entry signals
      - get_indicators(df)   → dict of indicator series for chart
      - get_zones(df)        → dict of zones for chart (OB, FVG etc)
    """

    def __init__(self, rules: dict, market: str = "india_equity"):
        self.rules   = rules
        self.market  = market
        self.entry   = rules.get("entry", {})
        self.sl_cfg  = rules.get("stop_loss", {})
        self.tp_cfg  = rules.get("take_profit", {})
        self.filters = rules.get("filters", {})
        self.rr      = self.tp_cfg.get("ratio", 2.0)  # default 1:2

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Returns boolean Series — True where entry signal fires"""
        pass

    @abstractmethod
    def get_indicators(self, df: pd.DataFrame) -> dict:
        """Returns dict of indicator Series for chart rendering"""
        pass

    def get_zones(self, df: pd.DataFrame) -> dict:
        """Returns dict of zones (OB, FVG etc) — override in SMC strategies"""
        return {}

    def calculate_sl(self, df: pd.DataFrame, entry_idx: int,
                     entry_price: float) -> float:
        """
        Calculate stop loss price based on rules
        Supports: swing_low, swing_high, percent, pips, atr, below_ob, below_fvg
        """
        sl_type   = self.sl_cfg.get("type", "swing_low")
        lookback  = self.sl_cfg.get("lookback", 5)
        sl_value  = self.sl_cfg.get("value")
        atr_mult  = self.sl_cfg.get("atr_multiplier", 1.5)
        pip_size  = get_pip_size(self.market)

        if sl_type == "swing_low":
            start = max(0, entry_idx - lookback)
            sl    = df["Low"].iloc[start:entry_idx].min()
            return round(sl * 0.999, 4)  # tiny buffer below

        elif sl_type == "swing_high":
            start = max(0, entry_idx - lookback)
            sl    = df["High"].iloc[start:entry_idx].max()
            return round(sl * 1.001, 4)

        elif sl_type == "percent" and sl_value:
            return round(entry_price * (1 - sl_value / 100), 4)

        elif sl_type == "pips" and sl_value:
            return round(entry_price - (sl_value * pip_size), 4)

        elif sl_type == "atr":
            atr = self._calculate_atr(df, entry_idx)
            return round(entry_price - (atr * atr_mult), 4)

        elif sl_type in ("below_ob", "below_fvg"):
            # Handled in individual strategy — fallback to swing low
            start = max(0, entry_idx - lookback)
            sl    = df["Low"].iloc[start:entry_idx].min()
            return round(sl * 0.999, 4)

        else:
            # Default — 2% SL
            return round(entry_price * 0.98, 4)

    def calculate_tp(self, entry_price: float, sl_price: float) -> float:
        """
        Calculate take profit based on RR ratio
        TP = entry + (SL distance × RR ratio)
        e.g. 1:2 RR → TP = entry + (2 × SL distance)
        """
        sl_distance = entry_price - sl_price
        tp          = entry_price + (sl_distance * self.rr)
        return round(tp, 4)

    def run(self, df: pd.DataFrame, initial_capital: float) -> dict:
        """
        Optimized execution — using NumPy values for speed.
        Returns all trades + equity curve.
        """
        # Convert to numpy for 100x faster iteration
        close_vals = df["Close"].values
        high_vals  = df["High"].values
        low_vals   = df["Low"].values
        time_vals  = df.index.values
        
        signals    = self.generate_signals(df)
        sig_vals   = signals.values
        self._last_signals = signals  # for vbt
        
        trades     = []
        equity     = [initial_capital]
        capital    = initial_capital
        active     = None
        trade_num  = 0

        # Pre-calculate indicator buffer (optional, but good for safety)
        warmup = 50

        for i in range(len(df)):
            low_i   = low_vals[i]
            high_i  = high_vals[i]
            close_i = close_vals[i]

            # ── Manage open trade ──
            if active:
                hit_sl = low_i  <= active["sl"]
                hit_tp = high_i >= active["tp"]

                if hit_sl or hit_tp:
                    exit_price = active["sl"] if hit_sl else active["tp"]
                    result     = "loss" if hit_sl else "win"

                    raw_pnl    = exit_price - active["entry_price"]
                    friction   = calculate_trade_friction(
                        active["entry_price"], exit_price, self.market
                    )
                    net_pnl    = raw_pnl - friction
                    pnl_pct    = (net_pnl / active["entry_price"]) * 100
                    sl_dist    = active["entry_price"] - active["sl"]
                    rr_ach     = raw_pnl / sl_dist if sl_dist > 0 else 0

                    capital   += net_pnl
                    trade_num += 1

                    trades.append({
                        "trade_number":  trade_num,
                        "entry_time":    str(active["entry_time"]),
                        "exit_time":     str(time_vals[i]),
                        "entry_price":   round(active["entry_price"], 4),
                        "exit_price":    round(exit_price, 4),
                        "sl_price":      round(active["sl"], 4),
                        "tp_price":      round(active["tp"], 4),
                        "result":        result,
                        "pnl":           round(net_pnl, 2),
                        "pnl_pct":       round(pnl_pct, 4),
                        "rr_achieved":   round(rr_ach, 3),
                        "friction_cost": round(friction, 4)
                    })
                    active = None

            equity.append(capital)

            # ── Look for new entry (only if flat) ──
            if active is None and i >= warmup:
                if sig_vals[i]:
                    entry_price = close_i
                    sl_price    = self.calculate_sl(df, i, entry_price)
                    tp_price    = self.calculate_tp(entry_price, sl_price)

                    if sl_price >= entry_price:
                        continue

                    active = {
                        "entry_price": entry_price,
                        "entry_time":  time_vals[i],
                        "sl":          sl_price,
                        "tp":          tp_price
                    }

        if not trades:
            return {
                "trades": [],
                "equity": [initial_capital] * len(df),
                "indicators": self.get_indicators(df),
                "zones": self.get_zones(df),
                "warning": "Zero valid trades were executed by this strategy on this timeframe."
            }

        return {
            "trades":     trades,
            "equity":     equity,
            "indicators": self.get_indicators(df),
            "zones":      self.get_zones(df)
        }

    # ── Shared indicator helpers ───────────────────────────────

    def _ema(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def _sma(self, series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period).mean()

    def _rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        delta  = series.diff()
        gain   = delta.clip(lower=0).rolling(period).mean()
        loss   = (-delta.clip(upper=0)).rolling(period).mean()
        rs     = gain / loss
        return 100 - (100 / (1 + rs))

    def _atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = df["High"], df["Low"], df["Close"]
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low  - close.shift()).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def _calculate_atr(self, df: pd.DataFrame, idx: int,
                       period: int = 14) -> float:
        atr_series = self._atr(df, period)
        return float(atr_series.iloc[idx]) if not np.isnan(atr_series.iloc[idx]) else 0

    def _find_swing_lows(self, df: pd.DataFrame,
                         lookback: int = 5) -> pd.Series:
        """Returns Series of swing low prices, NaN elsewhere"""
        lows   = df["Low"]
        result = pd.Series(np.nan, index=df.index)
        for i in range(lookback, len(df) - lookback):
            window = lows.iloc[i - lookback: i + lookback + 1]
            if lows.iloc[i] == window.min():
                result.iloc[i] = lows.iloc[i]
        return result

    def _find_swing_highs(self, df: pd.DataFrame,
                          lookback: int = 5) -> pd.Series:
        """Returns Series of swing high prices, NaN elsewhere"""
        highs  = df["High"]
        result = pd.Series(np.nan, index=df.index)
        for i in range(lookback, len(df) - lookback):
            window = highs.iloc[i - lookback: i + lookback + 1]
            if highs.iloc[i] == window.max():
                result.iloc[i] = highs.iloc[i]
        return result

    def _fvg(self, df: pd.DataFrame, direction: str = "bullish") -> pd.Series:
        """
        Calculates Fair Value Gaps.
        Bullish FVG: Low of candle 3 > High of candle 1
        Bearish FVG: High of candle 3 < Low of candle 1
        Returns the top of the bullish FVG or bottom of the bearish FVG
        """
        high, low = df["High"], df["Low"]
        
        if direction == "bullish":
            # Condition: C1 High < C3 Low. FVG Top = C3 Low
            is_fvg = (low > high.shift(2)) & (df["Close"].shift(1) > df["Open"].shift(1))
            return pd.Series(np.where(is_fvg, low, np.nan), index=df.index)
        else:
            # Condition: C1 Low > C3 High. FVG Bottom = C3 High
            is_fvg = (high < low.shift(2)) & (df["Close"].shift(1) < df["Open"].shift(1))
            return pd.Series(np.where(is_fvg, high, np.nan), index=df.index)

    def _ob(self, df: pd.DataFrame, direction: str = "bullish") -> pd.Series:
        """
        Calculates Order Blocks.
        Bullish OB: Last down candle before an up impulse breaking structure.
        Bearish OB: Last up candle before a down impulse breaking structure.
        Returns the High (Bull) or Low (Bear) of the OB candle itself.
        """
        open_p, close = df["Open"], df["Close"]
        high, low = df["High"], df["Low"]
        
        if direction == "bullish":
            # Very simplified OB: Down candle followed by strong Up candle.
            is_down = close < open_p
            is_up = close > open_p
            strong_body = (close - open_p) > (open_p.shift(1) - close.shift(1)) * 1.5
            is_bull_ob = is_up & is_down.shift(1) & strong_body
            return pd.Series(np.where(is_bull_ob, high.shift(1), np.nan), index=df.index).ffill()
        else:
            is_down = close < open_p
            is_up = close > open_p
            strong_body = (open_p - close) > (close.shift(1) - open_p.shift(1)) * 1.5
            is_bear_ob = is_down & is_up.shift(1) & strong_body
            return pd.Series(np.where(is_bear_ob, low.shift(1), np.nan), index=df.index).ffill()

    def _adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculates Average Directional Index (ADX)"""
        high, low, close = df["High"], df["Low"], df["Close"]
        
        tr = self._atr(df, 1).rolling(period).mean() # Approximate
        up_move = high.diff()
        down_move = low.diff().abs()
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        plus_di = 100 * (pd.Series(plus_dm).rolling(period).mean() / tr)
        minus_di = 100 * (pd.Series(minus_dm).rolling(period).mean() / tr)
        
        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
        return dx.rolling(period).mean()

    def get_market_regime(self, df: pd.DataFrame) -> str:
        """Classifies market as Trending or Ranging based on ADX"""
        adx = self._adx(df).iloc[-1]
        if adx > 25:
            return "Trending (Strong Momentum)"
        elif adx > 20:
            return "Trending (Weakening/Developing)"
        else:
            return "Ranging (Sideways/Choppy)"
