# agent/parser.py
# Gemini LLM parser — uses google-generativeai for non-blocking execution
# Handles Universal JSON DSL logic

import json
import os
import hashlib
from typing import Any
from threading import Lock
from google import genai
from google.genai import types
from agent.prompts import SYSTEM_PROMPT, AI_STRATEGIST_PROMPT
from agent.tools import (
    TOOL_REGISTRY,
    run_backtest_tool,
    check_optimizations_tool,
    get_market_regime_tool,
    get_gemini_tools
)
from dotenv import load_dotenv

load_dotenv()

# ── Performance Caching ──────────────────────────────────────
# Hugging Face Spaces allows writing only to /tmp
LLM_CACHE_DIR = "/tmp/prahari_cache/llm"

os.makedirs(LLM_CACHE_DIR, exist_ok=True)

def _get_cache_path(key_data: str, prefix: str) -> str:
    h = hashlib.md5(key_data.encode()).hexdigest()
    return os.path.join(LLM_CACHE_DIR, f"{prefix}_{h}.json")

# ── Load API Key from Environment ────────────────────────────
def _parse_csv_env(value: str) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _load_api_keys() -> list[str]:
    # Preferred: GEMINI_API_KEYS="key1,key2,key3"
    keys = _parse_csv_env(os.getenv("GEMINI_API_KEYS", ""))
    if keys:
        return keys

    # Backward-compatible: GEMINI_API_KEY can also be comma-separated
    return _parse_csv_env(os.getenv("GEMINI_API_KEY", ""))


def _load_model_fallbacks() -> list[str]:
    # Optional override via env: GEMINI_MODELS="gemini-2.5-flash,gemini-2.0-flash"
    env_models = _parse_csv_env(os.getenv("GEMINI_MODELS", ""))
    
    if env_models:
        return env_models

    # Default broad fallback chain
    # Default broad fallback chain (Best → Worst)
    return [

    #🧠 Latest Gemini 3 Preview Models (Strong reasoning, but preview)

    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",

    #🚀 Gemini 2.5 (Most stable modern models)

    "gemini-2.5-flash-lite",


    # 🧠 Legacy Gemini routing aliases

    "gemini-flash-latest",
    "gemini-flash-lite-latest",

]


API_KEYS = _load_api_keys()
FALLBACK_MODELS = _load_model_fallbacks()

# Initialize client pool globally (round-robin)
CLIENTS = [genai.Client(api_key=key) for key in API_KEYS]
_client_lock = Lock()
_client_index = 0

if not CLIENTS:
    print("[parser.py] WARNING: GEMINI_API_KEYS / GEMINI_API_KEY is not set.")


def _next_client() -> tuple[Any, int]:
    """Round-robin client selection across configured API keys."""
    global _client_index
    if not CLIENTS:
        raise RuntimeError("No Gemini API keys configured. Set GEMINI_API_KEYS (comma-separated) or GEMINI_API_KEY.")

    with _client_lock:
        idx = _client_index % len(CLIENTS)
        _client_index = (_client_index + 1) % len(CLIENTS)
    return CLIENTS[idx], idx

async def _generate_with_fallback(contents, config=None, is_parser=False):
    """
    Tries multiple Gemini models in sequence to mitigate rate limits.
    """
    models = FALLBACK_MODELS
    last_err = None

    if not CLIENTS:
        raise RuntimeError("No Gemini clients available. Configure GEMINI_API_KEYS or GEMINI_API_KEY.")

    # Try each key (round-robin start) and each model before failing.
    for _ in range(len(CLIENTS)):
        client, client_idx = _next_client()
        for model_name in models:
            try:
                print(f"[parser.py] Attempting generation with key#{client_idx + 1} model={model_name}...")
                if is_parser and config:
                    response = await client.aio.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=config
                    )
                else:
                    response = await client.aio.models.generate_content(
                        model=model_name,
                        contents=contents
                    )

                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[parser.py] key#{client_idx + 1} model={model_name} failed: {e}")
                last_err = e
                continue
            
    raise last_err

