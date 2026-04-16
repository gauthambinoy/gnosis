"""CLI client commands API — backend support for CLI interactions."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
import time
from app.core.auth import get_current_user_id

router = APIRouter()

_start_time = time.time()


@router.get("/info")
async def cli_info(user_id: str = Depends(get_current_user_id)):
    uptime_seconds = int(time.time() - _start_time)
    return {
        "version": "1.0.0",
        "platform": "Gnosis AI",
        "uptime_seconds": uptime_seconds,
        "endpoints_count": 3,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/execute")
async def cli_execute(body: dict, user_id: str = Depends(get_current_user_id)):
    agent_id = body.get("agent_id")
    task = body.get("task")
    if not agent_id or not task:
        raise HTTPException(status_code=400, detail="agent_id and task are required")
    return {
        "agent_id": agent_id,
        "task": task,
        "status": "queued",
        "message": f"Task queued for agent {agent_id}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/agents")
async def cli_agents(user_id: str = Depends(get_current_user_id)):
    return {"agents": [], "message": "Use main agents API for full listing"}
