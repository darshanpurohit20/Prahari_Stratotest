import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

API_URL = "http://localhost:8000/api/v1"

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Prahari AI — Agentic Backtesting",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Custom Theme Injection (From your HTML) ─────────────────────
st.markdown("""
<style>
    /* Core palette and fonts */
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
    
    .stApp {
        background-color: #080c18;
        color: #e4e8f5;
        font-family: 'DM Sans', sans-serif;
    }
    /* Hide top header bar & standard padding */
    header[data-testid="stHeader"] { background: rgba(8,12,24,0.92) !important; backdrop-filter: blur(16px); }
    .css-18e3th9, .block-container { padding-top: 5rem !important; }
    
    /* Typography */
    h1, h2, h3 { font-family: 'Space Mono', monospace !important; font-weight: 700 !important; }
    .hero-title {
        font-size: clamp(32px, 6vw, 68px);
        font-weight: 700;
        line-height: 1.1;
        text-align: center;
        color: #e4e8f5;
        font-family: 'Space Mono', monospace;
    }
    .hero-title span {
        background: linear-gradient(135deg, #00d4ff, #5b5ef4 55%, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        text-align: center; color: #6b7494; font-size: 18px; margin-bottom: 40px; max-width: 600px; margin-left: auto; margin-right: auto;
    }
    
    /* Layout & Cards */
    .metric-card {
        background-color: #0c1120; border: 1px solid rgba(255,255,255,0.07);
        border-radius: 12px; padding: 20px; text-align: center; font-family: 'Space Mono', monospace;
    }
    .metric-value { font-size: 32px; font-weight: 700; color: #00d4ff; }
    .metric-label { font-size: 12px; color: #6b7494; text-transform: uppercase; letter-spacing: 1px; }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #5b5ef4, #7c3aed);
        border: none; border-radius: 10px; color: white !important; font-weight: 600; font-family: 'DM Sans', sans-serif;
        padding: 0.5rem 1rem; transition: all 0.2s; width: 100%;
    }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(91,94,244,0.4); }
    
    .logo-hdr { font-family: 'Space Mono', monospace; font-size: 18px; font-weight: 700; color: #00d4ff; letter-spacing: 3px; }
    .logo-hdr span { color: #5b5ef4; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# CHART FUNCTIONS (Intact exactly as Streamlit)
# ══════════════════════════════════════════════════════════════

def render_price_chart(data):
    from plotly.subplots import make_subplots
    candles    = data["candles"]
    trades     = data["trades"]
    indicators = data["indicators"]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])

    times, opens, highs, lows, closs, vols = (
        [c["time"] for c in candles], [c["open"] for c in candles], [c["high"] for c in candles],
        [c["low"] for c in candles], [c["close"] for c in candles], [c["volume"] for c in candles]
    )

    fig.add_trace(go.Candlestick(x=times, open=opens, high=highs, low=lows, close=closs, name="Price", increasing_line_color="#00e5a0", decreasing_line_color="#ff4560"), row=1, col=1)
    
    vol_colors = ["#00e5a0" if closs[i] >= opens[i] else "#ff4560" for i in range(len(closs))]
    fig.add_trace(go.Bar(x=times, y=vols, name="Volume", marker_color=vol_colors, opacity=0.4), row=2, col=1)

    colors = ["#f59e0b", "#5b5ef4", "#00d4ff", "#a855f7"]
    for idx, (name, series) in enumerate(indicators.items()):
        if series:
            fig.add_trace(go.Scatter(x=[s["time"] for s in series], y=[s["value"] for s in series], name=name, line=dict(color=colors[idx % len(colors)], width=1.2)), row=1, col=1)

    if trades:
        for t in trades:
            fig.add_annotation(x=t["entry_time"], y=t["entry_price"], text="B", showarrow=True, arrowhead=1, ax=0, ay=25, bgcolor="#00e5a0", font=dict(color="black", size=10), row=1, col=1)
            color = "#00e5a0" if t["result"] == "win" else "#ff4560"
            fig.add_annotation(x=t["exit_time"], y=t["exit_price"], text="S", showarrow=True, arrowhead=1, ax=0, ay=-25, bgcolor=color, font=dict(color="white", size=10), row=1, col=1)

    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, title=f"<span style='color:#00d4ff'>{data['ticker']}</span> | {data['timeframe']}", margin=dict(l=10, r=10, t=50, b=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

def render_equity_curve(data):
    curve = data["equity_curve"]
    if not curve: return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[e["time"] for e in curve], y=[e["value"] for e in curve], fill="tozeroy", fillcolor="rgba(0,229,160,0.15)", line=dict(color="#00e5a0", width=2), name="Strategy Value"))
    fig.update_layout(template="plotly_dark", height=350, title="Equity Curve", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

def render_drawdown(data):
    curve = data["drawdown_curve"]
    if not curve: return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[e["time"] for e in curve], y=[e["value"] for e in curve], fill="tozeroy", fillcolor="rgba(255,69,96,0.2)", line=dict(color="#ff4560", width=1.5), name="Drawdown %"))
    fig.update_layout(template="plotly_dark", height=350, title="Drawdown Curve", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# APP STATE
# ══════════════════════════════════════════════════════════════
if "messages" not in st.session_state:
    st.session_state.messages = []
if "prefill" not in st.session_state:
    st.session_state.prefill = ""

# Top banner
st.markdown("<div class='logo-hdr'>PRAHARI<span>.</span>AI ⚡</div>", unsafe_allow_html=True)
st.divider()

# ══════════════════════════════════════════════════════════════
# DASHBOARD — single page, no landing form
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="hero-title">Backtest any strategy<br>in <span>plain English</span></div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Describe your strategy — ticker, market & settings are detected automatically by the AI.</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.markdown("<div class='metric-card'><div class='metric-value'>2.8M+</div><div class='metric-label'>Backtests</div></div>", unsafe_allow_html=True)
c2.markdown("<div class='metric-card'><div class='metric-value'>300+</div><div class='metric-label'>Instruments</div></div>", unsafe_allow_html=True)
c3.markdown("<div class='metric-card'><div class='metric-value'><4s</div><div class='metric-label'>Avg Time</div></div>", unsafe_allow_html=True)
c4.markdown("<div class='metric-card'><div class='metric-value'>10Y</div><div class='metric-label'>Data Depth</div></div>", unsafe_allow_html=True)

st.write("")

if True:
    st.sidebar.markdown("### 🛠️ Controls")
    if st.sidebar.button("🗑️ Clear Chat Session", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
        
    st.sidebar.divider()
    st.sidebar.markdown("### 🧩 Universal DSL")
    st.sidebar.caption("Indicators: ma, rsi, sma, close, atr, fvg, ob")
    st.sidebar.caption("Logic: AND/OR with gt, lt, gte, lte, eq, crosses_above, crosses_below")

    st.sidebar.divider()
    st.sidebar.markdown("### 🚀 Fast Presets")
    examples = [
        {
            "label": "MA Crossover",
            "prompt": "Backtest BTC where EMA 50 crosses above EMA 200, stop loss swing_low lookback 5, take profit 1:2",
            "description": "EMA 50/200 bullish crossover with swing-low stop and 1:2 risk-reward.",
        },
        {
            "label": "RSI Reversal",
            "prompt": "Backtest Nifty: buy when RSI 14 is below 30 and then rises, stop loss swing_low, take profit 1:2",
            "description": "RSI oversold reversal setup with confirmation and fixed 1:2 target.",
        },
        {
            "label": "Fibonacci Pullback",
            "prompt": "Backtest ETH bullish pullback to Fibonacci 0.618 with trend continuation, stop loss swing_low, take profit 1:2",
            "description": "Trend continuation entry on 0.618 pullback zone.",
        },
        {
            "label": "SR Bounce",
            "prompt": "Backtest RELIANCE support bounce setup near recent support with bullish close confirmation",
            "description": "Support touch-and-bounce with bullish close confirmation.",
        },
        {
            "label": "Breakout Retest",
            "prompt": "Backtest Nifty breakout and retest strategy: resistance break then successful retest and continuation",
            "description": "Breakout above resistance followed by retest continuation entry.",
        },
    ]
    for item in examples:
        if st.sidebar.button(item["label"], use_container_width=True, help=item["description"]):
            st.session_state.prefill = item["prompt"]

    st.sidebar.divider()
    st.sidebar.markdown("### 🧠 Direct Analyses")
    direct_analyses = [
        {
            "label": "HHHL Trend",
            "prompt": "Analyze and backtest BTC higher-high higher-low trend continuation logic on 1h timeframe",
            "description": "Trend-structure analysis using higher highs and higher lows.",
        },
        {
            "label": "Order Block",
            "prompt": "Analyze and backtest Gold bullish order block entry when price revisits OB and closes strong",
            "description": "SMC order block revisit with bullish confirmation.",
        },
        {
            "label": "FVG Fill",
            "prompt": "Analyze and backtest ETH bullish fair value gap entry with confirmation candle",
            "description": "Fair Value Gap fill-and-go setup with confirmation.",
        },
        {
            "label": "CHoCH",
            "prompt": "Analyze and backtest Nifty bullish CHoCH setup after downtrend structure break",
            "description": "Change-of-character bullish reversal after bearish structure break.",
        },
        {
            "label": "BOS Pullback",
            "prompt": "Analyze and backtest BTC break of structure then pullback continuation entry",
            "description": "Break of structure followed by pullback continuation setup.",
        },
    ]
    for item in direct_analyses:
        if st.sidebar.button(item["label"], use_container_width=True, help=item["description"]):
            st.session_state.prefill = item["prompt"]

    # Display Chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    prefill = st.session_state.get("prefill", "")
    if prefill:
        st.session_state.prefill = ""

    prompt = st.chat_input(placeholder='e.g. "Buy when the 50 MA crosses above 200 MA, 2% SL"')
    if prefill and not prompt:
        prompt = prefill

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🤖 Agentic AI is building & running strategy..."):
                try:
                    history = st.session_state["messages"][-5:]
                    full_input = "\n".join([f"{m['role']}: {m['content']}" for m in history])
                    
                    bt_resp = requests.post(f"{API_URL}/backtest", json={
                            "user_input": full_input,
                            "ticker": "AUTO",
                            "timeframe": "1h",
                            "period": "1y",
                            "initial_capital": 100000,
                            "market": "india_equity"
                        }, timeout=120)
                    
                    if bt_resp.status_code != 200:
                        st.error(f"Backtest failed: {bt_resp.json().get('detail')}")
                        st.stop()
                    data = bt_resp.json()
                    
                    if data.get("clarification_needed"):
                        st.session_state.messages.append({"role": "assistant", "content": data['question']})
                        st.rerun()

                except Exception as e:
                    st.error(f"Backend offline or err: {e}")
                    st.stop()

            if not data.get("metrics"):
                st.info("No stats. Enter refinement.")
                st.stop()
                
            # Key metrics header
            m = data["metrics"]
            st.markdown("### 📊 Performance Tearsheet")
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"<div class='metric-card' style='border-color: #00e5a0;'><div class='metric-value' style='color:#00e5a0;'>{m.get('total_return_pct', 0)}%</div><div class='metric-label'>Total Return</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card' style='border-color: #00d4ff;'><div class='metric-value' style='color:#00d4ff;'>{m.get('sharpe_ratio', 0)}</div><div class='metric-label'>Sharpe Ratio</div></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-card' style='border-color: #ff4560;'><div class='metric-value' style='color:#ff4560;'>{m.get('max_drawdown_pct', 0)}%</div><div class='metric-label'>Max Drawdown</div></div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='metric-card' style='border-color: #f59e0b;'><div class='metric-value' style='color:#f59e0b;'>{m.get('win_rate', 0)}%</div><div class='metric-label'>Win Rate</div></div>", unsafe_allow_html=True)

            st.write("")
            tab1, tab2, tab3 = st.tabs(["📈 Price & Sub-Charts", "💰 Equity & Risk", "📋 Trade Log"])
            with tab1: render_price_chart(data)
            with tab2: 
                render_equity_curve(data)
                render_drawdown(data)
            with tab3:
                df = pd.DataFrame(data["trades"])
                if not df.empty:
                    st.dataframe(df[["entry_time", "exit_time", "result", "pnl", "rr_achieved"]], use_container_width=True)

            summary = f"✅ Tested **{data['strategy_name']}** on **{data['ticker']}**. Return: {m['total_return_pct']}%."
            st.session_state.messages.append({"role": "assistant", "content": summary})
