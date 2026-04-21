"""Persistence guarantees for MemoryEngine (C5).

These tests spin up an isolated SQLite database, create all Gnosis tables on
it, flip ``db_available`` on, and exercise MemoryEngine's public API to prove
memories survive engine restarts and decay correctly.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def persistent_db(tmp_path, monkeypatch):
    """Point the app at a private SQLite DB, create tables, enable db_available."""
    db_file = tmp_path / "memory_persist.db"
    url = f"sqlite+aiosqlite:///{db_file}"

    # Swap the module-level engine/session factory so tests don't trample the
    # shared test.db.
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core import database as db_mod
    from app.models import Base

    new_engine = create_async_engine(url, echo=False)
    new_factory = async_sessionmaker(
        new_engine, class_=db_mod.AsyncSession, expire_on_commit=False
    )

    async with new_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(db_mod, "engine", new_engine)
    monkeypatch.setattr(db_mod, "async_session_factory", new_factory)
    monkeypatch.setattr(db_mod, "db_available", True)

    yield new_factory

    await new_engine.dispose()


@pytest.fixture
async def seeded_user_agent(persistent_db):
    """Insert one user + one agent row we can reference as FK targets."""
    from app.models.agent import Agent, AgentStatus
    from app.models.user import User

    user_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    async with persistent_db() as session:
        user = User(
            id=user_id,
            email=f"mem-{user_id.hex[:8]}@test.gnosis",
            hashed_password="x",
            full_name="Mem Test",
        )
        session.add(user)
        await session.flush()
        agent = Agent(
            id=agent_id,
            owner_id=user_id,
            name="Mem Agent",
            description="memory persistence test agent",
            status=AgentStatus.idle,
        )
        session.add(agent)
        await session.commit()
    return {"user_id": str(user_id), "agent_id": str(agent_id)}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_store_and_retrieve_roundtrip(persistent_db, seeded_user_agent):
    from app.core.memory_engine import MemoryEngine

    engine = MemoryEngine()
    agent_id = seeded_user_agent["agent_id"]

    entry = await engine.store(agent_id, "semantic", "The CEO is Ada Lovelace")
    assert entry.id
    fetched = await engine.get_agent_memories(agent_id, tier="semantic")
    assert any(m.content == "The CEO is Ada Lovelace" for m in fetched)


async def test_survives_engine_restart(persistent_db, seeded_user_agent):
    """Simulating a process restart: a fresh engine must see old rows."""
    from app.core.memory_engine import MemoryEngine

    agent_id = seeded_user_agent["agent_id"]
    engine1 = MemoryEngine()
    await engine1.store(agent_id, "episodic", "Yesterday we shipped v2")
    await engine1.store(agent_id, "semantic", "Gnosis uses FastAPI")

    # Throw engine1 away; new MemoryEngine instance simulates restart.
    del engine1
    engine2 = MemoryEngine()
    memories = await engine2.get_agent_memories(agent_id, limit=100)
    contents = {m.content for m in memories}
    assert "Yesterday we shipped v2" in contents
    assert "Gnosis uses FastAPI" in contents


async def test_tier_filter_in_search(persistent_db, seeded_user_agent):
    from app.core.memory_engine import MemoryEngine

    engine = MemoryEngine()
    agent_id = seeded_user_agent["agent_id"]
    await engine.store(agent_id, "episodic", "shipped v2 yesterday")
    await engine.store(agent_id, "semantic", "fastapi powers gnosis")
    await engine.store(agent_id, "procedural", "how to run migrations")

    episodic = await engine.get_agent_memories(agent_id, tier="episodic")
    semantic = await engine.get_agent_memories(agent_id, tier="semantic")
    procedural = await engine.get_agent_memories(agent_id, tier="procedural")
    assert len(episodic) == 1 and episodic[0].tier == "episodic"
    assert len(semantic) == 1 and semantic[0].tier == "semantic"
    assert len(procedural) == 1 and procedural[0].tier == "procedural"


async def test_correction_tier_never_decays(persistent_db, seeded_user_agent):
    from app.core.memory_engine import MemoryEngine

    engine = MemoryEngine()
    agent_id = seeded_user_agent["agent_id"]
    await engine.store_correction(
        agent_id,
        "send mass email",
        "ask for approval first",
        {"situation": "bulk outreach"},
    )

    # Run decay many times — correction rows must survive unchanged.
    for _ in range(200):
        await engine.decay_agent(agent_id)

    remaining = await engine.get_agent_memories(agent_id, tier="correction")
    assert len(remaining) == 1
    assert remaining[0].strength >= 1.0


async def test_decay_reduces_and_evicts_non_correction(
    persistent_db, seeded_user_agent
):
    from app.core.memory_engine import MemoryEngine
    from app.core.database import async_session_factory
    from app.models.memory import Memory

    engine = MemoryEngine()
    agent_id = seeded_user_agent["agent_id"]
    await engine.store(agent_id, "episodic", "ephemeral event")

    # One cycle should reduce strength.
    async with async_session_factory() as s:
        row = (await s.execute(
            __import__("sqlalchemy").select(Memory).where(
                Memory.agent_id == uuid.UUID(agent_id)
            )
        )).scalars().first()
        initial = float(row.strength or 1.0)

    stats = await engine.decay_agent(agent_id)
    assert stats["decayed"] >= 1

    async with async_session_factory() as s:
        row = (await s.execute(
            __import__("sqlalchemy").select(Memory).where(
                Memory.agent_id == uuid.UUID(agent_id)
            )
        )).scalars().first()
        assert row is not None
        assert row.strength < initial

    # Many cycles should eventually evict it.
    for _ in range(500):
        s = await engine.decay_agent(agent_id)
        if s["pruned"] >= 1:
            break
    remaining = await engine.get_agent_memories(agent_id, tier="episodic")
    assert remaining == []


async def test_concurrent_stores_all_persist(persistent_db, seeded_user_agent):
    from app.core.memory_engine import MemoryEngine

    engine = MemoryEngine()
    agent_id = seeded_user_agent["agent_id"]

    N = 25
    await asyncio.gather(
        *(engine.store(agent_id, "semantic", f"fact-{i}") for i in range(N))
    )

    rows = await engine.get_agent_memories(agent_id, tier="semantic", limit=100)
    contents = {m.content for m in rows}
    assert len(contents) == N
    for i in range(N):
        assert f"fact-{i}" in contents


async def test_sync_wrapper_runs_decay(persistent_db, seeded_user_agent):
    """The sync-friendly wrapper must work from legacy sync code paths."""
    from app.core.memory_engine import MemoryEngine

    engine = MemoryEngine()
    agent_id = seeded_user_agent["agent_id"]
    await engine.store(agent_id, "episodic", "sync wrapper smoke")

    stats = engine.decay_agent_sync(agent_id)
    assert isinstance(stats, dict)
    assert {"decayed", "pruned", "preserved"}.issubset(stats.keys())
