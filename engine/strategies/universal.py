# engine/strategies/universal.py
# The "Universal Engine" — parses JSON DSL logic and executes it
# No more static classes for every strategy!

import pandas as pd
import numpy as np
from engine.strategies.base import BaseStrategy

class UniversalStrategy(BaseStrategy):
    """
    Interprets a JSON DSL to build strategies on the fly.
    Schema:
    {
        "indicators": [
            {"id": "ma1", "type": "ema", "params": {"period": 20}},
            {"id": "rsi1", "type": "rsi", "params": {"period": 14}}
        ],
        "logic": {
            "op": "AND",
            "conditions": [
                {"left": "ma1", "op": "crosses_above", "right": 200},
                {"left": "rsi1", "op": "lt", "right": 30}
            ]
        }
    }
    """

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        # 1. Calc all indicators
        indicator_data = self._calculate_all_indicators(df)
        
        # 2. Evaluate logic block
        logic = self.rules.get("logic", {})
        signals = self._evaluate_logic(df, indicator_data, logic)
        
        return signals

    def get_indicators(self, df: pd.DataFrame) -> dict:
        """Return dict of Series for charting"""
        # We show all calculated indicators on the chart
        return self._calculate_all_indicators(df)

    # ── Private Implementation ────────────────────────────────

    def _calculate_all_indicators(self, df: pd.DataFrame) -> dict:
        results = {}
        indicators = self.rules.get("indicators", [])
        
        for ind in indicators:
            ind_id = ind.get("id")
            ind_type = ind.get("type").lower()
            params = ind.get("params", {})
            
            if ind_type == "ema":
                results[ind_id] = self._ema(df["Close"], params.get("period", 20))
            elif ind_type == "sma":
                results[ind_id] = self._sma(df["Close"], params.get("period", 20))
            elif ind_type == "rsi":
                results[ind_id] = self._rsi(df["Close"], params.get("period", 14))
            elif ind_type == "atr":
                results[ind_id] = self._atr(df, params.get("period", 14))
            elif ind_type == "fvg":
                results[ind_id] = self._fvg(df, params.get("direction", "bullish"))
            elif ind_type == "ob":
                results[ind_id] = self._ob(df, params.get("direction", "bullish"))
            elif ind_type == "close":
                results[ind_id] = df["Close"]
        
        return results

    def _evaluate_logic(self, df: pd.DataFrame, indicators: dict, logic: dict) -> pd.Series:
        op = logic.get("op", "AND").upper()
        conditions = logic.get("conditions", [])
        
        if not conditions:
            return pd.Series(False, index=df.index)

        results = []
        for cond in conditions:
            results.append(self._evaluate_condition(df, indicators, cond))
        
        # Combine
        combined = results[0]
        for next_res in results[1:]:
            if op == "AND":
                combined = combined & next_res
            else:
                combined = combined | next_res
                
        return combined

    def _evaluate_condition(self, df: pd.DataFrame, indicators: dict, cond: dict) -> pd.Series:
        left_key = cond.get("left")
        right_val = cond.get("right")
        op = cond.get("op", "gt")
        
        # Resolve values (could be indicator ID or raw number/string)
        def _resolve(val):
            if val in indicators:
                return indicators[val]
            # Try to parse as float if it's a number-like string or int
            try:
                f_val = float(val)
                return pd.Series(f_val, index=df.index)
            except:
                return pd.Series(0.0, index=df.index)

        left = _resolve(left_key)
        right = _resolve(right_val)
        
        if op == "gt" or op == ">":
            return left > right
        elif op == "lt" or op == "<":
            return left < right
        elif op == "gte" or op == ">=":
            return left >= right
        elif op == "lte" or op == "<=":
            return left <= right
        elif op == "eq" or op == "==":
            return left == right
        elif op == "crosses_above" or op == "cross_above":
            return (left > right) & (left.shift(1) <= right.shift(1))
        elif op == "crosses_below" or op == "cross_below":
            return (left < right) & (left.shift(1) >= right.shift(1))
            
        return pd.Series(False, index=df.index)
