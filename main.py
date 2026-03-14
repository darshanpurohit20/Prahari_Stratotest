# main.py — Prahari Agentic Backtesting API
# Entry point for FastAPI application

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import backtest, strategy, health

app = FastAPI(
    title="Prahari — Agentic AI Backtesting",
    description="Natural language trading strategy backtester for Indian markets",
    version="1.0.0"
)

# Allow frontend (Streamlit or any UI) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routes
app.include_router(health.router,    prefix="/api/v1")
app.include_router(strategy.router,  prefix="/api/v1")
app.include_router(backtest.router,  prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
