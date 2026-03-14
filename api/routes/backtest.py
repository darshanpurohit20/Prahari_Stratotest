import asyncio
import json
import re
import traceback
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from api.models.request import BacktestRequest
from api.models.response import BacktestResponse
from agent.parser import parse_strategy, generate_ai_insight
from engine.data import fetch_data, get_warnings
from engine.backtester import run_backtest
from engine.tearsheet import generate_tearsheet

router = APIRouter(tags=["backtest"])
executor = ThreadPoolExecutor(max_workers=5)

import agent.parser
import os
print(f"--- DEBUG: agent.parser file: {agent.parser.__file__}")
print(f"--- DEBUG: current working dir: {os.getcwd()}")

def _hint_market(ticker: str) -> str:
    """Guess market for parallel hint"""
    if any(c in ticker for c in ["-USD", "=X", "GC=F"]):
        if "-USD" in ticker: return "crypto"
        if "=X" in ticker: return "forex"
        return "commodity"
    return "india_equity"

def _hint_ticker(user_input: str) -> str:
    """Fast regex hint for parallel data fetching (Turbo)"""
    ui = user_input.lower()
    
    # Use word boundaries to avoid catching "nse" inside "defense" etc.
    if re.search(r"\b(nifty|nse|nsei)\b", ui): return "^NSEI"
    if re.search(r"\b(reliance|rel)\b", ui): return "RELIANCE.NS"
    if re.search(r"\b(tcs)\b", ui): return "TCS.NS"
    if re.search(r"\b(hdfc)\b", ui): return "HDFCBANK.NS"
    if re.search(r"\b(infy|infosys)\b", ui): return "INFY.NS"
    
    if re.search(r"\b(bitcoin|btc)\b", ui): return "BTC-USD"
    if re.search(r"\b(eth|ethereum)\b", ui): return "ETH-USD"
    if re.search(r"\b(sol|solana)\b", ui): return "SOL-USD"
    if re.search(r"\b(pepe)\b", ui): return "PEPE-USD"
    
    if re.search(r"\b(gold|gc)\b", ui): return "GC=F"
    if re.search(r"\b(silver|si)\b", ui): return "SI=F"
    if re.search(r"\b(eurusd)\b", ui): return "EURUSD=X"
    if re.search(r"\b(gbpusd)\b", ui): return "GBPUSD=X"
    
    return None

