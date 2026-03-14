# engine/friction.py
# Realistic cost modelling — your key differentiator
# Models slippage, commissions, STT, spread

# ── Market friction presets ───────────────────────────────────
FRICTION_PRESETS = {
    "india_equity": {
        "commission_pct":     0.0003,   # Zerodha ~₹20 flat ~ 0.03% per side
        "slippage_pct":       0.0005,   # 0.05% market impact per side
        "spread_pct":         0.0002,   # bid-ask spread
        "stt_sell_pct":       0.001,    # STT on sell side (delivery)
        "gst_on_brokerage":   0.18,     # 18% GST on brokerage
        "sebi_charges_pct":   0.000001, # SEBI turnover fee
        "stamp_duty_pct":     0.00015,  # stamp duty on buy side
    },
    "us_equity": {
        "commission_pct":     0.0001,
        "slippage_pct":       0.0003,
        "spread_pct":         0.0001,
        "stt_sell_pct":       0.0,
        "gst_on_brokerage":   0.0,
        "sebi_charges_pct":   0.0,
        "stamp_duty_pct":     0.0,
    },
    "crypto": {
        "commission_pct":     0.001,    # 0.1% per side (Binance)
        "slippage_pct":       0.001,
        "spread_pct":         0.0005,
        "stt_sell_pct":       0.0,
        "gst_on_brokerage":   0.0,
        "sebi_charges_pct":   0.0,
        "stamp_duty_pct":     0.0,
    },
    "forex": {
        "commission_pct":     0.0001,
        "slippage_pct":       0.0002,
        "spread_pct":         0.0003,   # spread wider in forex
        "stt_sell_pct":       0.0,
        "gst_on_brokerage":   0.0,
        "sebi_charges_pct":   0.0,
        "stamp_duty_pct":     0.0,
    }
}

# ── Pip sizes per market ──────────────────────────────────────
PIP_SIZE = {
    "india_equity": 0.05,    # ₹0.05 tick size on NSE
    "us_equity":    0.01,    # $0.01
    "crypto":       0.01,    # varies but 0.01 is safe default
    "forex":        0.0001,  # standard forex pip
    "forex_jpy":    0.01,    # JPY pairs
}


def calculate_trade_friction(
    entry_price:  float,
    exit_price:   float,
    market:       str = "india_equity"
) -> float:
    """
    Calculate total friction cost for a round-trip trade
    Returns cost in price units (same as entry/exit price)
    """
    f = FRICTION_PRESETS.get(market, FRICTION_PRESETS["india_equity"])

    # Entry costs
    entry_commission = entry_price * f["commission_pct"]
    entry_slippage   = entry_price * f["slippage_pct"]
    entry_spread     = entry_price * f["spread_pct"] * 0.5
    entry_stamp      = entry_price * f["stamp_duty_pct"]

    # Exit costs
    exit_commission  = exit_price * f["commission_pct"]
    exit_slippage    = exit_price * f["slippage_pct"]
    exit_spread      = exit_price * f["spread_pct"] * 0.5
    exit_stt         = exit_price * f["stt_sell_pct"]

    # GST on total brokerage
    total_brokerage  = entry_commission + exit_commission
    gst              = total_brokerage * f["gst_on_brokerage"]

    # SEBI charges
    sebi             = (entry_price + exit_price) * f["sebi_charges_pct"]

    total_friction = (
        entry_commission + entry_slippage + entry_spread + entry_stamp +
        exit_commission  + exit_slippage  + exit_spread  + exit_stt +
        gst + sebi
    )

    return round(total_friction, 4)


def get_pip_size(market: str, ticker: str = "") -> float:
    """Returns pip size for given market"""
    if market == "forex" and "JPY" in ticker.upper():
        return PIP_SIZE["forex_jpy"]
    return PIP_SIZE.get(market, 0.01)


def get_friction_summary(market: str) -> dict:
    """Returns human readable friction breakdown for display"""
    f = FRICTION_PRESETS.get(market, FRICTION_PRESETS["india_equity"])
    return {
        "commission_per_side": f"{f['commission_pct'] * 100:.3f}%",
        "slippage_per_side":   f"{f['slippage_pct'] * 100:.3f}%",
        "spread":              f"{f['spread_pct'] * 100:.3f}%",
        "stt_on_sell":         f"{f['stt_sell_pct'] * 100:.3f}%",
        "total_roundtrip_approx": f"{(f['commission_pct'] * 2 + f['slippage_pct'] * 2 + f['spread_pct'] + f['stt_sell_pct']) * 100:.3f}%"
    }
