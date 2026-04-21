"""Durability tests for the request-audit middleware buffer.

Covers:
* Redis write path (LPUSH + LTRIM cap)
* Readback ordering
* List cap (LTRIM drops oldest)
* Redis outage does not raise from middleware / add()
* DB fallback when Redis is disabled
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest

from app.middleware.audit_log import (
    REDIS_LIST_CAP,
    REDIS_LIST_KEY,
    AuditRecord,
    AuditStore,
)


def _record(i: int = 0, **overrides) -> AuditRecord:
    base = dict(
        id=f"req-{i}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        method="GET",
        path=f"/api/v1/thing/{i}",
        status_code=200,
        latency_ms=1.23 + i,
        user_id="u1",
        ip_address="127.0.0.1",
        user_agent="pytest",
        request_size=0,
        response_size=0,
    )
    base.update(overrides)
    return AuditRecord(**base)


async def _drain(store: AuditStore) -> None:
    """Wait for all fire-and-forget persistence tasks to complete."""
    while store._background_tasks:
        await asyncio.gather(*list(store._background_tasks), return_exceptions=True)


@pytest.fixture
def fake_redis():
    """Patch redis_manager to expose a fakeredis async client."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)

    fake_mgr = MagicMock()
    fake_mgr.client = client
    fake_mgr.available = True

    with patch("app.core.redis_client.redis_manager", fake_mgr):
        yield client

    # Cleanup — FakeRedis doesn't need await close(), but be explicit.
    asyncio.get_event_loop().run_until_complete(client.aclose()) if False else None


@pytest.mark.asyncio
async def test_entry_written_to_redis_list(fake_redis):
    store = AuditStore()
    rec = _record(1)

    store.add(rec)
    await _drain(store)

    raw = await fake_redis.lrange(REDIS_LIST_KEY, 0, -1)
    assert len(raw) == 1
    payload = json.loads(raw[0])
    assert payload["id"] == "req-1"
    assert payload["path"] == "/api/v1/thing/1"


@pytest.mark.asyncio
async def test_readback_returns_entries_newest_first(fake_redis):
    store = AuditStore()
    for i in range(5):
        store.add(_record(i))
    await _drain(store)

    out = await store.recent(limit=10)
    assert [r["id"] for r in out] == ["req-4", "req-3", "req-2", "req-1", "req-0"]


@pytest.mark.asyncio
async def test_ltrim_caps_list_at_redis_cap(fake_redis):
    # Use a small cap so the test stays fast while still exercising LTRIM.
    import app.middleware.audit_log as mod

    store = AuditStore()
    with patch.object(mod, "REDIS_LIST_CAP", 5):
        for i in range(12):
            store.add(_record(i))
        await _drain(store)

    length = await fake_redis.llen(REDIS_LIST_KEY)
    assert length == 5

    # Newest 5 should have survived; oldest dropped.
    raw = await fake_redis.lrange(REDIS_LIST_KEY, 0, -1)
    ids = [json.loads(x)["id"] for x in raw]
    assert ids == ["req-11", "req-10", "req-9", "req-8", "req-7"]


@pytest.mark.asyncio
async def test_redis_outage_does_not_raise(caplog):
    """A Redis failure must never propagate to the request path."""
    store = AuditStore()

    broken = MagicMock()
    pipe = MagicMock()
    pipe.lpush = MagicMock()
    pipe.ltrim = MagicMock()
    pipe.execute = AsyncMock(side_effect=ConnectionError("redis down"))
    broken.client = MagicMock()
    broken.client.pipeline = MagicMock(return_value=pipe)
    broken.available = True

    async def _boom(*a, **kw):
        raise ConnectionError("db also down")

    with patch("app.core.redis_client.redis_manager", broken), patch.object(
        AuditStore, "_persist_db", AsyncMock(side_effect=ConnectionError("db down"))
    ):
        # add() must not raise even when both Redis and DB fail.
        store.add(_record(1))
        await _drain(store)

        # persist() returns "none" instead of raising.
        result = await store.persist(_record(2))
        assert result == "none"

    # Tail cache is still populated — always durable-ish for the live process.
    assert len(store._records) >= 1


@pytest.mark.asyncio
async def test_db_fallback_when_redis_disabled():
    """When Redis is unavailable, entries must write-through to the DB."""
    store = AuditStore()

    # redis_manager.client returns None when unavailable (per RedisManager impl).
    disabled_mgr = MagicMock()
    disabled_mgr.client = None
    disabled_mgr.available = False

    db_calls: list[AuditRecord] = []

    async def fake_db_persist(self, record):
        db_calls.append(record)
        return "db"

    with patch("app.core.redis_client.redis_manager", disabled_mgr), patch.object(
        AuditStore, "_persist_db", fake_db_persist
    ):
        backend = await store.persist(_record(7))

    assert backend == "db"
    assert len(db_calls) == 1
    assert db_calls[0].id == "req-7"


@pytest.mark.asyncio
async def test_recent_filters_by_path_and_method(fake_redis):
    store = AuditStore()
    store.add(_record(1, method="GET", path="/api/v1/users/1"))
    store.add(_record(2, method="POST", path="/api/v1/users/2"))
    store.add(_record(3, method="GET", path="/api/v1/agents/3"))
    await _drain(store)

    only_users = await store.recent(limit=10, path_filter="/users")
    assert {r["id"] for r in only_users} == {"req-1", "req-2"}

    only_post = await store.recent(limit=10, method_filter="post")
    assert [r["id"] for r in only_post] == ["req-2"]
