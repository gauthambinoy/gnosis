from fastapi import APIRouter

router = APIRouter()


@router.get("/{agent_id}")
async def get_agent_memories(agent_id: str, tier: str | None = None, limit: int = 50):
    """Get memories for an agent, optionally filtered by tier."""
    return {"agent_id": agent_id, "memories": [], "total": 0, "tier": tier}


@router.get("/{agent_id}/search")
async def search_memories(agent_id: str, query: str, limit: int = 10):
    """Semantic search across agent memories."""
    return {"agent_id": agent_id, "query": query, "results": [], "total": 0}