async def agentic_backtest(request_data: Any) -> Any:
    """
    Advanced 'Deep Agent' loop (Multi-Turn).
    1. AI initializes strategy
    2. AI calls tools (Regime, Backtest, Optimize) in sequence
    3. AI loops until satisfied or max turns reached.
    """
    user_input = request_data.user_input
    tools = get_gemini_tools()
    
    try:
        if not CLIENTS:
            raise RuntimeError("No Gemini clients available. Configure GEMINI_API_KEYS or GEMINI_API_KEY.")

        last_err = None
        for _ in range(len(CLIENTS)):
            client, client_idx = _next_client()
            for model_name in FALLBACK_MODELS:
                try:
                    print(f"[agent] Starting deep-agent with key#{client_idx + 1} model={model_name}...")
                    chat = client.aio.chats.create(
                        model=model_name,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT + "\n\nCRITICAL: You are in DEEP AGENT mode. "
                            "1. ALWAYS call 'get_market_regime' first to understand the context. "
                            "2. Use 'run_backtest' to verify your strategy. "
                            "3. If results are poor (Win Rate < 50%), refine and test again. "
                            "4. Once satisfied, output the final JSON and stop calling tools.",
                            tools=tools
                        )
                    )

                    response = await chat.send_message(user_input)

                    # Multi-Turn Loop (Max 5 turns)
                    for _ in range(5):
                        parts = response.candidates[0].content.parts
                        # Check if there's a function call
                        f_calls = [p.function_call for p in parts if p.function_call]

                        if not f_calls:
                            break # No more tools, we have the final answer

                        # Handle each function call (usually one at a time)
                        tool_responses = []
                        for fc in f_calls:
                            print(f"[agent] AI calling tool: {fc.name} with {fc.args}")

                            # Route tool calls
                            if fc.name == "run_backtest":
                                res = await run_backtest_tool(**fc.args)
                            elif fc.name == "get_market_regime":
                                res = await get_market_regime_tool(**fc.args)
                            elif fc.name == "check_optimizations":
                                res = check_optimizations_tool(**fc.args)
                            else:
                                res = "Unknown tool."

                            tool_responses.append(
                                types.Part(
                                    function_response=types.FunctionResponse(
                                        name=fc.name,
                                        response={"result": res}
                                    )
                                )
                            )

                        # Send results back to AI
                        response = await chat.send_message(types.Content(parts=tool_responses))

                    # Final Parse
                    raw_json = response.text.strip()
                    parsed = json.loads(raw_json)
                    return _normalize(parsed)
                except Exception as e:
                    print(f"[agent] key#{client_idx + 1} model={model_name} failed: {e}")
                    last_err = e
                    continue

        raise last_err

    except Exception as e:
        print(f"[parser.py] Agentic Loop failed: {e}")
        return await parse_strategy(user_input)

async def generate_ai_insight(results: dict) -> str:
    """
    Generates a professional 'Chief Strategist' take on the backtest results.
    """
    if not results or "metrics" not in results:
        return "No sufficient data for AI insight."

    m = results.get("metrics", {})
    vbt = results.get("vbt_analytics", {})
    
    # 1. Check Cache
    cache_key = f"{results.get('strategy_name')}_{results.get('ticker')}_{results.get('timeframe')}_{m.get('total_return_pct')}"
    cache_path = _get_cache_path(cache_key, "insight")

    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f).get("insight", "")
        except: pass

    # 2. Format Prompt
    prompt_user_content = AI_STRATEGIST_PROMPT.format(
        strategy_name=results.get("strategy_name", "Unknown Strategy"),
        ticker=results.get("ticker", "Unknown Asset"),
        timeframe=results.get("timeframe", "Unknown Timeframe"),
        total_return=round(m.get("total_return_pct", 0), 2),
        win_rate=round(m.get("win_rate", 0), 2),
        profit_factor=round(vbt.get("profit_factor", 0), 2),
        max_drawdown=round(m.get("max_drawdown_pct", 0), 2),
        sortino=round(vbt.get("sortino_ratio", 0), 2)
    )

    # 2.5 ADD PROACTIVE TWEAK ADVICE
    # Based on results, we suggest a mathematical tweak
    tweak_note = ""
    win_rate = m.get("win_rate", 0)
    if win_rate < 45:
        tweak_note = "\n\n💡 PROACTIVE TWEAK: Your win rate is currently low. I recommend adding a 200 EMA filter to ensure you only trade in the direction of the major trend, or tightening your stop loss slightly."
    elif win_rate > 70 and results.get("trades", 0) < 5:
        tweak_note = "\n\n💡 PROACTIVE TWEAK: Results look great but the sample size is very small. Consider increasing the 'period' to verify this isn't just a lucky streak."
    
    prompt_user_content += tweak_note

    # 3. Call LLM (With Fallback)
    try:
        insight = await _generate_with_fallback(prompt_user_content)
        
        # Save cache
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump({"insight": insight}, f)
            
        return insight
    except Exception as e:
        print(f"[parser.py] AI Insight failed: {e}")
        return "The strategist is currently unavailable, but your metrics are ready to review below."


