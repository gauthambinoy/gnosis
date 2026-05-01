"""Gnosis Memory Engine — durable 4-tier memory with optional vector search.

Storage model
-------------
* Writes go straight to PostgreSQL (via the async SQLAlchemy engine) when the
  database is available. On any restart, memories survive.
* A small in-process LRU cache sits on top of the DB for hot reads.
* Similarity search currently loads candidates from the DB and computes cosine
  similarity in Python. Future work: pgvector / FAISS for index-side search.

The public API (store / store_correction / push_sensory / retrieve_context /
get_agent_memories / search_memories / stats) is unchanged from the previous
in-memory implementation — callers rely on these signatures.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import numpy as np
from sqlalchemy import delete, select, update

from app.core.embeddings import embedding_service
from app.core.vector_store import SearchResult, agent_vectors


_MISSING_DB_WARNED = False


def _db_active() -> bool:
    """Return True if the SQLAlchemy engine is reachable.

    Imported lazily so test harnesses that flip ``db_available`` mid-run pick
    up the change.
    """
    try:
        from app.core.database import db_available

        return bool(db_available)
    except Exception:
        return False


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _encode_embedding(vec) -> str | None:
    if vec is None:
        return None
    try:
        return json.dumps([float(x) for x in np.asarray(vec).ravel().tolist()])
    except Exception:
        return None


def _decode_embedding(raw) -> np.ndarray | None:
    if not raw:
        return None
    try:
        return np.asarray(json.loads(raw), dtype=np.float32)
    except Exception:
        return None


def _uuid_or_none(value):
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _row_to_entry(row) -> MemoryEntry:
    """Convert a Memory ORM row into a MemoryEntry dataclass."""
    from app.models.memory import MemoryTier

    tier = row.tier.value if isinstance(row.tier, MemoryTier) else str(row.tier)
    return MemoryEntry(
        id=str(row.id),
        agent_id=str(row.agent_id) if row.agent_id else "",
        tier=tier,
        content=row.content,
        relevance_score=float(row.relevance_score or 1.0),
        access_count=int(row.access_count or 0),
        strength=float(row.strength or 1.0),
        last_accessed=(
            row.last_accessed_at.isoformat() if row.last_accessed_at else None
        ),
        created_at=(
            row.created_at.isoformat()
            if row.created_at
            else datetime.now(timezone.utc).isoformat()
        ),
        metadata=dict(row.extra_metadata or {}),
    )


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class MemoryEngine:
    """4-tier memory with DB-backed persistence and cached hot reads."""

    LRU_CAPACITY = 512

    def __init__(self):
        # Fallback store for when the DB is unavailable (demo / offline mode).
        self._memories: dict[str, dict[str, list[MemoryEntry]]] = {}
        # Short ring buffer of recent sensory events per agent.
        self._sensory_buffer: dict[str, list[dict]] = {}
        # LRU cache of hot memory entries keyed by id.
        self._lru: "OrderedDict[str, MemoryEntry]" = OrderedDict()

    # ------------------------------------------------------------------ cache

    def _cache_put(self, entry: MemoryEntry) -> None:
        self._lru[entry.id] = entry
        self._lru.move_to_end(entry.id)
        while len(self._lru) > self.LRU_CAPACITY:
            self._lru.popitem(last=False)

    # ---------------------------------------------------- in-memory fallback

    def _get_agent_memories(self, agent_id: str, tier: str) -> list[MemoryEntry]:
        if agent_id not in self._memories:
            self._memories[agent_id] = {}
        if tier not in self._memories[agent_id]:
            self._memories[agent_id][tier] = []
        return self._memories[agent_id][tier]

    # ----------------------------------------------------- DB-backed writes

    async def store(
        self,
        agent_id: str,
        tier: str,
        content: str,
        metadata: dict | None = None,
    ) -> MemoryEntry:
        """Persist a new memory. Returns the in-memory representation."""
        mem_id = str(uuid.uuid4())
        entry = MemoryEntry(
            id=mem_id,
            agent_id=agent_id,
            tier=tier,
            content=content,
            metadata=metadata or {},
        )

        # Compute embedding once — used for both the vector store and DB.
        embedding = None
        try:
            embedding = embedding_service.embed(content)
        except Exception:
            embedding = None

        if _db_active():
            await self._db_insert(entry, embedding)
        else:
            # Fallback: in-process list.
            self._get_agent_memories(agent_id, tier).append(entry)

        # Always update the in-memory vector index for fast similarity (legacy
        # behavior) and the LRU read cache.
        if embedding is not None:
            try:
                store = agent_vectors.get_store(agent_id, tier)
                store.add(
                    mem_id,
                    embedding,
                    {"content": content, "tier": tier, **(metadata or {})},
                )
            except Exception:
                pass
        self._cache_put(entry)
        return entry

    async def _db_insert(self, entry: MemoryEntry, embedding) -> None:
        from app.core.database import async_session_factory
        from app.models.memory import Memory, MemoryTier

        try:
            tier_enum = MemoryTier(entry.tier)
        except ValueError:
            tier_enum = MemoryTier.episodic  # safe fallback

        agent_uuid = _uuid_or_none(entry.agent_id)
        row = Memory(
            id=_uuid_or_none(entry.id) or uuid.uuid4(),
            agent_id=agent_uuid,
            tier=tier_enum,
            content=entry.content,
            embedding=_encode_embedding(embedding),
            extra_metadata=entry.metadata or {},
            relevance_score=entry.relevance_score,
            access_count=entry.access_count,
            strength=entry.strength,
        )
        async with async_session_factory() as session:
            session.add(row)
            await session.commit()

    async def store_correction(
        self, agent_id: str, original_action: str, correction: str, context: dict
    ) -> MemoryEntry:
        """Store a correction with highest priority — these NEVER decay."""
        content = (
            f"CORRECTION: When situation is '{context.get('situation', 'unknown')}',"
            f" do NOT '{original_action}', instead '{correction}'"
        )
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
        """Push to sensory buffer (most recent 100 events). In-process only."""
        if agent_id not in self._sensory_buffer:
            self._sensory_buffer[agent_id] = []
        self._sensory_buffer[agent_id].append(
            {**event, "timestamp": datetime.now(timezone.utc).isoformat()}
        )
        if len(self._sensory_buffer[agent_id]) > 100:
            self._sensory_buffer[agent_id] = self._sensory_buffer[agent_id][-100:]

    # ------------------------------------------------------ DB-backed reads

    async def _load_from_db(
        self, agent_id: str, tier: str | None = None, limit: int | None = None
    ) -> list:
        """Return ORM rows for (agent_id, tier)."""
        from app.core.database import async_session_factory
        from app.models.memory import Memory, MemoryTier

        agent_uuid = _uuid_or_none(agent_id)
        if agent_uuid is None:
            return []
        stmt = select(Memory).where(Memory.agent_id == agent_uuid)
        if tier:
            try:
                stmt = stmt.where(Memory.tier == MemoryTier(tier))
            except ValueError:
                return []
        stmt = stmt.order_by(Memory.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)
        async with async_session_factory() as session:
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def _bump_access(self, ids: Iterable[uuid.UUID]) -> None:
        from app.core.database import async_session_factory
        from app.models.memory import Memory

        ids = [i for i in ids if i is not None]
        if not ids:
            return
        async with async_session_factory() as session:
            await session.execute(
                update(Memory)
                .where(Memory.id.in_(ids))
                .values(
                    access_count=Memory.access_count + 1,
                    last_accessed_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

    async def get_agent_memories(
        self, agent_id: str, tier: str | None = None, limit: int = 50
    ) -> list[MemoryEntry]:
        """Return up to ``limit`` most-recent memories (optionally per tier)."""
        if _db_active():
            if tier:
                rows = await self._load_from_db(agent_id, tier, limit)
            else:
                rows = []
                for t in ("correction", "episodic", "semantic", "procedural"):
                    rows.extend(await self._load_from_db(agent_id, t, limit))
                rows.sort(
                    key=lambda r: r.created_at or datetime.min.replace(tzinfo=timezone.utc),
                    reverse=True,
                )
                rows = rows[:limit]
            entries = [_row_to_entry(r) for r in rows]
            for e in entries:
                self._cache_put(e)
            return entries

        if tier:
            return list(self._get_agent_memories(agent_id, tier))[:limit]
        all_memories: list[MemoryEntry] = []
        for t in ("correction", "episodic", "semantic", "procedural"):
            all_memories.extend(self._get_agent_memories(agent_id, t))
        return sorted(all_memories, key=lambda m: m.created_at, reverse=True)[:limit]

    async def search_memories(
        self, agent_id: str, query: str, limit: int = 10
    ) -> list[MemoryEntry]:
        """Semantic search across agent memories.

        Current implementation loads stored embeddings from the DB and ranks
        them with cosine similarity in Python. This is fine for typical agent
        working-set sizes; for larger corpora swap in pgvector or FAISS at
        this point without changing the public API.
        """
        try:
            query_embedding = embedding_service.embed(query)
        except Exception:
            query_embedding = None

        if _db_active():
            rows = await self._load_from_db(agent_id)
            scored: list[tuple[float, Any]] = []
            qvec = np.asarray(query_embedding) if query_embedding is not None else None
            for r in rows:
                emb = _decode_embedding(r.embedding)
                if qvec is not None and emb is not None:
                    score = _cosine(qvec, emb)
                else:
                    score = float(r.relevance_score or 0.0)
                scored.append((score, r))
            scored.sort(key=lambda p: p[0], reverse=True)
            top = scored[:limit]
            entries: list[MemoryEntry] = []
            ids = []
            for score, r in top:
                e = _row_to_entry(r)
                e.relevance_score = score
                entries.append(e)
                ids.append(r.id)
            if ids:
                try:
                    await self._bump_access(ids)
                except Exception:
                    pass
            for e in entries:
                self._cache_put(e)
            return entries

        # In-memory fallback: reuse existing vector store.
        if query_embedding is None:
            return []
        results = agent_vectors.search_all_tiers(agent_id, query_embedding, top_k=limit)
        return [self._result_to_entry(r, agent_id) for r in results]

    async def retrieve_context(
        self, agent_id: str, trigger_data: dict
    ) -> MemoryContext:
        """Retrieve relevant context from all memory tiers."""
        start = time.time()
        query_text = " ".join(str(v) for v in trigger_data.values())
        if not query_text.strip():
            query_text = "general context"

        results = await self.search_memories(agent_id, query_text, limit=40)

        corrections = [r for r in results if r.tier == "correction"]
        episodic = [r for r in results if r.tier == "episodic"]
        semantic = [r for r in results if r.tier == "semantic"]
        procedural = [r for r in results if r.tier == "procedural"]

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

    # --------------------------------------------------------------- stats

    def stats(self, agent_id: str) -> dict:
        vectors = agent_vectors.stats(agent_id)
        sensory_count = len(self._sensory_buffer.get(agent_id, []))
        embedding_stats = embedding_service.cache_stats
        return {
            "vectors": vectors,
            "sensory_buffer": sensory_count,
            "embeddings": embedding_stats,
            "cache_size": len(self._lru),
        }

    # --------------------------------------------------------------- decay

    DECAY_RATES = {
        "sensory": 0.95,
        "episodic": 0.98,
        "semantic": 0.995,
        "procedural": 0.99,
        "correction": 1.0,  # Never decays
    }
    STRENGTH_FLOOR = 0.01

    async def decay_agent(self, agent_id: str) -> dict:
        """Apply exponential decay to one agent's memories.

        * ``correction``-tier rows are skipped (permanent).
        * Rows whose strength falls below ``STRENGTH_FLOOR`` are deleted.
        """
        stats = {"decayed": 0, "pruned": 0, "preserved": 0}

        if _db_active():
            from app.core.database import async_session_factory
            from app.models.memory import Memory, MemoryTier

            agent_uuid = _uuid_or_none(agent_id)
            if agent_uuid is None:
                return stats

            async with async_session_factory() as session:
                result = await session.execute(
                    select(Memory).where(Memory.agent_id == agent_uuid)
                )
                rows = result.scalars().all()
                to_delete: list = []
                for row in rows:
                    tier = (
                        row.tier.value
                        if isinstance(row.tier, MemoryTier)
                        else str(row.tier)
                    )
                    rate = self.DECAY_RATES.get(tier, 0.98)
                    if rate >= 1.0:
                        stats["preserved"] += 1
                        continue
                    access_boost = min((row.access_count or 0) * 0.01, 0.05)
                    effective_rate = min(rate + access_boost, 0.999)
                    decayed_strength = float(row.strength or 1.0) * effective_rate
                    setattr(row, "strength", decayed_strength)
                    if decayed_strength < self.STRENGTH_FLOOR:
                        to_delete.append(row.id)
                        stats["pruned"] += 1
                    else:
                        stats["decayed"] += 1
                if to_delete:
                    await session.execute(
                        delete(Memory).where(Memory.id.in_(to_delete))
                    )
                    # Drop from caches too.
                    for mid in to_delete:
                        self._lru.pop(str(mid), None)
                await session.commit()
            return stats

        # In-memory fallback mirrors the original behavior.
        for tier, rate in self.DECAY_RATES.items():
            memories = self._get_agent_memories(agent_id, tier)
            if rate >= 1.0:
                stats["preserved"] += len(memories)
                continue
            to_remove = []
            for mem in memories:
                access_boost = min(mem.access_count * 0.01, 0.05)
                effective_rate = min(rate + access_boost, 0.999)
                mem.strength *= effective_rate
                if mem.strength < self.STRENGTH_FLOOR:
                    to_remove.append(mem.id)
                    stats["pruned"] += 1
                else:
                    stats["decayed"] += 1
            if to_remove:
                self._memories[agent_id][tier] = [
                    m for m in memories if m.id not in set(to_remove)
                ]
        return stats

    async def decay_all(self) -> dict:
        """Run decay across every agent known to this engine."""
        total = {"agents_processed": 0, "decayed": 0, "pruned": 0, "preserved": 0}
        agent_ids: set[str] = set()

        if _db_active():
            from app.core.database import async_session_factory
            from app.models.memory import Memory

            async with async_session_factory() as session:
                result = await session.execute(
                    select(Memory.agent_id).distinct()
                )
                for (aid,) in result.all():
                    if aid is not None:
                        agent_ids.add(str(aid))

        agent_ids.update(self._memories.keys())
        for aid in agent_ids:
            s = await self.decay_agent(aid)
            total["agents_processed"] += 1
            for key in ("decayed", "pruned", "preserved"):
                total[key] += s[key]
        return total

    # ---------------------------------------------------- sync-friendly API

    @staticmethod
    def _run_sync(coro):
        """Run *coro* from a sync context, whether or not a loop is running."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        # A loop is already running — execute on a dedicated thread so we
        # don't deadlock. Caller is responsible for using the async API when
        # possible; this branch exists for legacy sync code paths.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(coro)).result()

    def decay_agent_sync(self, agent_id: str) -> dict:
        return self._run_sync(self.decay_agent(agent_id))

    def decay_all_sync(self) -> dict:
        return self._run_sync(self.decay_all())


# Global singleton
memory_engine = MemoryEngine()
