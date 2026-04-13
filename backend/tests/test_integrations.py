import pytest

pytestmark = pytest.mark.anyio

"""Tests for integration providers and status endpoints."""


async def test_list_providers(client, api_prefix):
    resp = await client.get(f"{api_prefix}/integrations/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "integrations" in data
    assert len(data["integrations"]) >= 4
    ids = [i["id"] for i in data["integrations"]]
    assert "gmail" in ids
    assert "slack" in ids


async def test_provider_status(client, api_prefix):
    resp = await client.get(f"{api_prefix}/integrations/gmail/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "gmail"
    assert data["status"] in ("connected", "not_connected")


async def test_provider_status_http(client, api_prefix):
    resp = await client.get(f"{api_prefix}/integrations/http/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "available"


async def test_unknown_provider_status(client, api_prefix):
    resp = await client.get(f"{api_prefix}/integrations/unknown/status")
    assert resp.status_code == 404
