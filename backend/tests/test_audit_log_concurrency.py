"""Concurrent-safety tests for the audit log hash chain."""

import asyncio
import pytest

from app.core.audit_log import AuditLog


@pytest.mark.anyio
async def test_concurrent_appends_preserve_chain():
    log = AuditLog()
    n = 200

    async def worker(i: int):
        await log.log("execution.started", f"agent-{i % 5}", {"i": i})

    await asyncio.gather(*(worker(i) for i in range(n)))

    assert len(log.entries) == n
    ids = [e["id"] for e in log.entries]
    assert ids == list(range(n))
    result = log.verify_integrity()
    assert result["valid"] is True
    assert result["entries_checked"] == n


@pytest.mark.anyio
async def test_verify_integrity_during_concurrent_writes():
    log = AuditLog()

    async def writer():
        for i in range(50):
            await log.log("evt", "agent", {"i": i})
            await asyncio.sleep(0)

    async def verifier():
        results = []
        for _ in range(20):
            results.append(log.verify_integrity())
            await asyncio.sleep(0)
        return results

    _, verifications = await asyncio.gather(writer(), verifier())
    for r in verifications:
        assert r["valid"] is True


@pytest.mark.anyio
async def test_prune_keeps_chain_valid_under_concurrency():
    log = AuditLog()
    for i in range(20):
        await log.log("evt", "agent", {"i": i})

    async def more_writes():
        for i in range(20):
            await log.log("evt", "agent", {"i": 100 + i})

    # Run a prune (no-op for retention) concurrently with appends
    results = await asyncio.gather(log.prune(retention_days=365), more_writes())
    assert results[0]["remaining"] >= 20
    integrity = log.verify_integrity()
    assert integrity["valid"] is True
