# frontend/app.py
# Streamlit frontend — calls FastAPI backend
# Run: streamlit run frontend/app.py

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

API_URL = "http://localhost:8000/api/v1"

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Prahari — AI Backtester",
    page_icon="📊",
    layout="wide"
)


# ══════════════════════════════════════════════════════════════
# CHART FUNCTIONS — defined first so they can be called below
# ══════════════════════════════════════════════════════════════

def render_price_chart(data):
    from plotly.subplots import make_subplots
    candles    = data["candles"]
    trades     = data["trades"]
    indicators = data["indicators"]

    # Create subplots: Price (row 1) and Volume (row 2)
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.8, 0.2]
    )

    times  = [c["time"]  for c in candles]
    opens  = [c["open"]  for c in candles]
    highs  = [c["high"]  for c in candles]
    lows   = [c["low"]   for c in candles]
    closs  = [c["close"] for c in candles]
    vols   = [c["volume"] for c in candles]

    # 1. Candlestick
    fig.add_trace(go.Candlestick(
        x=times, open=opens, high=highs, low=lows, close=closs,
        name="Price",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350"
    ), row=1, col=1)

    # 2. Volume Bars
    vol_colors = ["#26a69a" if closs[i] >= opens[i] else "#ef5350" for i in range(len(closs))]
    fig.add_trace(go.Bar(
        x=times, y=vols, 
        name="Volume", 
        marker_color=vol_colors,
        opacity=0.4
    ), row=2, col=1)

    # 3. Indicator lines
    colors = ["#ff9800", "#2196f3", "#9c27b0", "#e91e63"]
    for idx, (name, series) in enumerate(indicators.items()):
        if series:
            fig.add_trace(go.Scatter(
                x   =[s["time"]  for s in series],
                y   =[s["value"] for s in series],
                name=name,
                line=dict(color=colors[idx % len(colors)], width=1.2)
            ), row=1, col=1)

    # 4. Professional Trade Annotations
    if trades:
        for t in trades:
            # Entry
            fig.add_annotation(
                x=t["entry_time"], y=t["entry_price"],
                text="B", showarrow=True, arrowhead=1, ax=0, ay=25,
                bgcolor="#26a69a", font=dict(color="white", size=10),
                row=1, col=1
            )
            # Exit
            color = "#26a69a" if t["result"] == "win" else "#ef5350"
            fig.add_annotation(
                x=t["exit_time"], y=t["exit_price"],
                text="S", showarrow=True, arrowhead=1, ax=0, ay=-25,
                bgcolor=color, font=dict(color="white", size=10),
                row=1, col=1
            )

    fig.update_layout(
        template="plotly_dark",
        height=600,
        xaxis_rangeslider_visible=False,
        title=f"<b>{data['ticker']}</b> | {data['timeframe']} | {data['strategy_name']}",
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    # Hide volume axis labels
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Vol", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)


def render_equity_curve(data):
    curve = data["equity_curve"]
    if not curve:
        st.info("No equity data")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x   =[e["time"]  for e in curve],
        y   =[e["value"] for e in curve],
        fill="tozeroy",
        fillcolor="rgba(38,166,154,0.15)",
        line=dict(color="#26a69a", width=2),
        name="Portfolio Value (Original)"
    ))
    
    # ── Agentic Tweak Comparison ────────────────────────────
    if data.get("optimization_results") and "equity_curve" in data["optimization_results"]:
        opt = data["optimization_results"]
        # Use the same index as original for alignment
        fig.add_trace(go.Scatter(
            x=[e["time"] for e in curve[:len(opt["equity_curve"])]],
            y=opt["equity_curve"],
            line=dict(color="#ffa726", width=2, dash="dot"),
            name="🤖 Agent Tweak (Optimized)"
        ))

    fig.update_layout(
        template="plotly_dark", height=350,
        title="💰 Equity Curve Comparison",
        yaxis_title="Portfolio Value (₹)"
    )

    # Add vbt comparison if available
    vbt = data.get("vbt_analytics")
    if vbt and vbt.get("vbt_equity_curve"):
        veq = vbt["vbt_equity_curve"]
        fig.add_trace(go.Scatter(
            x=[v["time"] for v in veq],
            y=[v["value"] for v in veq],
            line=dict(color="#9e9e9e", width=1, dash="dash"),
            name="vectorbt Engine"
        ))

    st.plotly_chart(fig, use_container_width=True)


