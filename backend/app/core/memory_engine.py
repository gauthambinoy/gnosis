"""Gnosis Memory Engine — real 4-tier memory with vector search."""

import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from app.core.embeddings import embedding_service
from app.core.vector_store import agent_vectors, SearchResult


@dataclass
class MemoryEntry:
    id: str
    agent_id: str
    tier: str
    content: str
    relevance_score: float = 1.0
    access_count: int = 0
    strength: float = 1.0
    last_accessed: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict = field(default_factory=dict)


@dataclass
class MemoryContext:
    corrections: list[MemoryEntry]
    recent: list[MemoryEntry]
    relevant_past: list[MemoryEntry]
    knowledge: list[MemoryEntry]
    procedures: list[MemoryEntry]
    retrieval_ms: float = 0.0


class MemoryEngine:
    """4-tier memory with parallel retrieval and vector search."""

    def __init__(self):
        # In-memory storage (upgrades to PostgreSQL + FAISS files later)
        self._memories: dict[
            str, dict[str, list[MemoryEntry]]
        ] = {}  # agent_id -> tier -> memories
        self._sensory_buffer: dict[
            str, list[dict]
        ] = {}  # agent_id -> recent events (max 100)

    def _get_agent_memories(self, agent_id: str, tier: str) -> list[MemoryEntry]:
        if agent_id not in self._memories:
            self._memories[agent_id] = {}
        if tier not in self._memories[agent_id]:
            self._memories[agent_id][tier] = []
        return self._memories[agent_id][tier]

    async def store(
        self, agent_id: str, tier: str, content: str, metadata: dict | None = None
    ) -> MemoryEntry:
        """Store a new memory and its embedding."""
        mem_id = str(uuid.uuid4())
        entry = MemoryEntry(
            id=mem_id,
            agent_id=agent_id,
            tier=tier,
            content=content,
            metadata=metadata or {},
        )

        # Store in memory list
        memories = self._get_agent_memories(agent_id, tier)
        memories.append(entry)

        # Generate and store embedding
        embedding = embedding_service.embed(content)
        store = agent_vectors.get_store(agent_id, tier)
        store.add(
            mem_id, embedding, {"content": content, "tier": tier, **(metadata or {})}
        )

        return entry

    async def store_correction(
        self, agent_id: str, original_action: str, correction: str, context: dict
    ) -> MemoryEntry:
        """Store a correction with highest priority — these NEVER decay."""
        content = f"CORRECTION: When situation is '{context.get('situation', 'unknown')}', do NOT '{original_action}', instead '{correction}'"
        return await self.store(
            agent_id=agent_id,
            tier="correction",
            content=content,
            metadata={
                "original": original_action,
                "correction": correction,
                "context": context,
            },
        )

    async def push_sensory(self, agent_id: str, event: dict):
        """Push to sensory buffer (most recent 100 events)."""
        if agent_id not in self._sensory_buffer:
            self._sensory_buffer[agent_id] = []
        self._sensory_buffer[agent_id].append(
            {
                **event,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        # Keep only last 100
        if len(self._sensory_buffer[agent_id]) > 100:
            self._sensory_buffer[agent_id] = self._sensory_buffer[agent_id][-100:]

    async def retrieve_context(
        self, agent_id: str, trigger_data: dict
    ) -> MemoryContext:
        """Retrieve relevant context from all memory tiers."""
        start = time.time()

        # Build query from trigger data
        query_text = " ".join(str(v) for v in trigger_data.values())
        if not query_text.strip():
            query_text = "general context"

        query_embedding = embedding_service.embed(query_text)

        # Search all tiers
        results = agent_vectors.search_all_tiers(agent_id, query_embedding, top_k=20)

        corrections = [
            self._result_to_entry(r, agent_id)
            for r in results
            if r.metadata.get("tier") == "correction"
        ]
        episodic = [
            self._result_to_entry(r, agent_id)
            for r in results
            if r.metadata.get("tier") == "episodic"
        ]
        semantic = [
            self._result_to_entry(r, agent_id)
            for r in results
            if r.metadata.get("tier") == "semantic"
        ]
        procedural = [
            self._result_to_entry(r, agent_id)
            for r in results
            if r.metadata.get("tier") == "procedural"
        ]

        # Recent from sensory buffer
        recent = self._sensory_buffer.get(agent_id, [])[-10:]
        recent_entries = [
            MemoryEntry(
                id=f"sensory-{i}", agent_id=agent_id, tier="sensory", content=str(e)
            )
            for i, e in enumerate(recent)
        ]

        retrieval_ms = (time.time() - start) * 1000

        return MemoryContext(
            corrections=corrections,
            recent=recent_entries,
            relevant_past=episodic,
            knowledge=semantic,
            procedures=procedural,
            retrieval_ms=retrieval_ms,
        )

    def _result_to_entry(self, result: SearchResult, agent_id: str) -> MemoryEntry:
        return MemoryEntry(
            id=result.id,
            agent_id=agent_id,
            tier=result.metadata.get("tier", "unknown"),
            content=result.metadata.get("content", ""),
            relevance_score=result.score,
            metadata=result.metadata,
        )

    async def get_agent_memories(
        self, agent_id: str, tier: str | None = None, limit: int = 50
    ) -> list[MemoryEntry]:
        """Get memories for an agent."""
        if tier:
            return self._get_agent_memories(agent_id, tier)[:limit]
        all_memories = []
        for t in ["correction", "episodic", "semantic", "procedural"]:
            all_memories.extend(self._get_agent_memories(agent_id, t))
        return sorted(all_memories, key=lambda m: m.created_at, reverse=True)[:limit]

    async def search_memories(
        self, agent_id: str, query: str, limit: int = 10
    ) -> list[MemoryEntry]:
        """Semantic search across agent memories."""
        query_embedding = embedding_service.embed(query)
        results = agent_vectors.search_all_tiers(agent_id, query_embedding, top_k=limit)
        return [self._result_to_entry(r, agent_id) for r in results]

    def stats(self, agent_id: str) -> dict:
        vectors = agent_vectors.stats(agent_id)
        sensory_count = len(self._sensory_buffer.get(agent_id, []))
        embedding_stats = embedding_service.cache_stats
        return {
            "vectors": vectors,
            "sensory_buffer": sensory_count,
            "embeddings": embedding_stats,
        }


# Global singleton
memory_engine = MemoryEngine()
