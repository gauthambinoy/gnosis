import uuid
import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from dataclasses import asdict

from app.core.memory_engine import memory_engine
from app.core.database import get_db
from app.core.logger import get_logger
from app.models.memory import Memory, MemoryTier

logger = get_logger(__name__)
router = APIRouter()


def _use_db() -> bool:
    from app.core.database import db_available as _flag
    return _flag


@router.get("/{agent_id}")
async def get_agent_memories(agent_id: str, tier: str | None = None, limit: int = 50, db: AsyncSession = Depends(get_db)):
    if _use_db():
        query = select(Memory).where(Memory.agent_id == uuid.UUID(agent_id))
        if tier:
            query = query.where(Memory.tier == tier)
        query = query.order_by(Memory.created_at.desc()).limit(limit)
        result = await db.execute(query)
        rows = result.scalars().all()
        memories = [
            {"id": str(m.id), "agent_id": str(m.agent_id), "tier": m.tier.value if isinstance(m.tier, MemoryTier) else m.tier,
             "content": m.content, "relevance_score": m.relevance_score, "access_count": m.access_count,
             "strength": m.strength, "created_at": m.created_at.isoformat() if m.created_at else None,
             "metadata": m.extra_metadata or {}}
            for m in rows
        ]
        # Also get vector stats
        vector_stats = memory_engine.stats(agent_id)
        return {"agent_id": agent_id, "memories": memories, "total": len(memories), "tier": tier, "stats": vector_stats}

    # Fallback to in-memory engine
    memories = await memory_engine.get_agent_memories(agent_id, tier, limit)
    return {
        "agent_id": agent_id,
        "memories": [asdict(m) for m in memories],
        "total": len(memories),
        "tier": tier,
        "stats": memory_engine.stats(agent_id),
    }


@router.get("/{agent_id}/search")
async def search_memories(agent_id: str, query: str, limit: int = 10, db: AsyncSession = Depends(get_db)):
    # Vector search always uses the in-memory engine (FAISS) for similarity
    results = await memory_engine.search_memories(agent_id, query, limit)
    return {
        "agent_id": agent_id,
        "query": query,
        "results": [asdict(m) for m in results],
        "total": len(results),
    }


@router.post("/{agent_id}/store")
async def store_memory(agent_id: str, tier: str, content: str, metadata: dict = {}, db: AsyncSession = Depends(get_db)):
    # Always store in vector engine
    entry = await memory_engine.store(agent_id, tier, content, metadata)

    # Dual-write to PostgreSQL when available
    if _use_db():
        mem = Memory(
            id=uuid.UUID(entry.id),
            agent_id=uuid.UUID(agent_id),
            tier=MemoryTier(tier),
            content=content,
            relevance_score=entry.relevance_score,
            extra_metadata=metadata,
        )
        db.add(mem)
        await db.flush()

    return {"status": "stored", "memory": asdict(entry)}


@router.get("/{agent_id}/stats")
async def get_memory_stats(agent_id: str, db: AsyncSession = Depends(get_db)):
    vector_stats = memory_engine.stats(agent_id)

    if _use_db():
        # Add DB-level counts per tier
        query = (
            select(Memory.tier, sa_func.count())
            .where(Memory.agent_id == uuid.UUID(agent_id))
            .group_by(Memory.tier)
        )
        result = await db.execute(query)
        db_counts = {row[0].value if isinstance(row[0], MemoryTier) else row[0]: row[1] for row in result.all()}
        vector_stats["db_counts"] = db_counts
        vector_stats["db_total"] = sum(db_counts.values())

    return vector_stats


@router.post("/decay")
async def trigger_memory_decay(agent_id: str | None = None):
    """Manually trigger memory decay cycle.
    
    If agent_id is provided, decays only that agent's memories.
    Otherwise, decays all agents' memories.
    """
    from app.tasks.memory_decay import decay_agent_memories, run_decay_cycle
    
    try:
        if agent_id:
            stats = await asyncio.to_thread(decay_agent_memories, memory_engine, agent_id)
            return {"status": "success", "agent_id": agent_id, "stats": stats}
        else:
            stats = await asyncio.to_thread(run_decay_cycle, memory_engine)
            return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error(f"Memory decay error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