def render_drawdown(data):
    curve = data["drawdown_curve"]
    if not curve:
        st.info("No drawdown data")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x   =[e["time"]  for e in curve],
        y   =[e["value"] for e in curve],
        fill="tozeroy",
        fillcolor="rgba(239,83,80,0.2)",
        line=dict(color="#ef5350", width=1.5),
        name="Drawdown %"
    ))
    fig.update_layout(
        template="plotly_dark", height=350,
        title="📉 Drawdown Chart",
        yaxis_title="Drawdown %"
    )
    st.plotly_chart(fig, use_container_width=True)


def render_trade_log(data):
    trades = data["trades"]
    if not trades:
        st.info("No trades generated")
        return
    df = pd.DataFrame(trades)
    df["result"] = df["result"].apply(
        lambda x: "✅ WIN" if x == "win" else "❌ LOSS"
    )
    df["pnl"] = df["pnl"].apply(lambda x: f"₹{x:,.2f}")
    st.dataframe(df[[
        "trade_number", "entry_time", "exit_time",
        "entry_price", "exit_price", "sl_price", "tp_price",
        "result", "pnl", "rr_achieved"
    ]], use_container_width=True)


def render_monte_carlo(data):
    vbt = data.get("vbt_analytics")
    if not vbt or not vbt.get("monte_carlo"):
        st.info("No Monte Carlo simulation data available")
        return

    mc = vbt["monte_carlo"]
    p10, p50, p90 = mc["p10"], mc["p50"], mc["p90"]
    steps = list(range(len(p50)))

    fig = go.Figure()

    # Fill between p10 and p90
    fig.add_trace(go.Scatter(
        x=steps + steps[::-1],
        y=p90 + p10[::-1],
        fill='toself',
        fillcolor='rgba(38,166,154,0.1)',
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo="skip",
        showlegend=False,
        name='P10-P90 Range'
    ))

    fig.add_trace(go.Scatter(x=steps, y=p50, line=dict(color='#26a69a', width=3), name='P50 (Median)'))
    fig.add_trace(go.Scatter(x=steps, y=p90, line=dict(color='#26a69a', width=1, dash='dot'), name='P90 (Best)'))
    fig.add_trace(go.Scatter(x=steps, y=p10, line=dict(color='#ef5350', width=1, dash='dot'), name='P10 (Worst)'))

    fig.update_layout(
        template="plotly_dark", height=400,
        title=f"🎲 Monte Carlo Simulation ({mc['n_sims']} iterations)",
        xaxis_title="Days",
        yaxis_title="Projected Capital (₹)"
    )
    st.plotly_chart(fig, use_container_width=True)


def render_vbt_metrics(data):
    vbt = data.get("vbt_analytics")
    if not vbt:
        return

    st.markdown("### 🧬 Institutional Analytics (Powered by vectorbt)")
    
    # Advanced Metrics Grid
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sortino Ratio", vbt.get("sortino_ratio") or "0.0")
    c2.metric("Profit Factor", vbt.get("profit_factor") or "0.0", help="Gross Profit / Gross Loss")
    c3.metric("Expectancy", f"₹{vbt.get('expectancy', 0):,.2f}")
    c4.metric("Avg Duration", f"{vbt.get('avg_trade_duration', 0)} bars")

    bc1, bc2, bc3, bc4 = st.columns(4)
    bc1.metric("Recovery Factor", vbt.get("recovery_factor") or "0.0", help="Total Profit / Max Drawdown (abs)")
    bc2.metric("Max DD % (vbt)", f"{vbt.get('max_drawdown_pct', 0)}%")
    bc3.metric("Max DD Duration", f"{vbt.get('max_dd_duration', 0)} bars")
    bc4.metric("Omega Ratio", vbt.get("omega_ratio") or "0.0")

    bc1, bc2 = st.columns(2)
    bc1.metric("Best Trade %", f"{vbt.get('best_trade_pct', 0)}%", delta_color="normal")
    bc2.metric("Worst Trade %", f"{vbt.get('worst_trade_pct', 0)}%", delta_color="inverse")


# ══════════════════════════════════════════════════════════════
# MAIN UI
# ══════════════════════════════════════════════════════════════