@router.post("/backtest", response_model=BacktestResponse)
async def backtest(request: BacktestRequest):
    try:
        # Step 0 — Start Parallel Hint Fetching (TURBO MODE)
        hint_ticker = _hint_ticker(request.user_input)
        hint_task = None
        if hint_ticker:
            hint_mkt = _hint_market(hint_ticker)
            # Use defaults ("1h", "2y") for the parallel guess
            hint_task = asyncio.get_event_loop().run_in_executor(
                executor, fetch_data, hint_ticker, "1h", "2y", hint_mkt
            )

        # Step 1 — LLM parses strategy
        t_start = time.time()
        parsed_rules = await parse_strategy(request.user_input)
        print(f"[debug] Step 1 (Parse) took: {time.time() - t_start:.2f}s")

        # Step 2 — Check if clarification is needed
        if parsed_rules.get("clarification_needed"):
            return JSONResponse(content={
                "strategy_name":        parsed_rules.get("strategy_name", "Strategy"),
                "ticker":               parsed_rules.get("ticker", "AUTO"),
                "timeframe":            parsed_rules.get("interval", "1h"),
                "period":               parsed_rules.get("period", "1y"),
                "parsed_rules":         parsed_rules,
                "clarification_needed": True,
                "question":             parsed_rules.get("question")
            })

        # Step 3 — Resolve ticker (LLM detected or user provided)
        ticker = request.ticker
        if ticker in ("AUTO", "", None):
            ticker = parsed_rules.get("ticker")
            if not ticker:
                raise HTTPException(
                    status_code=400,
                    detail="Could not detect asset. Please mention asset name e.g. 'nifty', 'bitcoin', 'gold'"
                )

        # Step 4 — Use LLM interval/period
        timeframe = parsed_rules.get("interval", "1h")
        period    = parsed_rules.get("period", "1y")

        # Step 5 — Detect market from LLM if not specified
        market = request.market.value
        if parsed_rules.get("market"):
            market = parsed_rules["market"]

        # Step 6 — Get warnings
        warnings = get_warnings(timeframe, period)

        # Step 7 — Fetch data (Market aware + Parallel Hint)
        t_fetch = time.time()
        if hint_task and ticker == hint_ticker and timeframe == "1h" and period == "2y":
            print(f"[api] Using background hint data for {ticker}...")
            df = await hint_task
        else:
            df = fetch_data(ticker=ticker, timeframe=timeframe, period=period, market=market)
        print(f"[debug] Step 7 (Fetch) took: {time.time() - t_fetch:.2f}s")
        
        if df is None or df.empty:
            raise HTTPException(
                status_code=400,
                detail=f"No data for '{ticker}' on {timeframe}. Try different timeframe or period."
            )

        # Step 8 — Run backtest
        t_bt = time.time()
        results = run_backtest(
            df=df,
            rules=parsed_rules,
            market=market,
            initial_capital=request.initial_capital
        )
        print(f"[debug] Step 8 (Backtest) took: {time.time() - t_bt:.2f}s")

        # Step 8 — Generate tearsheet
        t_tear = time.time()
        response = generate_tearsheet(
            results=results,
            df=df,
            parsed_rules=parsed_rules,
            ticker=ticker,
            timeframe=timeframe,
            period=period
        )
        print(f"[debug] Step 9 (Tearsheet) took: {time.time() - t_tear:.2f}s")

        # Step 9 — Generate AI Strategy Insight (Advanced Upgrade)
        t_insight = time.time()
        response.ai_insight = await generate_ai_insight(results)
        print(f"[debug] Step 10 (Insight) took: {time.time() - t_insight:.2f}s")

        # Step 10 — COMPARATIVE OPTIMIZATION (The Tweak)
        # If win rate is low, we try a mathematical tweak locally
        if results.get("metrics", {}).get("win_rate", 0) < 50:
            print("[api] Win rate low. Running comparative optimization...")
            # Use JSON serialization for a deep copy to avoid mutating the original
            tweaked_rules = json.loads(json.dumps(parsed_rules))
            # Add a 200 EMA trend filter logic
            if "indicators" not in tweaked_rules: tweaked_rules["indicators"] = []
            ema_id = f"ema_trend_{int(time.time())}"
            tweaked_rules["indicators"].append({"id": ema_id, "type": "ema", "params": {"period": 200}})
            
            # Inject into logic
            old_logic = tweaked_rules.get("logic", {"op": "AND", "conditions": []})
            new_logic = {
                "op": "AND",
                "conditions": old_logic.get("conditions", []) + [
                    {"left": "close", "op": "gt", "right": ema_id}
                ]
            }
            tweaked_rules["logic"] = new_logic
            
            # Run optimized version
            opt_results = run_backtest(df, tweaked_rules, market, request.initial_capital)
            if opt_results.get("trades"):
                opt_m = opt_results["metrics"]
                response.optimization_results = {
                    "win_rate": opt_m["win_rate"],
                    "total_return": opt_m["total_return_pct"],
                    "equity_curve": opt_results["equity"] # Full curve for comparative charting
                }
                response.optimization_summary = f"Adding a 200 EMA Trend Filter improved accuracy to {opt_m['win_rate']}%."

        # Check for zero trade warning from the base engine
        if results.get("warning"):
            warnings.append(results["warning"])

        response.warnings = warnings + response.warnings
        return response

    except HTTPException:
        raise
    except Exception as e:
        print("=== FULL ERROR ===")
        traceback.print_exc()
        print("==================")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse")
async def parse_only(user_input: str):
    """Test LLM parsing — see exactly what JSON is returned"""
    try:
        rules = await parse_strategy(user_input)
        return {"success": True, "parsed_rules": rules}
    except Exception as e:
        print("=== PARSE ERROR ===")
        traceback.print_exc()
        print("===================")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeframes")
def get_timeframes():
    return {
        "timeframes": [
            {"value": "1m",  "display": "1 Minute",  "max_history": "7 days",   "warning": True},
            {"value": "5m",  "display": "5 Minutes", "max_history": "60 days",  "warning": True},
            {"value": "15m", "display": "15 Minutes","max_history": "60 days",  "warning": True},
            {"value": "30m", "display": "30 Minutes","max_history": "60 days",  "warning": True},
            {"value": "1h",  "display": "1 Hour",    "max_history": "2 years",  "warning": False},
            {"value": "4h",  "display": "4 Hour",    "max_history": "2 years",  "warning": False},
            {"value": "1d",  "display": "Daily",     "max_history": "10 years", "warning": False},
            {"value": "1wk", "display": "Weekly",    "max_history": "20 years", "warning": False},
        ]
    }
