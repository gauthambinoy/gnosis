import pytest

pytestmark = pytest.mark.anyio

"""Tests for memory store, search, and stats endpoints."""


async def test_store_memory(client, api_prefix, created_agent):
    agent_id = created_agent["id"]
    resp = await client.post(
        f"{api_prefix}/memory/{agent_id}/store",
        params={"tier": "episodic", "content": "User prefers morning emails"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "stored"
    assert data["memory"]["tier"] == "episodic"
    assert data["memory"]["agent_id"] == agent_id


async def test_search_memory(client, api_prefix, created_agent):
    agent_id = created_agent["id"]
    # Store a memory first
    await client.post(
        f"{api_prefix}/memory/{agent_id}/store",
        params={"tier": "semantic", "content": "The CEO is John Smith"},
    )
    resp = await client.get(
        f"{api_prefix}/memory/{agent_id}/search",
        params={"query": "The CEO is John Smith"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == agent_id
    assert data["total"] >= 1


async def test_search_empty(client, api_prefix):
    # Search on an agent with no memories
    resp = await client.get(
        f"{api_prefix}/memory/no-memories-agent/search",
        params={"query": "anything"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_memory_stats(client, api_prefix, created_agent):
    agent_id = created_agent["id"]
    # Store a couple of memories
    for content in ("fact one", "fact two"):
        await client.post(
            f"{api_prefix}/memory/{agent_id}/store",
            params={"tier": "semantic", "content": content},
        )
    resp = await client.get(f"{api_prefix}/memory/{agent_id}/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "vectors" in data


async def test_memory_tiers(client, api_prefix, created_agent):
    agent_id = created_agent["id"]
    for tier in ("episodic", "semantic", "procedural"):
        await client.post(
            f"{api_prefix}/memory/{agent_id}/store",
            params={"tier": tier, "content": f"Memory in {tier}"},
        )
    resp = await client.get(f"{api_prefix}/memory/{agent_id}/stats")
    stats = resp.json()
    vectors = stats.get("vectors", {})
    tiers = vectors.get("tiers", {})
    assert len(tiers) >= 3
    total_vectors = sum(tiers.values())
    assert total_vectors >= 3
