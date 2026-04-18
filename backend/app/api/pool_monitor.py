"""Connection pool health monitor API."""

from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user_id
from app.core.pool_monitor import pool_monitor
from dataclasses import asdict

router = APIRouter()


@router.get("")
async def get_all_pool_health(user_id: str = Depends(get_current_user_id)):
    pools = pool_monitor.get_all_pools()
    return {"pools": [asdict(p) for p in pools]}


@router.get("/{pool_name}")
async def get_pool_health(pool_name: str, user_id: str = Depends(get_current_user_id)):
    if pool_name == "database":
        health = pool_monitor.check_db_pool()
    elif pool_name == "redis":
        health = pool_monitor.check_redis_pool()
    else:
        raise HTTPException(status_code=404, detail=f"Unknown pool: {pool_name}")
    return asdict(health)
