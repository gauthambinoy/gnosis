from fastapi import APIRouter
from app.core.memory_engine import memory_engine
from dataclasses import asdict

router = APIRouter()


@router.get("/{agent_id}")
async def get_agent_memories(agent_id: str, tier: str | None = None, limit: int = 50):
    memories = await memory_engine.get_agent_memories(agent_id, tier, limit)
    return {
        "agent_id": agent_id,
        "memories": [asdict(m) for m in memories],
        "total": len(memories),
        "tier": tier,
        "stats": memory_engine.stats(agent_id),
    }


@router.get("/{agent_id}/search")
async def search_memories(agent_id: str, query: str, limit: int = 10):
    results = await memory_engine.search_memories(agent_id, query, limit)
    return {
        "agent_id": agent_id,
        "query": query,
        "results": [asdict(m) for m in results],
        "total": len(results),
    }


@router.post("/{agent_id}/store")
async def store_memory(agent_id: str, tier: str, content: str, metadata: dict = {}):
    entry = await memory_engine.store(agent_id, tier, content, metadata)
    return {"status": "stored", "memory": asdict(entry)}


@router.get("/{agent_id}/stats")
async def get_memory_stats(agent_id: str):
    return memory_engine.stats(agent_id)
