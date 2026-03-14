# api/models/request.py
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Timeframe(str, Enum):
    m1  = "1m"
    m5  = "5m"
    m15 = "15m"
    m30 = "30m"
    h1  = "1h"
    h4  = "4h"
    d1  = "1d"
    w1  = "1wk"


class Period(str, Enum):
    d7  = "7d"
    d60 = "60d"
    y1  = "1y"
    y2  = "2y"
    y3  = "3y"
    y5  = "5y"
    y10 = "10y"


class Market(str, Enum):
    india_equity = "india_equity"
    us_equity    = "us_equity"
    crypto       = "crypto"
    forex        = "forex"
    commodity    = "commodity"


class BacktestRequest(BaseModel):
    user_input:      str      = Field(..., description="Plain English strategy")
    ticker:          str      = Field("AUTO",  description="Ticker e.g. RELIANCE.NS or AUTO to detect from prompt")
    timeframe:       Timeframe = Field(Timeframe.h1,  description="Candle timeframe")
    period:          Period    = Field(Period.y2,     description="Backtest period")
    initial_capital: float    = Field(100000,         description="Starting capital in INR")
    market:          Market   = Field(Market.india_equity, description="Market type")

    class Config:
        json_schema_extra = {
            "example": {
                "user_input":      "backtest nifty with 50 EMA crossing above 200 EMA, 1:2 RR",
                "ticker":          "AUTO",
                "timeframe":       "1h",
                "period":          "2y",
                "initial_capital": 100000,
                "market":          "india_equity"
            }
        }
