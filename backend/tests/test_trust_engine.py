"""Unit tests for TrustEngine."""

import pytest
from app.core.trust_engine import TrustEngine


@pytest.fixture
def te():
    return TrustEngine()


@pytest.mark.anyio
async def test_initial_level_is_zero(te):
    assert te.get_trust_level("agent-1") == 0


@pytest.mark.anyio
async def test_promote_increments_level(te):
    res = await te.promote("agent-1")
    assert res["changed"] is True
    assert res["level"] == 1
    assert te.get_trust_level("agent-1") == 1


@pytest.mark.anyio
async def test_promote_at_max_no_change(te):
    te.set_trust_level("agent-1", 4)
    res = await te.promote("agent-1")
    assert res["changed"] is False


@pytest.mark.anyio
async def test_demote_decrements_level(te):
    te.set_trust_level("agent-1", 2)
    res = await te.demote("agent-1", reason="test")
    assert res["changed"] is True
    assert res["level"] == 1


@pytest.mark.anyio
async def test_demote_at_min_no_change(te):
    res = await te.demote("agent-1")
    assert res["changed"] is False


@pytest.mark.anyio
async def test_check_permission_observer_only_read(te):
    res = await te.check_permission("agent-1", "read")
    assert res["allowed"] is True
    res2 = await te.check_permission("agent-1", "execute_safe")
    assert res2["allowed"] is False


@pytest.mark.anyio
async def test_check_permission_autonomous_all(te):
    te.set_trust_level("agent-1", 4)
    res = await te.check_permission("agent-1", "anything")
    assert res["allowed"] is True
    assert res["requires_approval"] is False


@pytest.mark.anyio
async def test_evaluate_recommends_demote_on_critical(te):
    res = await te.evaluate("agent-1", {"critical_failures_7d": 1, "accuracy": 0.99, "total_executions": 30})
    assert res["recommendation"] == "demote"


@pytest.mark.anyio
async def test_evaluate_recommends_promote(te):
    for _ in range(25):
        te.record_execution("agent-1", success=True)
    res = await te.evaluate("agent-1", {})
    assert res["recommendation"] == "promote"


@pytest.mark.anyio
async def test_evaluate_holds_when_insufficient(te):
    te.record_execution("agent-1", success=True)
    res = await te.evaluate("agent-1", {})
    assert res["recommendation"] == "hold"


@pytest.mark.anyio
async def test_should_require_approval_blocked(te):
    # Observer cannot execute
    needs = await te.should_require_approval("agent-1", "execute_safe", confidence=0.9)
    assert needs is True


@pytest.mark.anyio
async def test_should_require_approval_apprentice_draft(te):
    te.set_trust_level("agent-1", 1)  # Apprentice: draft allowed but auto_approve False
    needs = await te.should_require_approval("agent-1", "draft", confidence=0.9)
    assert needs is True


@pytest.mark.anyio
async def test_record_execution_history(te):
    te.record_execution("agent-1", success=True)
    te.record_execution("agent-1", success=False, critical=True)
    assert len(te._agent_history["agent-1"]) == 2