async def parse_strategy(user_input: str) -> dict:
    """
    Tries AI first (Async) via Gemini, with caching and regex fallback.
    """
    ui_lower = user_input.lower().strip()
    
    # ── Check Cache ──────────────────────────────────────────
    cache_path = _get_cache_path(ui_lower, "parse")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                print(f"[parser.py] Loading parse result from cache...")
                return json.load(f)
        except: pass

    # ── Try AI (Gemini with Fallback) ──────────────────────────
    last_error = None
    
    try:
        raw_text = await _generate_with_fallback(
            contents=user_input,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
            ),
            is_parser=True
        )

        parsed = json.loads(raw_text)
        
        if parsed:
            # Normalize and cache
            parsed = _normalize(parsed)
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(parsed, f)
            except: pass
            return parsed
        
    except Exception as e:
        last_error = e

    # ── Safety Net: Basic Regex Fallback (If AI is down) ──────
    # Try to extract ticker from input (DO NOT CACHE FALLBACKS)
    print(f"[parser.py] AI Parsing failed. Falling back to regex. Error: {last_error}")
    detected_ticker = None
    if "bitcoin" in ui_lower or "btc" in ui_lower: detected_ticker = "BTC-USD"
    elif "eth" in ui_lower: detected_ticker = "ETH-USD"
    elif "sol" in ui_lower: detected_ticker = "SOL-USD"
    elif "reliance" in ui_lower: detected_ticker = "RELIANCE.NS"
    elif "nifty" in ui_lower: detected_ticker = "^NSEI"
    
    if "rsi" in ui_lower:
        return _normalize({
            "clarification_needed": detected_ticker is None,
            "question": "Which asset should I test this RSI strategy on?" if detected_ticker is None else None,
            "strategy_id": "universal", "strategy_name": "RSI (Fallback)",
            "ticker": detected_ticker, "market": "india_equity" if ".NS" in str(detected_ticker) or "^" in str(detected_ticker) else "crypto",
            "indicators": [{"id": "rsi1", "type": "rsi", "params": {"period": 14}}],
            "logic": {"op": "AND", "conditions": [{"left": "rsi1", "op": "lt", "right": 30}]},
            "notes": "⚠️ AI Busy. Used basic RSI extraction."
        })
    
    if "ema" in ui_lower or "ma" in ui_lower:
        return _normalize({
            "clarification_needed": detected_ticker is None,
            "question": "Which asset should I test this MA Crossover on?" if detected_ticker is None else None,
            "strategy_id": "universal", "strategy_name": "MA Cross (Fallback)",
            "ticker": detected_ticker, "market": "india_equity" if ".NS" in str(detected_ticker) or "^" in str(detected_ticker) else "crypto",
            "indicators": [{"id": "ma1", "type": "ema", "params": {"period": 50}}, {"id": "ma2", "type": "ema", "params": {"period": 200}}],
            "logic": {"op": "AND", "conditions": [{"left": "ma1", "op": "crosses_above", "right": "ma2"}]},
            "notes": "⚠️ AI Busy. Used basic MA extraction."
        })
        
    # If we get here, AI failed and we have no fallback pattern
    raise ValueError(f"AI Parse Failed. Please verify your GEMINI_API_KEY and API Limits. Error: {last_error}")


def _normalize(parsed: dict) -> dict:
    """Ensures consistent format for the engine"""
    # 1. Map legacy strategy_params if present
    sp  = parsed.get("strategy_params", {})
    el  = parsed.get("exit_logic", {})
    sl  = el.get("stop_loss", {})
    tp  = el.get("take_profit", {})

    # 2. Preserve/Initialize DSL keys ONLY if they are part of the core rules
    if "indicators" in parsed:
        parsed["indicators"] = parsed.get("indicators")
    if "logic" in parsed:
        parsed["logic"]      = parsed.get("logic")

    # 3. Create unified entry/exit blocks for standard strategies
    parsed["entry"] = {
        "indicator":    sp.get("indicator"),
        "condition":    parsed.get("entry_condition", "crosses_above"),
        "direction":    sp.get("direction", "bullish"),
        "params":       sp
    }

    parsed["stop_loss"] = {
        "type":           sl.get("type", "swing_low"),
        "lookback":       sl.get("lookback", 5),
        "value":          sl.get("value")
    }

    parsed["take_profit"] = {
        "type":  tp.get("type", "risk_reward"),
        "ratio": tp.get("ratio", 2.0)
    }

    # 4. Preserve Agent Intelligence
    if "market_regime" in parsed:
        parsed["market_regime"] = parsed["market_regime"]

    return parsed
