"""Memory garbage collection API."""

from fastapi import APIRouter, Depends
from app.core.auth import get_current_user_id
from app.core.memory_gc import memory_gc
from dataclasses import asdict

router = APIRouter()


@router.post("/{agent_id}")
async def run_gc(
    agent_id: str, body: dict = None, user_id: str = Depends(get_current_user_id)
):
    body = body or {}
    result = memory_gc.run_gc(
        agent_id,
        min_strength=body.get("min_strength", 0.1),
        max_age_days=body.get("max_age_days", 90),
    )
    return asdict(result)


@router.get("/history")
async def gc_history(agent_id: str = None, user_id: str = Depends(get_current_user_id)):
    history = memory_gc.get_gc_history(agent_id)
    return {"history": [asdict(r) for r in history]}


@router.get("/stats")
async def gc_stats(user_id: str = Depends(get_current_user_id)):
    return memory_gc.get_stats()
