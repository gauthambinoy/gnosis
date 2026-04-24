"""Unit tests for AuditLog (basic API)."""

import pytest
from app.core.audit_log import AuditLog, wire_audit_log
from app.core.event_bus import event_bus, Events


@pytest.fixture
def al():
    return AuditLog()


@pytest.mark.anyio
async def test_log_appends(al):
    await al.log("evt", "agent-1", {"k": "v"})
    assert len(al.entries) == 1
    e = al.entries[0]
    assert e["event_type"] == "evt"
    assert e["agent_id"] == "agent-1"
    assert e["hash"]


@pytest.mark.anyio
async def test_hash_chain_integrity(al):
    await al.log("evt", "a", {})
    await al.log("evt", "a", {"i": 2})
    res = al.verify_integrity()
    assert res["valid"] is True
    assert res["entries_checked"] == 2


@pytest.mark.anyio
async def test_tamper_detected(al):
    await al.log("evt", "a", {})
    await al.log("evt", "a", {"i": 2})
    al.entries[1]["details"] = {"tampered": True}
    res = al.verify_integrity()
    assert res["valid"] is False


@pytest.mark.anyio
async def test_query_by_agent(al):
    await al.log("evt", "a1", {})
    await al.log("evt", "a2", {})
    res = await al.query(agent_id="a1")
    assert len(res) == 1


@pytest.mark.anyio
async def test_query_by_event_type(al):
    await al.log("evt1", "a1", {})
    await al.log("evt2", "a1", {})
    res = await al.query(event_type="evt2")
    assert len(res) == 1


@pytest.mark.anyio
async def test_query_limit(al):
    for i in range(10):
        await al.log("e", "a", {"i": i})
    res = await al.query(limit=3)
    assert len(res) == 3


@pytest.mark.anyio
async def test_export_json(al):
    await al.log("e", "a", {})
    out = await al.export("json")
    assert "event_type" in out


@pytest.mark.anyio
async def test_export_csv(al):
    await al.log("e", "a", {"k": "v"})
    out = await al.export("csv")
    assert out.splitlines()[0].startswith("id,timestamp")


@pytest.mark.anyio
async def test_export_unknown_format_raises(al):
    with pytest.raises(ValueError):
        await al.export("xml")


def test_wire_audit_log_subscribes_handlers():
    """Verify wiring registers handlers for known events."""
    before = len(event_bus._handlers.get(Events.EXECUTION_STARTED, []))
    wire_audit_log()
    after = len(event_bus._handlers.get(Events.EXECUTION_STARTED, []))
    assert after > before
