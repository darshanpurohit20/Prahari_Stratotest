from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class TradeResult(BaseModel):
    trade_number:  int
    entry_time:    str
    exit_time:     str
    entry_price:   float
    exit_price:    float
    sl_price:      float
    tp_price:      float
    result:        str
    pnl:           float
    pnl_pct:       float
    rr_achieved:   float
    friction_cost: float

class PerformanceMetrics(BaseModel):
    total_trades:        int
    winning_trades:      int
    losing_trades:       int
    win_rate:            float
    total_return_pct:    float
    total_return_inr:    float
    annual_return_pct:   float
    sharpe_ratio:        float
    max_drawdown_pct:    float
    profit_factor:       float
    avg_rr_achieved:     float
    calmar_ratio:        float
    max_consec_wins:     int
    max_consec_losses:   int
    avg_win_inr:         float
    avg_loss_inr:        float
    total_friction_cost: float
    return_without_friction: float

class CandleData(BaseModel):
    time:   str
    open:   float
    high:   float
    low:    float
    close:  float
    volume: float

class MonteCarloData(BaseModel):
    p10:    List[float]
    p50:    List[float]
    p90:    List[float]
    n_sims: int

class VbtAnalytics(BaseModel):
    sortino_ratio:       Optional[float] = None
    omega_ratio:         Optional[float] = None
    profit_factor:       Optional[float] = None
    max_drawdown_pct:    Optional[float] = None
    recovery_factor:     Optional[float] = None
    max_dd_duration:     Optional[int]   = None
    expectancy:          Optional[float] = None
    best_trade_pct:      Optional[float] = None
    worst_trade_pct:     Optional[float] = None
    avg_trade_duration:  Optional[float] = None
    vbt_equity_curve:    Optional[List[Dict]]= None
    monte_carlo:         Optional[MonteCarloData] = None

class BacktestResponse(BaseModel):
    strategy_name:   str
    ticker:          str
    timeframe:       str
    period:          str
    parsed_rules:    Dict[str, Any]
    clarification_needed: bool = False
    question:             Optional[str] = None
    metrics:         Optional[PerformanceMetrics] = None
    trades:          List[Any] = Field(default_factory=list)
    candles:         List[Any] = Field(default_factory=list)
    equity_curve:    List[Any] = Field(default_factory=list)
    drawdown_curve:  List[Any] = Field(default_factory=list)
    indicators:      Dict[str, Any] = Field(default_factory=dict)
    zones:           Dict[str, Any] = Field(default_factory=dict)
    warnings:        List[str] = Field(default_factory=list)
    confidence:      Optional[str] = None
    confidence_reason: Optional[str] = None
    vbt_analytics:   Optional[VbtAnalytics] = None
    ai_insight:      Optional[str] = None
    optimization_results: Optional[Dict[str, Any]] = None # Holds tweaked stats for comparison
    optimization_summary: Optional[str] = None           # Summary of the improvement
