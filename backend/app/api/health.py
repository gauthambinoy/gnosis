import os
import time

from fastapi import APIRouter
from app.core.redis_client import redis_manager
from app.core.database import engine, db_available
from app.core.task_worker import task_worker
from app.config import get_settings
from sqlalchemy import text

router = APIRouter(tags=["health"])

_start_time = time.time()
_settings = get_settings()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "gnosis", "version": "1.0.0"}


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
    return {"alive": True}


@router.get("/health/detailed")
async def detailed():
    """Full system info: uptime, route count, memory, DB pool stats."""
    import resource

    uptime_seconds = time.time() - _start_time

    # Memory usage (RSS in MB)
    rusage = resource.getrusage(resource.RUSAGE_SELF)
    memory_mb = rusage.ru_maxrss / 1024  # Linux reports KB

    # DB pool stats (only meaningful for a real pooled engine)
    pool_stats: dict = {}
    try:
        pool = engine.pool
        pool_stats = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }
    except Exception:
        pool_stats = {"status": "unavailable"}

    # Route count
    from app.main import app as _app  # local import to avoid circulars

    route_count = len(_app.routes)

    return {
        "status": "ok",
        "version": _settings.app_version,
        "uptime_seconds": round(uptime_seconds, 2),
        "route_count": route_count,
        "memory_mb": round(memory_mb, 2),
        "db_pool": pool_stats,
    }
