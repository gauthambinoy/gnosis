import pytest

pytestmark = pytest.mark.anyio

"""Tests for standup daily and agent summary endpoints."""


async def test_standup_daily(client, api_prefix):
    resp = await client.get(f"{api_prefix}/standup/daily")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    # Should have standup report fields
    assert any(k in data for k in ("date", "summary", "agents", "total_executions", "period"))


async def test_standup_today(client, api_prefix):
    resp = await client.get(f"{api_prefix}/standup/today")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


async def test_standup_agent(client, api_prefix, created_agent):
    agent_id = created_agent["id"]
    resp = await client.get(f"{api_prefix}/standup/agent/{agent_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert data.get("agent_id") == agent_id or "agent_id" in data
