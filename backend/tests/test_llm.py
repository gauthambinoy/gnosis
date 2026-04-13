import pytest

pytestmark = pytest.mark.anyio

"""Tests for LLM tiers, providers, and cost endpoints."""


async def test_llm_tiers(client, api_prefix):
    resp = await client.get(f"{api_prefix}/llm/tiers")
    assert resp.status_code == 200
    data = resp.json()
    tiers = data["tiers"]
    for key in ("L0", "L1", "L2", "L3"):
        assert key in tiers
        assert "name" in tiers[key]


async def test_llm_providers(client, api_prefix):
    resp = await client.get(f"{api_prefix}/llm/providers")
    assert resp.status_code == 200
    providers = resp.json()["providers"]
    assert len(providers) == 8
    ids = [p["id"] for p in providers]
    assert "openrouter" in ids
    assert "ollama" in ids


async def test_llm_stats(client, api_prefix):
    resp = await client.get(f"{api_prefix}/llm/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


async def test_llm_costs(client, api_prefix):
    resp = await client.get(f"{api_prefix}/llm/costs")
    assert resp.status_code == 200
    data = resp.json()
    assert "today" in data
    assert "total" in data
