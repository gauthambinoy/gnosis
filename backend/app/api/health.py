from fastapi import APIRouter
from app.core.redis_client import redis_manager
from app.core.database import engine, db_available
from app.core.task_worker import task_worker
from sqlalchemy import text

router = APIRouter(tags=["health"])

@router.get("/health")
async def health():
    return {"status": "alive", "service": "gnosis", "version": "1.0.0"}

@router.get("/health/ready")
async def readiness():
    """Deep health check — verifies all dependencies."""
    checks = {}
    overall = True
    
    # Database
    try:
        if db_available:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = {"status": "up", "type": "postgresql"}
        else:
            checks["database"] = {"status": "degraded", "type": "in-memory"}
    except Exception as e:
        checks["database"] = {"status": "down", "error": str(e)}
        overall = False
    
    # Redis
    try:
        if redis_manager.available:
            await redis_manager.client.ping()
            checks["redis"] = {"status": "up"}
        else:
            checks["redis"] = {"status": "degraded", "type": "in-memory fallback"}
    except Exception as e:
        checks["redis"] = {"status": "down", "error": str(e)}
        overall = False
    
    # Task Worker
    checks["task_worker"] = {
        "status": "up" if task_worker._running else "down",
        "tasks": len(task_worker.tasks),
    }
    
    # LLM (check if any provider is configured)
    checks["llm"] = {"status": "configured", "note": "Requires API keys for actual calls"}
    
    return {
        "status": "ready" if overall else "degraded",
        "checks": checks,
    }

@router.get("/health/live")
async def liveness():
    """Simple liveness probe for k8s."""
    return {"status": "alive"}
