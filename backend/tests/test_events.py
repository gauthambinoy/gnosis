import pytest

pytestmark = pytest.mark.anyio

"""Tests for event recent and connections endpoints."""


async def test_recent_events(client, api_prefix):
    resp = await client.get(f"{api_prefix}/events/recent")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert isinstance(data["events"], list)


async def test_connections(client, api_prefix):
    resp = await client.get(f"{api_prefix}/events/connections")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "dashboard" in data
    assert isinstance(data["total"], int)
