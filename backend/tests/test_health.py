import pytest

pytestmark = pytest.mark.anyio

"""Tests for the health endpoint."""


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "gnosis"
