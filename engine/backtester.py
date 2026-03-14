# engine/backtester.py
# Routes JSON rules to the correct strategy class
# Easy to add new strategies — just add to STRATEGY_MAP

import pandas as pd
from engine.strategies.base import BaseStrategy
from engine.strategies.ma_crossover import MACrossoverStrategy
from engine.strategies.rsi_reversal import RSIReversalStrategy
from engine.strategies.fibonacci_pullback import FibonacciPullbackStrategy
from engine.strategies.strategies import (
    SRBounceStrategy,
    BreakoutRetestStrategy,
    HHHLStrategy,
    OrderBlockStrategy,
    FVGStrategy,
    CHoCHStrategy,
    BOSPullbackStrategy
)
from engine.strategies.universal import UniversalStrategy
from engine.vbt_engine import run_vbt_analysis
import json

# ── Strategy registry ─────────────────────────────────────────
# To add a new strategy:
# 1. Create new file in engine/strategies/
# 2. Add it to this map
# That's it!

STRATEGY_MAP = {
    "ma_crossover":      MACrossoverStrategy,
    "rsi_reversal":      RSIReversalStrategy,
    "fibonacci_pullback": FibonacciPullbackStrategy,
    "sr_bounce":         SRBounceStrategy,
    "breakout_retest":   BreakoutRetestStrategy,
    "hhhl":              HHHLStrategy,
    "order_block":       OrderBlockStrategy,
    "fvg":               FVGStrategy,
    "choch":             CHoCHStrategy,
    "bos_pullback":      BOSPullbackStrategy,
    "universal":         UniversalStrategy,
}


def run_backtest(
    df:              pd.DataFrame,
    rules:           dict,
    market:          str   = "india_equity",
    initial_capital: float = 100000
) -> dict:
    """
    Main backtest runner.
    1. Reads strategy_id from parsed JSON rules
    2. Picks correct strategy class
    3. Runs bar-by-bar simulation
    4. Returns trades + equity + indicators + zones
    """
    strategy_id = rules.get("strategy_id", "ma_crossover")

    # Get strategy class — fallback to MA crossover if unknown
    StrategyClass = STRATEGY_MAP.get(strategy_id)

    if not StrategyClass:
        # Check if it's a DSL request (has indicators or logic keys)
        if "indicators" in rules or "logic" in rules:
            StrategyClass = UniversalStrategy
        else:
            # Try to find closest match
            for key in STRATEGY_MAP:
                if key in strategy_id or strategy_id in key:
                    StrategyClass = STRATEGY_MAP[key]
                    break
        
        if not StrategyClass:
            StrategyClass = MACrossoverStrategy  # safe fallback

    # Instantiate and run
    strategy = StrategyClass(rules=rules, market=market)
    results  = strategy.run(df=df, initial_capital=initial_capital)

    # ── vectorbt enhanced analytics (purely additive) ──────────
    signals = getattr(strategy, "_last_signals", None)
    if signals is not None:
        results["vbt_analytics"] = run_vbt_analysis(
            df=df,
            signals=signals,
            initial_capital=initial_capital
        )
    else:
        results["vbt_analytics"] = {}

    return results