# ── Header ────────────────────────────────────────────────────
st.markdown("# 📊 Prahari — Agentic AI Backtesting")
st.markdown("*Describe your trading strategy in plain English. Get results in seconds.*")
st.divider()

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛠️ Controls")
    if st.button("🗑️ Clear Chat Session", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["prefill"] = None
        st.rerun()
        
    st.divider()
    st.markdown("### 🚀 Fast Presets")
    st.header("⚙️ Status")
    
    # API status check
    try:
        r = requests.get(f"{API_URL}/health", timeout=2)
        if r.status_code == 200:
            st.success("✅ API Connected")
        else:
            st.error("❌ API Error")
    except:
        st.error("❌ API Offline")

    st.divider()
    st.markdown("**📋 Quick Strategies**")
    st.caption("Click to prefill — edit and submit")

    examples = [
        ("MA Crossover",  "Buy when 50 EMA crosses above 200 EMA, SL below last swing low, 1:2 RR"),
        ("RSI Reversal",  "Buy when RSI drops below 30 and bounces back, SL below swing low, 1:2 RR"),
        ("Order Block",   "Buy at bullish order block, SL below the OB, 1:3 RR"),
        ("FVG Entry",     "Buy when price fills bullish fair value gap, SL below FVG, 1:2 RR"),
    ]

    for label, example in examples:
        if st.button(label, use_container_width=True):
            st.session_state["prefill"] = example

# ── Session state init ────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "prefill" not in st.session_state:
    st.session_state["prefill"] = ""

# ── Display chat history ──────────────────────────────────────
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ── Strategy input ────────────────────────────────────────────
prefill = st.session_state.get("prefill", "")
if prefill:
    st.session_state["prefill"] = ""  # clear after reading

prompt = st.chat_input(
    placeholder="e.g. Buy when 50 EMA crosses above 200 EMA, SL below swing low, 1:2 RR"
)

# Use prefill if a quick button was clicked
if prefill and not prompt:
    prompt = prefill

# ── Run on submit ─────────────────────────────────────────────
if prompt:
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):

        # Merged Step — Run backtest (includes parsing)
        with st.spinner("🤖 AI is analyzing and backtesting your strategy..."):
            try:
                # Concatenate messages for context - but only last few to avoid confusion
                history = st.session_state["messages"][-5:] # Last 5 messages for context
                full_input = "\n".join([f"{m['role']}: {m['content']}" for m in history])
                
                bt_resp = requests.post(
                    f"{API_URL}/backtest",
                    json={
                        "user_input":      full_input,
                        "ticker":          "AUTO",
                        "timeframe":       "1h",
                        "period":          "1y",
                        "initial_capital": 100000,
                        "market":          "india_equity"
                    },
                    timeout=120 
                )
                
                if bt_resp.status_code != 200:
                    st.error(f"Backtest failed: {bt_resp.json().get('detail')}")
                    st.stop()
                
                data = bt_resp.json()
                
                # Handle Clarification Needed (Exit early and rerun)
                if data.get("clarification_needed"):
                    st.session_state["messages"].append({"role": "assistant", "content": data['question']})
                    st.rerun()
                
                # Show parsed rules for transparency
                if data.get("parsed_rules"):
                    with st.expander("📋 AI's Interpretation (Logic Rules)"):
                        st.json(data["parsed_rules"])
                        
            except Exception as e:
                st.error(f"Backtest error: {e}")
                st.stop()

        # ── Results Rendering (Only if NOT clarification) ────────
        if not data.get("metrics"):
            st.info("No backtest results yet. Please provide more details.")
            st.stop()

        # ── Warnings ──────────────────────────────────────────
        for w in data.get("warnings", []):
            st.warning(w)

        # ── Confidence badge ──────────────────────────────────
        conf = data.get("confidence", "medium")
        conf_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(conf, "⚪")
        st.caption(f"{conf_color} Confidence: {data.get('confidence_reason', 'Analysis complete')}")

        # ── Market Environment Intelligence ───────────────────
        if data.get("market_regime"):
            st.markdown(f"""
            <div style="background-color: #001219; border: 1px solid #005f73; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <span style="color: #94d2bd; font-weight: bold; font-size: 0.8em; letter-spacing: 1.2px;">🌐 AI MARKET INTELLIGENCE</span><br/>
                <span style="color: #e9d8a6; font-size: 1.1em; font-weight: 500;">{data['market_regime']}</span>
            </div>
            """, unsafe_allow_html=True)

        # ── AI Strategist Insight ─────────────────────────────
        if data.get("ai_insight"):
            st.markdown(f"""
            <div style="background-color: #1e1e1e; border-left: 5px solid #26a69a; padding: 20px; border-radius: 10px; margin-bottom: 25px;">
                <h4 style='margin-top:0; color:#26a69a;'>💡 Strategist's Take</h4>
                <p style='font-style: italic; color:#e0e0e0; font-size: 1.1em;'>"{data['ai_insight']}"</p>
            </div>
            """, unsafe_allow_html=True)
            
        # ── COMPARATIVE OPTIMIZATION (The Tweak) ──────────────
        if data.get("optimization_results"):
            opt = data["optimization_results"]
            st.markdown(f"""
            <div style="background-color: #0d1b2a; border: 1px solid #415a77; padding: 20px; border-radius: 10px; margin-bottom: 25px;">
                <h4 style='margin-top:0; color:#e0e1dd;'>🤖 Agent Optimization Found</h4>
                <p style='color:#e0e1dd;'>{data.get("optimization_summary", "Better parameters detected.")}</p>
                <div style="display: flex; gap: 20px;">
                    <div>
                        <span style="color:#778da9;">Original Win Rate</span><br/>
                        <span style="font-size: 1.5em; font-weight: bold; color:#e0e0e0;">{m.get('win_rate')}%</span>
                    </div>
                    <div style="font-size: 2em; color:#415a77;">→</div>
                    <div>
                        <span style="color:#1b4332;">Optimized Win Rate</span><br/>
                        <span style="font-size: 1.5em; font-weight: bold; color:#2d6a4f;">{opt['win_rate']}%</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ── Key metrics ───────────────────────────────────────
        st.markdown("### 📊 Performance Summary")
        m = data["metrics"]
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total Trades",  m.get("total_trades", 0))
        c2.metric("Win Rate",      f"{m.get('win_rate', 0)}%")
        c3.metric("Total Return",  f"{m.get('total_return_pct', 0)}%")
        c4.metric("Annual Return", f"{m.get('annual_return_pct', 0)}%")

        c5,c6,c7,c8 = st.columns(4)
        c5.metric("Sharpe Ratio",  m.get("sharpe_ratio", 0))
        c6.metric("Max Drawdown",  f"{m.get('max_drawdown_pct', 0)}%")
        c7.metric("Profit Factor", m.get("profit_factor", 0))
        c8.metric("Avg RR",        m.get("avg_rr_achieved", 0))

        # ── Charts ────────────────────────────────────────────
        st.divider()
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Price Chart", "💰 Equity Curve", "📉 Drawdown", "📋 Trade Log", "🎲 Risk Analysis"
        ])
        with tab1: render_price_chart(data)
        with tab2: render_equity_curve(data)
        with tab3: render_drawdown(data)
        with tab4: render_trade_log(data)
        with tab5: render_monte_carlo(data)

        # ── vectorbt metrics ──────────────────────────────────
        st.divider()
        render_vbt_metrics(data)

        # ── Friction comparison ───────────────────────────────
        st.divider()
        st.markdown("### 🔍 Friction Impact (Reality vs Fantasy)")
        fc1, fc2, fc3 = st.columns(3)
        fc1.metric("Return WITH Friction", f"{m['total_return_pct']}%")
        fc2.metric("Return WITHOUT Friction", f"{m['return_without_friction']}%")
        fc3.metric("Hidden Cost", f"₹{m['total_friction_cost']:,.0f}", 
                   delta=f"-{round(m['return_without_friction'] - m['total_return_pct'], 2)}%", delta_color="inverse")

        # ── Assistant Summary in Chat ─────────────────────────
        summary = (
            f"✅ **{data['strategy_name']}** on {data['ticker']}\n"
            f"📈 Return: **{m['total_return_pct']}%** | Sharpe: **{m['sharpe_ratio']}**"
        )
        st.session_state["messages"].append({"role": "assistant", "content": summary})
        
        st.markdown("##### 💡 Suggested Next Steps")
        ac1, ac2, ac3 = st.columns(3)
        if ac1.button("Try on 15m", key=f"btn_15m_{prompt}"):
            st.session_state["prefill"] = f"{prompt} on 15m timeframe"
            st.rerun()
        if ac2.button("Try on Nifty", key=f"btn_nifty_{prompt}"):
            st.session_state["prefill"] = f"{prompt} on nifty"
            st.rerun()
        if ac3.button("Change Asset", key=f"btn_asset_{prompt}"):
            st.session_state["prefill"] = f"{prompt} but change the asset"
            st.rerun()
