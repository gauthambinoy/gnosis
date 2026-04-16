"""Memory pre-fetching API."""
from fastapi import APIRouter, Depends
from app.core.auth import get_current_user_id
from app.core.memory_prefetch import memory_prefetch_engine
from dataclasses import asdict

router = APIRouter()


@router.post("/{agent_id}")
async def prefetch_memory(agent_id: str, body: dict = None, user_id: str = Depends(get_current_user_id)):
    body = body or {}
    context_hint = body.get("context_hint", "")
    result = memory_prefetch_engine.prefetch(agent_id, context_hint)
    return asdict(result)


@router.get("/stats")
async def prefetch_stats(user_id: str = Depends(get_current_user_id)):
    return memory_prefetch_engine.get_stats()
