"""Tests for the audit log retention policy (prune)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.audit_log import AuditLog


@pytest.mark.asyncio
async def test_prune_removes_old_entries():
    log = AuditLog()
    await log.log("test.event", "agent-1", {"k": "v"})

    # Force the entry to look ancient
    log.entries[0]["timestamp"] = (
        datetime.now(timezone.utc) - timedelta(days=400)
    ).isoformat()

    result = await log.prune(retention_days=365)
    assert result["pruned"] == 1
    assert result["remaining"] == 0


@pytest.mark.asyncio
async def test_prune_keeps_recent_entries_and_chain_valid():
    log = AuditLog()
    await log.log("e1", "a", {"v": 1})
    await log.log("e2", "a", {"v": 2})
    await log.log("e3", "a", {"v": 3})

    # Age out the first one
    log.entries[0]["timestamp"] = (
        datetime.now(timezone.utc) - timedelta(days=500)
    ).isoformat()

    result = await log.prune(retention_days=30)
    assert result["pruned"] == 1
    assert result["remaining"] == 2

    integrity = log.verify_integrity()
    assert integrity["valid"] is True
    assert integrity["entries_checked"] == 2


@pytest.mark.asyncio
async def test_prune_invalid_retention_rejected():
    log = AuditLog()
    with pytest.raises(ValueError):
        await log.prune(retention_days=0)


@pytest.mark.asyncio
async def test_prune_empty_log_is_safe():
    log = AuditLog()
    result = await log.prune(retention_days=30)
    assert result == {"pruned": 0, "remaining": 0}
