import os
import time

import psutil
from fastapi import APIRouter
from fastapi.responses import JSONResponse
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
    """Deep health check — verifies all dependencies. Returns 503 if any critical component is down."""
    checks = {}
    has_critical_down = False

    # Database (critical)
    try:
        if db_available:
            start = time.time()
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            latency = round((time.time() - start) * 1000, 2)
            checks["database"] = {"status": "ok", "latency_ms": latency, "type": "postgresql"}
        else:
            checks["database"] = {"status": "degraded", "latency_ms": 0, "type": "in-memory"}
    except Exception as e:
        checks["database"] = {"status": "down", "latency_ms": 0, "error": str(e)}
        has_critical_down = True

    # Redis (critical)
    try:
        if redis_manager.available:
            start = time.time()
            await redis_manager.client.ping()
            latency = round((time.time() - start) * 1000, 2)
            checks["redis"] = {"status": "ok", "latency_ms": latency}
        else:
            checks["redis"] = {"status": "degraded", "latency_ms": 0, "type": "in-memory fallback"}
    except Exception as e:
        checks["redis"] = {"status": "down", "latency_ms": 0, "error": str(e)}
        has_critical_down = True

    # FAISS
    try:
        from app.core.memory_engine import memory_engine
        checks["faiss"] = {"status": "ok", "latency_ms": 0} if memory_engine else {"status": "degraded", "latency_ms": 0}
    except Exception:
        checks["faiss"] = {"status": "degraded", "latency_ms": 0, "note": "not loaded"}

    # Disk
    disk = psutil.disk_usage("/")
    disk_pct = disk.percent
    checks["disk"] = {
        "status": "ok" if disk_pct < 85 else "degraded" if disk_pct < 95 else "down",
        "latency_ms": 0,
        "used_percent": disk_pct,
        "free_gb": round(disk.free / (1024**3), 2),
    }
    if checks["disk"]["status"] == "down":
        has_critical_down = True

    # Task Worker
    checks["task_worker"] = {
        "status": "ok" if task_worker._running else "down",
        "latency_ms": 0,
        "tasks": len(task_worker.tasks),
    }
    if not task_worker._running:
        has_critical_down = True

    # LLM provider
    checks["llm"] = {"status": "ok", "latency_ms": 0, "note": "Requires API keys for actual calls"}

    overall = "down" if has_critical_down else (
        "degraded" if any(c["status"] == "degraded" for c in checks.values()) else "ready"
    )
    status_code = 503 if has_critical_down else 200

    return JSONResponse(
        content={"status": overall, "checks": checks},
        status_code=status_code,
    )


@router.get("/health/live")
async def liveness():
    """Simple liveness probe for k8s — always returns 200."""
    return {"status": "alive"}


@router.get("/health/deep")
async def deep_health():
    """Component-level health with latency measurements."""
    checks = {}

    # Database
    try:
        if db_available:
            start = time.time()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = {"status": "ok", "latency_ms": round((time.time() - start) * 1000, 2)}
        else:
            checks["database"] = {"status": "degraded", "latency_ms": 0, "note": "in-memory mode"}
    except Exception as e:
        checks["database"] = {"status": "down", "latency_ms": 0, "error": type(e).__name__}

    # Redis
    try:
        if redis_manager.available:
            start = time.time()
            await redis_manager.client.ping()
            checks["redis"] = {"status": "ok", "latency_ms": round((time.time() - start) * 1000, 2)}
        else:
            checks["redis"] = {"status": "degraded", "latency_ms": 0, "note": "in-memory fallback"}
    except Exception as e:
        checks["redis"] = {"status": "down", "latency_ms": 0, "error": type(e).__name__}

    # Disk
    disk = psutil.disk_usage("/")
    disk_pct = disk.percent
    checks["disk"] = {
        "status": "ok" if disk_pct < 85 else "degraded" if disk_pct < 95 else "down",
        "used_percent": disk_pct,
        "free_gb": round(disk.free / (1024**3), 2),
    }

    # Memory
    mem = psutil.virtual_memory()
    checks["memory"] = {
        "status": "ok" if mem.percent < 85 else "degraded",
        "used_percent": mem.percent,
        "available_gb": round(mem.available / (1024**3), 2),
    }

    # FAISS
    try:
        from app.core.memory_engine import memory_engine
        checks["faiss"] = {"status": "ok" if memory_engine else "degraded"}
    except Exception:
        checks["faiss"] = {"status": "degraded", "note": "not loaded"}

    # LLM provider reachable (lightweight check — config only)
    checks["llm"] = {"status": "ok", "note": "configured"}

    overall = "ok"
    if any(c["status"] == "down" for c in checks.values()):
        overall = "down"
    elif any(c["status"] == "degraded" for c in checks.values()):
        overall = "degraded"

    status_code = 200 if overall != "down" else 503
    return JSONResponse(
        content={"status": overall, "service": "gnosis", "version": "1.0.0", "checks": checks},
        status_code=status_code,
    )


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
