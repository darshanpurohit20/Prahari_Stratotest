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

def render_trade_log(data):
    trades = data.get("trades", [])
    if not trades:
        st.info("No trades generated")
        return

    df = pd.DataFrame(trades)
    cols = ["trade_number", "entry_time", "exit_time", "entry_price", "exit_price", "sl_price", "tp_price", "result", "pnl", "rr_achieved"]
    available = [c for c in cols if c in df.columns]
    st.dataframe(df[available], use_container_width=True)

def render_monte_carlo(data):
    vbt = data.get("vbt_analytics")
    if not vbt or not vbt.get("monte_carlo"):
        st.info("No Monte Carlo simulation data available")
        return

    mc = vbt["monte_carlo"]
    p10, p50, p90 = mc["p10"], mc["p50"], mc["p90"]
    steps = list(range(len(p50)))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=steps + steps[::-1],
        y=p90 + p10[::-1],
        fill="toself",
        fillcolor="rgba(0,229,160,0.1)",
        line=dict(color="rgba(255,255,255,0)"),
        hoverinfo="skip",
        showlegend=False,
        name="P10-P90 Range"
    ))
    fig.add_trace(go.Scatter(x=steps, y=p50, line=dict(color="#00e5a0", width=3), name="P50 (Median)"))
    fig.add_trace(go.Scatter(x=steps, y=p90, line=dict(color="#00e5a0", width=1, dash="dot"), name="P90 (Best)"))
    fig.add_trace(go.Scatter(x=steps, y=p10, line=dict(color="#ff4560", width=1, dash="dot"), name="P10 (Worst)"))

    fig.update_layout(
        template="plotly_dark",
        height=400,
        title=f"Monte Carlo Simulation ({mc['n_sims']} iterations)",
        xaxis_title="Steps",
        yaxis_title="Projected Capital"
    )
    st.plotly_chart(fig, use_container_width=True)

def render_vbt_metrics(data):
    vbt = data.get("vbt_analytics")
    if not vbt:
        return

    st.markdown("### Institutional Analytics (vectorbt)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sortino Ratio", vbt.get("sortino_ratio") or "0.0")
    c2.metric("Profit Factor", vbt.get("profit_factor") or "0.0")
    c3.metric("Expectancy", f"{vbt.get('expectancy', 0):,.2f}")
    c4.metric("Avg Duration", f"{vbt.get('avg_trade_duration', 0)} bars")

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Recovery Factor", vbt.get("recovery_factor") or "0.0")
    b2.metric("Max DD % (vbt)", f"{vbt.get('max_drawdown_pct', 0)}%")
    b3.metric("Max DD Duration", f"{vbt.get('max_dd_duration', 0)} bars")
    b4.metric("Omega Ratio", vbt.get("omega_ratio") or "0.0")

# ══════════════════════════════════════════════════════════════
# APP STATE
# ══════════════════════════════════════════════════════════════
if "messages" not in st.session_state:
    st.session_state.messages = []
if "prefill" not in st.session_state:
    st.session_state.prefill = ""
if "context_asset" not in st.session_state:
    st.session_state.context_asset = "Nifty 50"


