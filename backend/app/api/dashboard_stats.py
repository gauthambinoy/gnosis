"""Aggregated dashboard stats endpoint."""
from fastapi import APIRouter, Depends
from app.core.auth import get_current_user_id
import logging

logger = logging.getLogger("gnosis.dashboard")

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

@router.get("/stats")
async def get_dashboard_stats(user_id: str = Depends(get_current_user_id)):
    """Aggregated stats for the main dashboard."""
    stats = {
        "agents": {"total": 0, "active": 0, "paused": 0, "error": 0},
        "executions": {"today": 0, "running": 0, "success_rate": 0.0},
        "memory": {"total_entries": 0},
        "files": {"total": 0, "total_size_mb": 0},
        "pipelines": {"total": 0, "active": 0},
        "system": {"uptime_seconds": 0},
    }

    try:
        from app.core.marketplace import marketplace_engine
        agents = list(marketplace_engine._agents.values())
        stats["agents"]["total"] = len(agents)
        for a in agents:
            status = getattr(a, "status", a.get("status", "")) if isinstance(a, dict) else getattr(a, "status", "")
            if status == "active":
                stats["agents"]["active"] += 1
            elif status == "paused":
                stats["agents"]["paused"] += 1
            elif status == "error":
                stats["agents"]["error"] += 1
    except Exception:
        pass

    try:
        from app.core.file_manager import file_manager
        file_stats = file_manager.stats
        stats["files"]["total"] = file_stats.get("total_files", 0)
        stats["files"]["total_size_mb"] = file_stats.get("total_size_mb", 0)
    except Exception:
        pass

    try:
        from app.core.pipeline import pipeline_engine
        pipelines = list(pipeline_engine._pipelines.values())
        stats["pipelines"]["total"] = len(pipelines)
        stats["pipelines"]["active"] = sum(1 for p in pipelines if p.status.value == "active")
    except Exception:
        pass

    return stats

@router.get("/health")
async def dashboard_health(user_id: str = Depends(get_current_user_id)):
    """Quick health check of all subsystems."""
    checks = {}

    try:
        from app.core.redis_client import redis_manager
        if redis_manager._client:
            await redis_manager._client.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "not_connected"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:50]}"

    try:
        from app.core.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:50]}"

    checks["api"] = "ok"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "healthy" if all_ok else "degraded", "checks": checks}
