# engine/strategies/sr_bounce.py
import pandas as pd
from engine.strategies.base import BaseStrategy

class SRBounceStrategy(BaseStrategy):
    """Strategy 4 — Support/Resistance Bounce"""
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        signals  = pd.Series(False, index=df.index)
        lookback = 20
        tolerance_pct = 0.005  # 0.5% zone around level

        for i in range(lookback * 2, len(df)):
            # Find support: lowest low in lookback window before current
            support = df["Low"].iloc[i - lookback:i].min()
            candle  = df.iloc[i]
            zone    = support * tolerance_pct

            # Price touching support and closing above it
            touching = candle["Low"] <= support + zone
            bounce   = candle["Close"] > support
            if touching and bounce:
                signals.iloc[i] = True

        return signals

    def get_indicators(self, df: pd.DataFrame) -> dict:
        return {}


# engine/strategies/breakout_retest.py
class BreakoutRetestStrategy(BaseStrategy):
    """Strategy 5 — Breakout + Retest"""
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        signals  = pd.Series(False, index=df.index)
        lookback = 20

        for i in range(lookback + 5, len(df)):
            resistance = df["High"].iloc[i - lookback:i - 5].max()
            candle     = df.iloc[i]
            prev_5_high = df["High"].iloc[i - 5:i].max()
            tolerance  = resistance * 0.003

            # Price broke above resistance recently, now retesting
            broke_out = prev_5_high > resistance
            retesting = abs(candle["Close"] - resistance) < tolerance
            if broke_out and retesting and candle["Close"] > resistance:
                signals.iloc[i] = True

        return signals

    def get_indicators(self, df: pd.DataFrame) -> dict:
        return {}


# engine/strategies/hhhl.py
class HHHLStrategy(BaseStrategy):
    """Strategy 6 — Higher High Higher Low trend confirmation"""
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        signals = pd.Series(False, index=df.index)
        swing_highs = self._find_swing_highs(df, 5).dropna()
        swing_lows  = self._find_swing_lows(df, 5).dropna()

        sh_indices = list(swing_highs.index)
        sl_indices = list(swing_lows.index)

        for i in range(len(sl_indices) - 1):
            curr_sl_idx  = df.index.get_loc(sl_indices[i])
            next_sl_idx  = df.index.get_loc(sl_indices[i + 1])

            curr_sl = swing_lows.iloc[i]
            next_sl = swing_lows.iloc[i + 1]

            # Higher Low confirmed
            if next_sl > curr_sl:
                # Check Higher High between these lows
                between_highs = [
                    sh for sh in sh_indices
                    if sl_indices[i] < sh < sl_indices[i + 1]
                ]
                if between_highs:
                    signals.iloc[next_sl_idx] = True

        return signals

    def get_indicators(self, df: pd.DataFrame) -> dict:
        return {"EMA_50": self._ema(df["Close"], 50)}


# engine/strategies/order_block.py
class OrderBlockStrategy(BaseStrategy):
    """Strategy 7 — SMC Order Block Entry"""
    def _find_order_blocks(self, df: pd.DataFrame) -> list:
        obs = []
        for i in range(2, len(df) - 2):
            # Bearish candle (potential bullish OB)
            bearish   = df["Close"].iloc[i] < df["Open"].iloc[i]
            body_size = abs(df["Close"].iloc[i] - df["Open"].iloc[i])
            big_body  = body_size > (df["Close"].iloc[i] * 0.001)

            # Followed by strong bullish move
            next_bull = (df["Close"].iloc[i + 1] > df["Open"].iloc[i]
                         if i + 1 < len(df) else False)

            if bearish and big_body and next_bull:
                obs.append({
                    "index":  i,
                    "top":    float(df["Open"].iloc[i]),
                    "bottom": float(df["Close"].iloc[i]),
                    "time":   str(df.index[i])
                })
        return obs

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        signals = pd.Series(False, index=df.index)
        obs     = self._find_order_blocks(df)

        for i in range(50, len(df)):
            candle = df.iloc[i]
            for ob in obs:
                if ob["index"] >= i:
                    continue
                # Price tapping into OB zone
                in_zone = (candle["Low"]  <= ob["top"] and
                           candle["High"] >= ob["bottom"])
                confirmed = candle["Close"] > ob["bottom"]
                if in_zone and confirmed:
                    signals.iloc[i] = True
                    break

        return signals

    def get_indicators(self, df: pd.DataFrame) -> dict:
        return {"EMA_200": self._ema(df["Close"], 200)}

    def get_zones(self, df: pd.DataFrame) -> dict:
        obs = self._find_order_blocks(df)
        return {"order_blocks": obs[-10:]}  # last 10 OBs