def build_context_prompt(template: str) -> str:
    asset = st.session_state.get("context_asset", "Nifty 50")
    return template.format(asset=asset)

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
            "prompt": "Backtest {asset} where EMA 50 crosses above EMA 200, stop loss swing_low lookback 5, take profit 1:2",
            "description": "EMA 50/200 bullish crossover with swing-low stop and 1:2 risk-reward.",
        },
        {
            "label": "RSI Reversal",
            "prompt": "Backtest {asset}: buy when RSI 14 is below 30 and then rises, stop loss swing_low, take profit 1:2",
            "description": "RSI oversold reversal setup with confirmation and fixed 1:2 target.",
        },
        {
            "label": "Fibonacci Pullback",
            "prompt": "Backtest {asset} bullish pullback to Fibonacci 0.618 with trend continuation, stop loss swing_low, take profit 1:2",
            "description": "Trend continuation entry on 0.618 pullback zone.",
        },
        {
            "label": "SR Bounce",
            "prompt": "Backtest {asset} support bounce setup near recent support with bullish close confirmation",
            "description": "Support touch-and-bounce with bullish close confirmation.",
        },
        {
            "label": "Breakout Retest",
            "prompt": "Backtest {asset} breakout and retest strategy: resistance break then successful retest and continuation",
            "description": "Breakout above resistance followed by retest continuation entry.",
        },
    ]
    for item in examples:
        if st.sidebar.button(item["label"], use_container_width=True, help=item["description"]):
            st.session_state.prefill = build_context_prompt(item["prompt"])

    st.sidebar.divider()
    st.sidebar.markdown("### 🧠 Direct Analyses")
    direct_analyses = [
        {
            "label": "HHHL Trend",
            "prompt": "Analyze and backtest {asset} higher-high higher-low trend continuation logic on 1h timeframe",
            "description": "Trend-structure analysis using higher highs and higher lows.",
        },
        {
            "label": "Order Block",
            "prompt": "Analyze and backtest {asset} bullish order block entry when price revisits OB and closes strong",
            "description": "SMC order block revisit with bullish confirmation.",
        },
        {
            "label": "FVG Fill",
            "prompt": "Analyze and backtest {asset} bullish fair value gap entry with confirmation candle",
            "description": "Fair Value Gap fill-and-go setup with confirmation.",
        },
        {
            "label": "CHoCH",
            "prompt": "Analyze and backtest {asset} bullish CHoCH setup after downtrend structure break",
            "description": "Change-of-character bullish reversal after bearish structure break.",
        },
        {
            "label": "BOS Pullback",
            "prompt": "Analyze and backtest {asset} break of structure then pullback continuation entry",
            "description": "Break of structure followed by pullback continuation setup.",
        },
    ]
    for item in direct_analyses:
        if st.sidebar.button(item["label"], use_container_width=True, help=item["description"]):
            st.session_state.prefill = build_context_prompt(item["prompt"])

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
                    st.session_state.context_asset = data.get("ticker_name") or data.get("ticker") or st.session_state.context_asset
                    
                    if data.get("clarification_needed"):
                        st.session_state.messages.append({"role": "assistant", "content": data['question']})
                        st.rerun()

                except Exception as e:
                    st.error(f"Backend offline or err: {e}")
                    st.stop()

            if not data.get("metrics"):
                st.info("No stats. Enter refinement.")
                st.stop()

            m = data["metrics"]

            # Warnings
            for w in data.get("warnings", []):
                st.warning(w)

            # Confidence badge
            conf = data.get("confidence", "medium")
            conf_color = {"high": "Green", "medium": "Orange", "low": "Red"}.get(conf, "Gray")
            st.markdown(f"<span style='color:{conf_color}'>Confidence:</span> {data.get('confidence_reason', 'Analysis complete')}", unsafe_allow_html=True)

            # Market intelligence
            if data.get("market_regime"):
                st.markdown(f"""
                <div style="background-color: #0b132b; border: 1px solid #1c2541; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <span style="color: #5bc0be; font-weight: bold; letter-spacing: 1px;">AI MARKET INTELLIGENCE</span><br/>
                    <span style="color: #e4e8f5; font-size: 1.05em;">{data['market_regime']}</span>
                </div>
                """, unsafe_allow_html=True)

            # AI Strategist Insight
            if data.get("ai_insight"):
                st.markdown(f"""
                <div style="background-color: #1e1e1e; border-left: 5px solid #00d4ff; padding: 16px; border-radius: 10px; margin-bottom: 20px;">
                    <h4 style='margin-top:0; color:#00d4ff;'>Strategist's Take</h4>
                    <p style='color:#e0e0e0; font-size: 1.05em;'>\"{data['ai_insight']}\"</p>
                </div>
                """, unsafe_allow_html=True)

            # Optimization comparison
            if data.get("optimization_results"):
                opt = data["optimization_results"]
                st.markdown(f"""
                <div style="background-color: #0d1b2a; border: 1px solid #415a77; padding: 16px; border-radius: 10px; margin-bottom: 20px;">
                    <h4 style='margin-top:0; color:#e0e1dd;'>Agent Optimization Found</h4>
                    <p style='color:#e0e1dd;'>{data.get("optimization_summary", "Better parameters detected.")}</p>
                    <div style="display: flex; gap: 18px; align-items: center;">
                        <div><span style="color:#778da9;">Original Win Rate</span><br/><span style="font-size: 1.3em; font-weight: bold; color:#e0e0e0;">{m.get('win_rate')}%</span></div>
                        <div style="font-size: 1.8em; color:#415a77;">→</div>
                        <div><span style="color:#1b4332;">Optimized Win Rate</span><br/><span style="font-size: 1.3em; font-weight: bold; color:#2d6a4f;">{opt.get('win_rate', 0)}%</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Key metrics header
            st.markdown("### 📊 Performance Tearsheet")
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"<div class='metric-card' style='border-color: #00e5a0;'><div class='metric-value' style='color:#00e5a0;'>{m.get('total_return_pct', 0)}%</div><div class='metric-label'>Total Return</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card' style='border-color: #00d4ff;'><div class='metric-value' style='color:#00d4ff;'>{m.get('sharpe_ratio', 0)}</div><div class='metric-label'>Sharpe Ratio</div></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-card' style='border-color: #ff4560;'><div class='metric-value' style='color:#ff4560;'>{m.get('max_drawdown_pct', 0)}%</div><div class='metric-label'>Max Drawdown</div></div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='metric-card' style='border-color: #f59e0b;'><div class='metric-value' style='color:#f59e0b;'>{m.get('win_rate', 0)}%</div><div class='metric-label'>Win Rate</div></div>", unsafe_allow_html=True)

            d1, d2, d3, d4 = st.columns(4)
            d1.markdown(f"<div class='metric-card'><div class='metric-value'>{m.get('total_trades', 0)}</div><div class='metric-label'>Total Trades</div></div>", unsafe_allow_html=True)
            d2.markdown(f"<div class='metric-card'><div class='metric-value'>{m.get('annual_return_pct', 0)}%</div><div class='metric-label'>Annual Return</div></div>", unsafe_allow_html=True)
            d3.markdown(f"<div class='metric-card'><div class='metric-value'>{m.get('profit_factor', 0)}</div><div class='metric-label'>Profit Factor</div></div>", unsafe_allow_html=True)
            d4.markdown(f"<div class='metric-card'><div class='metric-value'>{m.get('avg_rr_achieved', 0)}</div><div class='metric-label'>Avg RR</div></div>", unsafe_allow_html=True)

            st.write("")
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Price & Sub-Charts", "💰 Equity & Risk", "📉 Drawdown", "📋 Trade Log", "🎲 Risk Analysis"])
            with tab1: render_price_chart(data)
            with tab2: render_equity_curve(data)
            with tab3: render_drawdown(data)
            with tab4: render_trade_log(data)
            with tab5: render_monte_carlo(data)

            st.divider()
            render_vbt_metrics(data)

            st.divider()
            st.markdown("### 🔍 Friction Impact")
            fc1, fc2, fc3 = st.columns(3)
            fc1.metric("Return WITH Friction", f"{m.get('total_return_pct', 0)}%")
            fc2.metric("Return WITHOUT Friction", f"{m.get('return_without_friction', 0)}%")
            hidden_cost = m.get("total_friction_cost", 0)
            hidden_delta = round(m.get("return_without_friction", 0) - m.get("total_return_pct", 0), 2)
            fc3.metric("Hidden Cost", f"₹{hidden_cost:,.0f}", delta=f"-{hidden_delta}%", delta_color="inverse")

            summary = f"✅ Tested **{data['strategy_name']}** on **{data['ticker']}**. Return: {m['total_return_pct']}%."
            st.session_state.messages.append({"role": "assistant", "content": summary})

            st.markdown("##### 💡 Suggested Next Steps")
            ac1, ac2, ac3 = st.columns(3)
            if ac1.button("Try on 15m", key=f"btn_15m_{prompt}"):
                st.session_state.prefill = f"{prompt} on 15m timeframe"
                st.rerun()
            if ac2.button("Try on Nifty", key=f"btn_nifty_{prompt}"):
                st.session_state.prefill = f"{prompt} on nifty"
                st.rerun()
            if ac3.button("Change Asset", key=f"btn_asset_{prompt}"):
                st.session_state.prefill = f"{prompt} but change the asset"
                st.rerun()
