# engine/tearsheet.py
# Calculates all performance metrics + prepares chart data
# Returns complete BacktestResponse

import pandas as pd
import numpy as np
from api.models.response import (
    BacktestResponse, PerformanceMetrics,
    TradeResult, CandleData, VbtAnalytics, MonteCarloData
)


def generate_tearsheet(
    results:      dict,
    df:           pd.DataFrame,
    parsed_rules: dict,
    ticker:       str,
    timeframe:    str,
    period:       str
) -> BacktestResponse:
    """
    Takes raw backtest results and produces full tearsheet
    """
    trades   = results["trades"]
    equity   = results["equity"]
    indicators = results["indicators"]
    zones    = results["zones"]
    vbt_raw  = results.get("vbt_analytics", {})

    # ── Performance metrics ────────────────────────────────────
    metrics = _calculate_metrics(trades, equity)

    # ── Chart data ─────────────────────────────────────────────
    candles       = _prepare_candles(df)
    equity_curve  = _prepare_equity_curve(df, equity)
    drawdown_curve = _prepare_drawdown_curve(equity_curve)
    ind_data      = _prepare_indicators(df, indicators)

    # ── Confidence level ───────────────────────────────────────
    confidence, confidence_reason = _assess_confidence(len(trades), period)

    # ── Build VbtAnalytics model (None if vbt not available) ──
    vbt_analytics = _build_vbt_model(vbt_raw)

    # ── Warnings ───────────────────────────────────────────────
    warnings = []
    if len(trades) < 30:
        warnings.append("⚠️ Less than 30 trades — results may not be statistically significant")
    if len(trades) == 0:
        warnings.append("❌ No trades generated — try adjusting strategy parameters or period")

    return BacktestResponse(
        strategy_name    = parsed_rules.get("strategy_name", "Custom Strategy"),
        ticker           = ticker,
        timeframe        = timeframe,
        period           = period,
        parsed_rules     = parsed_rules,
        metrics          = metrics,
        trades           = [TradeResult(**t) for t in trades],
        candles          = candles,
        equity_curve     = equity_curve,
        drawdown_curve   = drawdown_curve,
        indicators       = ind_data,
        zones            = zones,
        warnings         = warnings,
        confidence       = confidence,
        confidence_reason = confidence_reason,
        vbt_analytics    = vbt_analytics
    )


def _calculate_metrics(trades: list, equity: list) -> PerformanceMetrics:
    if not trades:
        return PerformanceMetrics(
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate=0, total_return_pct=0, total_return_inr=0,
            annual_return_pct=0, sharpe_ratio=0, max_drawdown_pct=0,
            profit_factor=0, avg_rr_achieved=0, calmar_ratio=0,
            max_consec_wins=0, max_consec_losses=0,
            avg_win_inr=0, avg_loss_inr=0,
            total_friction_cost=0, return_without_friction=0
        )

    wins   = [t for t in trades if t["result"] == "win"]
    losses = [t for t in trades if t["result"] == "loss"]

    total        = len(trades)
    win_count    = len(wins)
    loss_count   = len(losses)
    win_rate     = (win_count / total) * 100 if total > 0 else 0

    # Returns
    initial_capital    = equity[0]
    final_capital      = equity[-1]
    total_return_inr   = final_capital - initial_capital
    total_return_pct   = (total_return_inr / initial_capital) * 100
    annual_return_pct  = total_return_pct / max(len(equity) / 252, 1)

    # Sharpe ratio
    equity_series = pd.Series(equity)
    daily_returns = equity_series.pct_change().dropna()
    risk_free     = 0.065 / 252
    excess        = daily_returns - risk_free
    sharpe        = float((excess.mean() / excess.std()) * np.sqrt(252)) \
                    if excess.std() > 0 else 0

    # Max drawdown
    rolling_peak  = equity_series.cummax()
    drawdown      = (equity_series - rolling_peak) / rolling_peak * 100
    max_dd        = float(drawdown.min())

    # Profit factor
    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss   = abs(sum(t["pnl"] for t in losses))
    profit_factor = round(gross_profit / gross_loss, 3) if gross_loss > 0 else 0

    # Average RR achieved
    rr_list      = [t["rr_achieved"] for t in trades]
    avg_rr       = round(sum(rr_list) / len(rr_list), 3) if rr_list else 0

    # Calmar ratio
    calmar       = round(annual_return_pct / abs(max_dd), 3) if max_dd != 0 else 0

    # Consecutive wins/losses
    max_cw, max_cl, curr = 0, 0, 0
    for t in trades:
        if t["result"] == "win":
            curr = max(0, curr) + 1
            max_cw = max(max_cw, curr)
        else:
            curr = min(0, curr) - 1
            max_cl = max(max_cl, abs(curr))

    avg_win  = round(sum(t["pnl"] for t in wins) / win_count, 2) if win_count else 0
    avg_loss = round(sum(t["pnl"] for t in losses) / loss_count, 2) if loss_count else 0
    total_friction = round(sum(t["friction_cost"] for t in trades), 2)
    return_no_friction = round(total_return_pct + (total_friction / initial_capital * 100), 2)

    return PerformanceMetrics(
        total_trades         = total,
        winning_trades       = win_count,
        losing_trades        = loss_count,
        win_rate             = round(win_rate, 2),
        total_return_pct     = round(total_return_pct, 2),
        total_return_inr     = round(total_return_inr, 2),
        annual_return_pct    = round(annual_return_pct, 2),
        sharpe_ratio         = round(sharpe, 3),
        max_drawdown_pct     = round(max_dd, 2),
        profit_factor        = profit_factor,
        avg_rr_achieved      = avg_rr,
        calmar_ratio         = calmar,
        max_consec_wins      = max_cw,
        max_consec_losses    = max_cl,
        avg_win_inr          = avg_win,
        avg_loss_inr         = avg_loss,
        total_friction_cost  = total_friction,
        return_without_friction = return_no_friction
    )


