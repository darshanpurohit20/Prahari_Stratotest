# StratoTest by Team Prahari
### Agentic AI Backtesting Tool — Describe a strategy in plain English. Get a full backtest in seconds.

[![Live Demo](https://img.shields.io/badge/🤗%20Hugging%20Face-Live%20Demo-blue)](https://darshanpurohit-stratotest.hf.space/)
[![Space](https://img.shields.io/badge/🤗%20Hugging%20Face-Space%20+%20Code-yellow)](https://huggingface.co/spaces/Darshanpurohit/StratoTest/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B)](https://streamlit.io/)

---

---

<div align="center">

# ⚔️ TEAM PRAHARI ⚔️
```
╔══════════════════════════════════════════════════════╗
║              Built by three builders.                ║
║             Powered by one obsession.                ║
╚══════════════════════════════════════════════════════╝
```

<br/>

| &nbsp;&nbsp;&nbsp;🧑‍💻&nbsp;&nbsp;&nbsp; | Builder | &nbsp;&nbsp;&nbsp;GitHub&nbsp;&nbsp;&nbsp; |
|:---:|:---|:---:|
| ![](https://img.shields.io/badge/-●-ff6b6b?style=flat-square) | **Chandan Singh** | [![GitHub](https://img.shields.io/badge/chandan22468-%23181717?style=for-the-badge&logo=github)](https://github.com/chandan22468) |
| ![](https://img.shields.io/badge/-●-ffd93d?style=flat-square) | **Darshan Purohit** | [![GitHub](https://img.shields.io/badge/darshanpurohit20-%23181717?style=for-the-badge&logo=github)](https://github.com/darshanpurohit20) |
| ![](https://img.shields.io/badge/-●-6bcb77?style=flat-square) | **Harsh Redasani** | [![GitHub](https://img.shields.io/badge/redasaniharsh-%23181717?style=for-the-badge&logo=github)](https://github.com/redasaniharsh) |

<br/>

![](https://img.shields.io/badge/Hackathon-2026-blueviolet?style=for-the-badge)
![](https://img.shields.io/badge/Made%20with-Claude%20+%20Gemini%20+%20Pinecone-black?style=for-the-badge)
![](https://img.shields.io/badge/India-🇮🇳-orange?style=for-the-badge)

</div>

---

## 🌐 Deployed Links

| Interface | URL |
|---|---|
| **Direct UI** | [darshanpurohit-stratotest.hf.space](https://darshanpurohit-stratotest.hf.space/) |
| **UI + Codebase (Hugging Face Space)** | [huggingface.co/spaces/Darshanpurohit/StratoTest](https://huggingface.co/spaces/Darshanpurohit/StratoTest/) |

---

## 🧠 What is StratoTest?

StratoTest is a **multi-agent AI backtesting system**. A user types a trading strategy in plain English. A pipeline of autonomous AI agents converts that description into executable Python code, validates it, runs a realistic historical simulation with friction modelling, generates a performance tearsheet, and then autonomously optimizes the strategy — all without any further user input.

A **Talkback Validation Agent** acts as a conversational gatekeeper, ensuring queries are complete before expensive computation begins. A **Pinecone RAG Layer** provides a strategy memory store, surfacing historically relevant configurations to auto-fill missing details and improve results over time.

---

## ✨ Key Features (USPs)

1. **Self-correcting code generation** — The agent writes Python strategy code, runs it in a sandbox, and fixes its own errors without user intervention. Not a chatbot — an agent with a goal.

2. **Autonomous optimization loop** — The Optimization Agent tries parameter variants, compares results, keeps improvements, and discards regressions. Goal-driven: targets Sharpe > 1.0 and Max Drawdown < 20%.

3. **Lookahead bias detection** — The Validation Agent checks for future data leakage, a real quantitative finance concern that most tools ignore entirely.

4. **Live agent reasoning panel** — Every tool call, every decision, every fix is streamed to the UI in real time. Watch the agent think.

5. **Session memory** — "Test the same strategy but add a volume filter" works because agents remember prior runs.

6. **Friction-realistic results** — Slippage, commissions, and spread are baked in. Results reflect what you'd actually make, not theoretical maximums.

7. **Explain Agent** — Post-backtest, ask "Why did it lose in 2022?" and get a narrative explanation with structural fix suggestions.

8. **Talkback Validation Layer** — Before any compute, the Talkback Agent confirms all required fields (asset, timeframe, date range, strategy intent) — using RAG to auto-suggest smart defaults from past successful runs.

9. **Pinecone RAG Memory** — Every successful backtest is embedded and stored. Future queries retrieve semantically similar past configs to guide decisions automatically.

---

## 🏗️ System Architecture

### The Multi-Agent Pipeline

```
User Natural Language Input
         │
         ▼
┌─────────────────────────────┐
│    TALKBACK AGENT (NEW)     │  ← Validates query completeness
│                             │    Uses Pinecone RAG for smart defaults
│  Checks:                    │    Asks user only if RAG can't fill gaps
│  • asset_name               │
│  • timeframe                │
│  • start_date / end_date    │
│  • strategy_hint            │
└────────┬────────────────────┘
         │ enriched, complete query
         ▼
┌─────────────────────────────┐
│      STRATEGY AGENT         │  ← LangChain + Claude + Tools
│                             │    Writes Python strategy code
│  Tools:                     │    Self-corrects syntax errors
│  • validate_syntax          │    Loops until sandbox passes
│  • run_sandbox_test         │
└────────┬────────────────────┘
         │ validated strategy code (Python string)
         ▼
┌─────────────────────────────┐
│     VALIDATION AGENT        │  ← Separate LLM call
│                             │    Checks lookahead bias
│  Checks:                    │    Minimum trade count
│  • lookahead bias           │    Sharpe sanity check
│  • trade frequency          │    Sends PASS or FAIL+reason
│  • Sharpe sanity            │    back to Strategy Agent
└────────┬────────────────────┘
         │ PASS
         ▼
┌─────────────────────────────┐
│   BACKTEST ENGINE           │  ← Pure Python, no LLM
│                             │    exec() the strategy code
│  Applies:                   │    Apply friction costs
│  • slippage                 │    Calculate all metrics
│  • commissions              │
│  • spread                   │
└────────┬────────────────────┘
         │ metrics dict
         ▼
┌─────────────────────────────┐
│    OPTIMIZATION AGENT       │  ← LangChain + Claude + Tools
│                             │    Goal: Sharpe > 1.0, DD < 20%
│  Tools:                     │    ONE tweak per iteration
│  • tweak_parameter          │    Max 4 iterations
│  • run_full_backtes         │    Returns best variant
└────────┬────────────────────┘
         │ best strategy + all iteration metrics
         ▼
┌─────────────────────────────┐
│      TEARSHEET + UI         │  ← Plotly charts + Streamlit
│                             │    Equity curve
│   Shows:                    │    Drawdown chart
│  • Original vs Best         │    Monthly returns heatmap
│  • Iteration table          │    Agent reasoning log
│  • Explain button           │
└─────────────────────────────┘
         │ on-demand
         ▼
┌─────────────────────────────┐
│     EXPLAIN AGENT           │  ← Single LLM call, no tools
│                             │    Analyzes bad periods
│  Answers:                   │    Explains WHY it lost money
│  • "Why 2022 loss?"         │    Suggests structural fixes
│  • "What kills it?"         │
└─────────────────────────────┘
```

### RAG + Talkback Layer (Intelligence Layers)

The existing pipeline is extended with two intelligence layers that prevent silent hallucination and leverage historical strategy memory:

```
BEFORE (Old Flow):
  User Query ──────────────────────────→ Deep Agent → Backtest

AFTER (New Flow):
  User Query → [Talkback Agent] → [RAG Layer] → [Validation Gate]
                                                      │
                                                      ▼ 
                                          ┌───────────┴───────────┐
                                          ▼                       ▼
                                   [Complete Query]        [Incomplete Query]
                                          │                       │
                                          │               [Ask User + LLM Defaults]
                                          │                       │
                                          └───────────┬───────────┘
                                                      ▼
                                               Deep Agent Controller
                                                      │
                                                      ▼
                                               Backtest Engine
                                                      │
                                                      ▼
                                        [Index Result → Pinecone RAG]
```

| Layer | Name | Role | Technology |
|---|---|---|---|
| Layer 1 | **Pinecone RAG Layer** | Retrieves historically relevant strategy configs from a vector database | Pinecone + Gemini Embeddings |
| Layer 2 | **Talkback Validation Agent** | Validates all required fields; uses RAG to suggest smart defaults; asks user only when necessary | Gemini 2.0 Flash + Pinecone |

#### What Gets Stored in Pinecone

Every successful backtest (win rate > 50%) is embedded and stored. Each vector carries rich metadata:

```json
{
  "strategy_id": "uuid-v4",
  "asset_name": "RELIANCE.NS",
  "asset_label": "Reliance Industries",
  "timeframe": "1d",
  "start_date": "2022-01-01",
  "end_date": "2024-01-01",
  "duration_label": "2 years",
  "strategy_type": "EMA Cross",
  "indicators_used": ["EMA_20", "EMA_50", "ADX"],
  "win_rate": 62.5,
  "roi": 18.3,
  "market_regime": "trending",
  "trade_count": 45,
  "summary_text": "EMA 20/50 crossover on Reliance Industries daily chart over 2 years trending regime"
}
```

#### Talkback Decision Logic

The Talkback Agent enforces that all 5 required fields are resolved before passing the query to the Deep Agent:

| Field | Example Values | Resolution Path |
|---|---|---|
| `asset_name` | `"Nifty 50"`, `"RELIANCE"`, `"BTC/USD"` | User text → NER → RAG suggestion → User confirm |
| `timeframe` | `"1d"`, `"1h"`, `"15m"`, `"1w"` | User text → RAG suggestion → LLM default |
| `start_date` | `"2022-01-01"` | User text → duration math → LLM default |
| `end_date` | `"2024-12-31"` or `"today"` | Derived from start + duration |
| `strategy_hint` | `"RSI overbought"`, `"EMA cross"`, `"breakout"` | User intent → RAG strategy_type → LLM inference |

Auto-fill threshold: if RAG confidence score > 0.85, the field is filled automatically and the user is notified. Below 0.85, the field goes to the missing list and the Talkback UI presents options.

---

## 🚀 Quick Start

### 1. Clone and set up

```bash
git clone https://github.com/darshanpurohit20/Prahari_Stratotest
cd Prahari_Stratotest
cp .env.example .env
```

### 2. Add your API keys

Edit `.env`:

```env
ANTHROPIC_API_KEY=your_anthropic_key_here
PINECONE_API_KEY=your_pinecone_key_here
GEMINI_API_KEY=your_gemini_key_here
```

Get your Anthropic key at: https://console.anthropic.com/

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. (Optional) Seed Pinecone with sample strategies

```bash
python scripts/seed_pinecone.py
```

### 5. Start the FastAPI backend

```bash
uvicorn main:app --reload --port 8000
```

### 6. Start the Streamlit frontend (new terminal)

```bash
streamlit run frontend/app.py
```

### 7. Open browser

- **Frontend:** http://localhost:8501
- **API Docs:** http://localhost:8000/docs

---

## 📁 Project Structure

```
prahari/
│
├── main.py                          ← FastAPI app factory + uvicorn runner
├── requirements.txt                 ← All pinned dependencies
├── .env.example                     ← Template for secrets (never commit .env)
├── .gitignore
├── config.py                        ← Central config (env vars, constants)
│
├── agent/                           ← All LLM agent logic
│   ├── tools.py                     ← @tool decorated LangChain tools
│   ├── strategy_agent.py            ← Agent 1: code generation + self-correction
│   ├── validation_agent.py          ← Agent 2: bias + sanity checks
│   ├── optimization_agent.py        ← Agent 3: autonomous parameter tuning
│   ├── explain_agent.py             ← Agent 4: narrative loss explanation
│   ├── memory.py                    ← Session context store
│   ├── pipeline.py                  ← Master orchestrator
│   ├── parser.py                    ← Claude LLM parser
│   └── prompts.py                   ← All system prompts (single source of truth)
│
├── rag/                             ← RAG + Talkback intelligence layers (NEW)
│   ├── embedder.py                  ← Gemini text-embedding-004 wrapper
│   ├── indexer.py                   ← Pinecone upsert + index_completed_strategy()
│   ├── retriever.py                 ← Pinecone query + top-K fetch
│   ├── talkback_agent.py            ← Talkback Validation Agent (Gemini 2.0 Flash)
│   ├── default_generator.py         ← LLM Default Generator + static fallbacks
│   └── validator.py                 ← Entity extraction + confidence scoring
│
├── engine/                          ← Pure Python backtesting (no LLM)
│   ├── data.py                      ← yfinance OHLCV fetcher + indicator calc
│   ├── backtester.py                ← exec() engine + trade simulator
│   ├── friction.py                  ← Slippage, commission, spread models
│   ├── tearsheet.py                 ← Metrics computation + chart data
│   └── strategies/
│       ├── base.py                  ← BaseStrategy ABC — every generated class inherits this
│       ├── ma_crossover.py          ← Strategy 1: MA / EMA Crossover
│       ├── rsi_reversal.py          ← Strategy 2: RSI Reversal
│       ├── fibonacci_pullback.py    ← Strategy 3: Fibonacci Pullback
│       └── strategies.py           ← Strategies 4–10
│
├── api/                             ← FastAPI REST layer
│   ├── models/
│   │   ├── request.py               ← Pydantic input models
│   │   └── response.py              ← Pydantic output models
│   └── routes/
│       ├── backtest.py              ← POST /backtest
│       ├── talkback.py              ← POST /talkback/validate, POST /talkback/confirm (NEW)
│       ├── strategy.py              ← GET /strategies, POST /explain
│       └── health.py                ← GET /health
│
├── scripts/
│   └── seed_pinecone.py             ← One-time Pinecone seed script for testing
│
└── frontend/
    └── app.py                       ← Streamlit UI (single file)
```

---

## 🎯 Supported Strategies

### Classic

| # | Strategy |
|---|---|
| 1 | MA / EMA Crossover |
| 2 | RSI Reversal |
| 3 | Fibonacci Pullback |
| 4 | Support / Resistance Bounce |
| 5 | Breakout + Retest |
| 6 | Higher High Higher Low |

### SMC (Smart Money Concepts)

| # | Strategy |
|---|---|
| 7 | Order Block Entry |
| 8 | Fair Value Gap (FVG) |
| 9 | Change of Character (CHoCH) |
| 10 | Break of Structure + Pullback |

---

## 💬 Example Inputs

```
"Buy when 50 EMA crosses above 200 EMA, SL below last swing low, 1:2 RR"
"Buy at bullish order block, SL below OB, 1:3 RR"
"Buy when RSI drops below 30, SL below swing low, 1:2 RR"
"Buy at 0.618 fibonacci level in uptrend, 1:2 RR"
"Buy after break of structure pullback, SL below BOS, 1:3 RR"
"Buy when MACD crosses above signal line and RSI is below 60"
"Buy at Bollinger Band lower band, sell at upper band"
```

---

## 🌍 Supported Markets & Tickers

| Market | Example Tickers |
|---|---|
| NSE India | `RELIANCE.NS`, `TCS.NS`, `INFY.NS` |
| BSE India | `RELIANCE.BO` |
| Nifty Index | `^NSEI`, `^NSEBANK` |
| US Stocks | `AAPL`, `TSLA`, `GOOGL` |
| Crypto | `BTC-USD`, `ETH-USD` |
| Forex | `EURUSD=X`, `GBPUSD=X` |

---

## 🔌 API Reference

### Core Endpoints

| Method | Route | Description |
|---|---|---|
| `POST` | `/backtest` | Run a full agentic backtest |
| `GET` | `/strategies` | List all supported strategy types |
| `POST` | `/explain` | Ask the Explain Agent about backtest results |
| `GET` | `/health` | Service health check |

### Talkback Endpoints (RAG Layer)

| Method | Route | Description |
|---|---|---|
| `POST` | `/talkback/validate` | Submit a raw query for entity extraction + RAG validation |
| `POST` | `/talkback/confirm` | Submit confirmed/modified fields to get an enriched query ready for the Deep Agent |

#### Example: Validate a query

```bash
curl -X POST http://localhost:8000/talkback/validate \
  -H "Content-Type: application/json" \
  -d '{"user_query": "RSI strategy on Nifty"}'
```

Response when fields are missing:

```json
{
  "status": "incomplete",
  "resolved_fields": {
    "asset_name": "^NSEI",
    "strategy_hint": "RSI"
  },
  "missing_fields": [
    {
      "field": "timeframe",
      "question": "What timeframe should the backtest use?",
      "options": [
        {"label": "Daily (1d)", "value": "1d"},
        {"label": "Hourly (1h)", "value": "1h"},
        {"label": "Weekly (1wk)", "value": "1wk"},
        {"label": "Custom — I'll type it", "value": null}
      ],
      "rag_suggestion": {
        "label": "Daily (based on similar Nifty RSI strategies)",
        "confidence": 0.91
      }
    }
  ]
}
```

---

## 📊 Data Schemas

### BacktestResult

```python
{
    "total_trades":          int,
    "sharpe_ratio":          float,   # annualised
    "max_drawdown_pct":      float,   # negative, e.g. -18.3
    "win_rate_pct":          float,   # 0–100
    "total_return_pct":      float,
    "profit_factor":         float,
    "avg_trade_return_pct":  float,
    "best_trade_pct":        float,
    "worst_trade_pct":       float,
    "equity_curve":          list[float],         # one per bar
    "monthly_returns":       dict[str, float],    # {"2023-01": 2.3, ...}
    "warning":               str | None,
    "error":                 str | None,
    "traceback":             str | None,
}
```

### PipelineResult

```python
{
    "success":              bool,
    "strategy_name":        str,
    "run_id":               str,
    "strategy_code":        str,
    "baseline_metrics":     BacktestResult,
    "optimized_metrics":    BacktestResult,
    "all_iterations":       list[{
                                "label":              str,
                                "metrics":            BacktestResult,
                                "change_description": str,
                            }],
    "improvement_pct":      float,
    "goal_met":             bool,
    "validation_issues":    list[str],
    "reasoning_log":        list[str],
    "stage_failed":         str | None,
    "error":                str | None,
}
```

---

## ⚠️ Error Handling

Every agent function returns a result dict with a `"success"` or `"error"` key — nothing raises unhandled exceptions. Errors are surfaced to the UI gracefully with friendly messages.

| Stage | Fallback |
|---|---|
| Data fetch failure | Return early: `"Could not fetch data for {ticker}"` |
| Strategy Agent fails | Return agent's last error + reasoning log |
| Validation fails | Log warning, continue (sandbox already passed) |
| Backtest fails | Return engine error + strategy code for debug |
| Optimization fails | Return baseline results + log that optimization failed |
| Pinecone unavailable | Skip RAG entirely, proceed with entity extraction only |
| Gemini embedding fails | Use cached zero-vector, skip RAG for this request |
| Pinecone upsert fails | Log warning, return backtest result normally — non-blocking |
| RAG returns 0 matches | Skip RAG suggestions, rely purely on LLM defaults |

---

## ➕ Extending the System

The system is designed so new features can be added without modifying existing files.

### Adding a New Strategy

1. Create `engine/strategies/my_strategy.py`
2. Inherit `BaseStrategy`
3. Implement `generate_signals()` and `get_indicators()`
4. Add to `STRATEGY_MAP` in `engine/backtester.py`
5. Add to `GET /strategies` in `api/routes/strategy.py`

### Adding a New Agent

1. Create `agent/new_agent.py`
2. Follow the pattern: `run_new_agent(inputs..., progress_callback) -> dict`
3. Add it as a step in `agent/pipeline.py`
4. Add its system prompt to `agent/prompts.py`

### Adding a New Chart

1. Add `build_X_chart(result: dict) -> go.Figure` to `engine/tearsheet.py`
2. Import and call it in `frontend/app.py`

### Adding Persistence (Redis/DB)

1. Modify `agent/memory.py` — implement `save_session` and `get_or_create_session` to use Redis instead of the in-memory `_sessions` dict
2. No other files need to change

### Adding a New Market/Ticker Type

1. Nothing to change — yfinance handles NSE (`.NS`), crypto (`-USD`), and forex (`=X`) automatically
2. Optionally add examples to the UI pill buttons in `frontend/app.py`

---

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
pytest tests/

# Key test cases
# tests/test_talkback.py
```

```python
def test_complete_query_returns_ready():
    result = process_query("Backtest Nifty 50 EMA crossover daily from 2022 to 2024")
    assert result["status"] == "ready"
    assert result["enriched_query"]["asset_name"] == "^NSEI"

def test_missing_timeframe_triggers_talkback():
    result = process_query("RSI strategy on Reliance from 2022")
    assert result["status"] in ["incomplete", "ready"]
    if result["status"] == "incomplete":
        assert "timeframe" in result["talkback_options"]

def test_completely_vague_query_returns_all_missing():
    result = process_query("run a backtest")
    assert result["status"] == "incomplete"
    assert len(result["talkback_options"]) >= 3
```

### Integration Test (End-to-End)

```bash
# Start the backend
uvicorn api.main:app --reload

# Test talkback route
curl -X POST http://localhost:8000/talkback/validate \
  -H "Content-Type: application/json" \
  -d '{"user_query": "RSI strategy on Nifty"}'

# Test engine in isolation (no API key needed)
python -c "
from engine.data import fetch_ohlc
from engine.backtester import run_backtest_from_code
df = fetch_ohlc('AAPL', '90d')
print(df.columns.tolist())
print(f'Data shape: {df.shape}')
"
```

### Seed Pinecone for RAG Testing

```bash
python scripts/seed_pinecone.py
```

---

## 🔧 Environment Variables

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...
PINECONE_API_KEY=...
GEMINI_API_KEY=...

# Optional (with defaults)
DEFAULT_TICKER=AAPL
DEFAULT_PERIOD=2y
MAX_OPTIMIZATION_ITERATIONS=4
SANDBOX_TEST_DAYS=90
MIN_TRADES_FOR_VALID_STRATEGY=3
COMMISSION_PCT=0.001
SLIPPAGE_PCT=0.0005
RAG_AUTO_FILL_THRESHOLD=0.85
RAG_TOP_K=5
```

---

*Team Prahari | Hackathon 2026*