# engine/strategies/fvg.py
class FVGStrategy(BaseStrategy):
    """Strategy 8 — SMC Fair Value Gap"""
    def _find_fvgs(self, df: pd.DataFrame) -> list:
        fvgs = []
        for i in range(1, len(df) - 1):
            # Bullish FVG: candle[i+1] low > candle[i-1] high
            if df["Low"].iloc[i + 1] > df["High"].iloc[i - 1]:
                fvgs.append({
                    "index":  i,
                    "top":    float(df["Low"].iloc[i + 1]),
                    "bottom": float(df["High"].iloc[i - 1]),
                    "type":   "bullish",
                    "time":   str(df.index[i])
                })
        return fvgs

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        signals = pd.Series(False, index=df.index)
        fvgs    = self._find_fvgs(df)

        for i in range(50, len(df)):
            candle = df.iloc[i]
            for fvg in fvgs:
                if fvg["index"] >= i:
                    continue
                # Price filling into FVG zone
                filling  = (candle["Low"]  <= fvg["top"] and
                            candle["High"] >= fvg["bottom"])
                confirmed = candle["Close"] > fvg["bottom"]
                if filling and confirmed:
                    signals.iloc[i] = True
                    break

        return signals

    def get_indicators(self, df: pd.DataFrame) -> dict:
        return {}

    def get_zones(self, df: pd.DataFrame) -> dict:
        fvgs = self._find_fvgs(df)
        return {"fvg_zones": fvgs[-10:]}


# engine/strategies/choch.py
class CHoCHStrategy(BaseStrategy):
    """Strategy 9 — SMC Change of Character"""
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        signals     = pd.Series(False, index=df.index)
        swing_highs = self._find_swing_highs(df, 5)
        swing_lows  = self._find_swing_lows(df, 5)

        for i in range(50, len(df)):
            # Get last swing high before current candle
            past_sh = swing_highs.iloc[:i].dropna()
            if len(past_sh) < 2:
                continue

            last_sh = past_sh.iloc[-1]

            # Bullish CHoCH: in downtrend, price breaks above last swing high
            past_sl = swing_lows.iloc[:i].dropna()
            if len(past_sl) < 2:
                continue

            # Confirm downtrend: lower highs pattern
            sh_values = past_sh.values[-3:]
            downtrend = len(sh_values) >= 2 and sh_values[-1] < sh_values[-2]

            if downtrend and df["Close"].iloc[i] > last_sh:
                signals.iloc[i] = True

        return signals

    def get_indicators(self, df: pd.DataFrame) -> dict:
        return {"EMA_50": self._ema(df["Close"], 50)}


# engine/strategies/bos_pullback.py
class BOSPullbackStrategy(BaseStrategy):
    """Strategy 10 — SMC Break of Structure + Pullback"""
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        signals     = pd.Series(False, index=df.index)
        swing_highs = self._find_swing_highs(df, 5)

        bos_levels = []

        for i in range(50, len(df)):
            past_sh = swing_highs.iloc[:i].dropna()
            if len(past_sh) < 1:
                continue

            last_sh_price = past_sh.iloc[-1]
            last_sh_idx   = past_sh.index[-1]

            # BOS: price breaks above swing high
            if df["Close"].iloc[i] > last_sh_price:
                bos_levels.append({
                    "level": last_sh_price,
                    "bos_idx": i
                })

            # After BOS, look for pullback to BOS level
            for bos in bos_levels[-3:]:  # check last 3 BOS levels
                candle     = df.iloc[i]
                tolerance  = bos["level"] * 0.003
                pullback   = abs(candle["Low"] - bos["level"]) < tolerance
                bounce     = candle["Close"] > bos["level"]
                after_bos  = i > bos["bos_idx"] + 1

                if pullback and bounce and after_bos:
                    signals.iloc[i] = True
                    break

        return signals

    def get_indicators(self, df: pd.DataFrame) -> dict:
        return {"EMA_50": self._ema(df["Close"], 50)}
