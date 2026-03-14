# api/routes/strategy.py
from fastapi import APIRouter

router = APIRouter(tags=["strategies"])

@router.get("/strategies")
def get_supported_strategies():
    """Returns all supported strategies with metadata"""
    return {
        "strategies": [
            # Classic Strategies
            {
                "id":          "ma_crossover",
                "name":        "MA / EMA Crossover",
                "type":        "classic",
                "description": "Buy when fast MA crosses above slow MA",
                "example":     "Buy when 50 EMA crosses above 200 EMA, SL below swing low, 1:2 RR"
            },
            {
                "id":          "rsi_reversal",
                "name":        "RSI Reversal",
                "type":        "classic",
                "description": "Buy oversold, sell overbought",
                "example":     "Buy when RSI drops below 30, sell when RSI crosses 70, 1:2 RR"
            },
            {
                "id":          "fibonacci_pullback",
                "name":        "Fibonacci Pullback",
                "type":        "classic",
                "description": "Buy at Fibonacci retracement in trending market",
                "example":     "Buy at 0.618 Fibonacci level in uptrend, SL below swing low, 1:3 RR"
            },
            {
                "id":          "sr_bounce",
                "name":        "Support / Resistance Bounce",
                "type":        "classic",
                "description": "Buy at key support, sell at resistance",
                "example":     "Buy when price bounces off support level, 1:2 RR"
            },
            {
                "id":          "breakout_retest",
                "name":        "Breakout + Retest",
                "type":        "classic",
                "description": "Buy after price breaks and retests key level",
                "example":     "Buy when price breaks resistance and retests it, SL below retest, 1:2 RR"
            },
            {
                "id":          "hhhl",
                "name":        "Higher High Higher Low",
                "type":        "price_action",
                "description": "Buy when uptrend structure confirmed",
                "example":     "Buy when market forms higher high and higher low, SL below HL, 1:2 RR"
            },
            # SMC Strategies
            {
                "id":          "order_block",
                "name":        "Order Block Entry",
                "type":        "smc",
                "description": "Buy when price returns to institutional order block",
                "example":     "Buy at bullish order block, SL below OB, 1:3 RR"
            },
            {
                "id":          "fvg",
                "name":        "Fair Value Gap",
                "type":        "smc",
                "description": "Buy when price fills bullish fair value gap",
                "example":     "Buy when price fills FVG, SL below FVG, 1:2 RR"
            },
            {
                "id":          "choch",
                "name":        "Change of Character",
                "type":        "smc",
                "description": "Buy on bullish CHoCH confirmation",
                "example":     "Buy on bullish change of character, SL below last swing low, 1:2 RR"
            },
            {
                "id":          "bos_pullback",
                "name":        "Break of Structure + Pullback",
                "type":        "smc",
                "description": "Buy after bullish BOS and pullback",
                "example":     "Buy after break of structure pullback, SL below BOS level, 1:2 RR"
            },
        ]
    }
