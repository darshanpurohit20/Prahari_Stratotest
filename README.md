# Prahari — Agentic AI Backtesting Tool
> Describe your trading strategy in plain English. Get a full backtest in seconds.

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Add your API key
Edit `.env` file:
```
ANTHROPIC_API_KEY=your_key_here
```
Get free key at: https://console.anthropic.com/

### 3. Start FastAPI backend
```bash
uvicorn main:app --reload --port 8000
```

### 4. Start Streamlit frontend (new terminal)
```bash
streamlit run frontend/app.py
```

### 5. Open browser
- Frontend: http://localhost:8501
- API Docs: http://localhost:8000/docs

---

## 📁 Project Structure
```
prahari/
├── main.py                        ← FastAPI entry point
├── requirements.txt
├── .env                           ← API keys
├── api/
│   ├── models/
│   │   ├── request.py             ← Input validation
│   │   └── response.py            ← Output structure
│   └── routes/
│       ├── backtest.py            ← POST /backtest
│       ├── strategy.py            ← GET /strategies
│       └── health.py              ← GET /health
├── agent/
│   ├── parser.py                  ← Claude LLM parser
│   └── prompts.py                 ← System prompts
├── engine/
│   ├── data.py                    ← yfinance data fetcher
│   ├── friction.py                ← Cost modelling
│   ├── backtester.py              ← Strategy router
│   ├── tearsheet.py               ← Metrics + chart data
│   └── strategies/
│       ├── base.py                ← Base class
│       ├── ma_crossover.py        ← Strategy 1
│       ├── rsi_reversal.py        ← Strategy 2
│       ├── fibonacci_pullback.py  ← Strategy 3
│       └── strategies.py         ← Strategies 4-10
└── frontend/
    └── app.py                     ← Streamlit UI
```

---

## 🎯 Supported Strategies

### Classic
1. MA / EMA Crossover
2. RSI Reversal
3. Fibonacci Pullback
4. Support / Resistance Bounce
5. Breakout + Retest
6. Higher High Higher Low

### SMC (Smart Money Concepts)
7. Order Block Entry
8. Fair Value Gap (FVG)
9. Change of Character (CHoCH)
10. Break of Structure + Pullback

---

## 💬 Example Inputs

```
"Buy when 50 EMA crosses above 200 EMA, SL below last swing low, 1:2 RR"
"Buy at bullish order block, SL below OB, 1:3 RR"
"Buy when RSI drops below 30, SL below swing low, 1:2 RR"
"Buy at 0.618 fibonacci level in uptrend, 1:2 RR"
"Buy after break of structure pullback, SL below BOS, 1:3 RR"
```

---

## ➕ Adding New Strategies

1. Create `engine/strategies/my_strategy.py`
2. Inherit `BaseStrategy`
3. Implement `generate_signals()` and `get_indicators()`
4. Add to `STRATEGY_MAP` in `engine/backtester.py`
5. Add to `GET /strategies` in `api/routes/strategy.py`

That's it — no other changes needed!

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

*Team Prahari | Hackathon 2026*