def _prepare_candles(df: pd.DataFrame) -> list:
    candles = []
    for idx, row in df.iterrows():
        candles.append(CandleData(
            time=str(idx),
            open=round(float(row["Open"]), 4),
            high=round(float(row["High"]), 4),
            low=round(float(row["Low"]), 4),
            close=round(float(row["Close"]), 4),
            volume=round(float(row["Volume"]), 2)
        ))
    return candles


def _prepare_equity_curve(df: pd.DataFrame, equity: list) -> list:
    curve = []
    times = list(df.index) + [df.index[-1]]  # pad to same length
    for i, val in enumerate(equity):
        if i < len(df.index):
            curve.append({"time": str(df.index[i]), "value": round(val, 2)})
    return curve


def _prepare_drawdown_curve(equity_curve: list) -> list:
    if not equity_curve:
        return []
    values  = [e["value"] for e in equity_curve]
    series  = pd.Series(values)
    peak    = series.cummax()
    dd      = ((series - peak) / peak * 100).round(3)
    return [{"time": equity_curve[i]["time"], "value": float(dd.iloc[i])}
            for i in range(len(equity_curve))]


def _prepare_indicators(df: pd.DataFrame, indicators: dict) -> dict:
    result = {}
    for name, series in indicators.items():
        data = []
        for idx, val in series.items():
            if not pd.isna(val):
                data.append({"time": str(idx), "value": round(float(val), 4)})
        result[name] = data
    return result


def _assess_confidence(num_trades: int, period: str) -> tuple:
    if num_trades < 30:
        return "low", f"Only {num_trades} trades — need 100+ for reliable results"
    elif num_trades < 100:
        return "medium", f"{num_trades} trades — acceptable but more data preferred"
    else:
        return "high", f"{num_trades} trades — statistically reliable results"


def _build_vbt_model(vbt_raw: dict):
    """
    Convert raw vbt_analytics dict (from vbt_engine.py) into the
    VbtAnalytics Pydantic model. Returns None if vbt_raw is empty,
    ensuring graceful degradation when vectorbt is not installed.
    """
    if not vbt_raw:
        return None

    try:
        mc_raw = vbt_raw.get("monte_carlo", {})
        monte_carlo = None
        if mc_raw and "p10" in mc_raw:
            from api.models.response import MonteCarloData
            monte_carlo = MonteCarloData(
                p10=mc_raw["p10"],
                p50=mc_raw["p50"],
                p90=mc_raw["p90"],
                n_sims=mc_raw.get("n_sims", 100),
            )

        return VbtAnalytics(
            sortino_ratio      = vbt_raw.get("sortino_ratio"),
            omega_ratio        = vbt_raw.get("omega_ratio"),
            expectancy         = vbt_raw.get("expectancy"),
            best_trade_pct     = vbt_raw.get("best_trade_pct"),
            worst_trade_pct    = vbt_raw.get("worst_trade_pct"),
            avg_trade_duration = vbt_raw.get("avg_trade_duration"),
            vbt_equity_curve   = vbt_raw.get("vbt_equity_curve"),
            monte_carlo        = monte_carlo,
        )
    except Exception as e:
        print(f"[tearsheet] Failed to build VbtAnalytics model: {e}")
        return None
