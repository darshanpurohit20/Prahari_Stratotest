# api/routes/health.py
from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health")
def health_check():
    return {"status": "ok", "app": "Prahari Backtesting API", "version": "1.0.0"}
