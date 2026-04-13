import pytest

pytestmark = pytest.mark.anyio

"""Tests for agent CRUD, execute, and correct endpoints."""


async def test_create_agent(client, api_prefix):
    resp = await client.post(f"{api_prefix}/agents", json={
        "name": "Email Bot",
        "description": "Handles emails",
        "personality": "professional",
        "trigger_type": "manual",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Email Bot"
    assert "id" in data
    assert data["status"] == "idle"
    assert data["trust_level"] == 0


async def test_list_agents(client, api_prefix):
    # Create 2 agents
    for name in ("Agent A", "Agent B"):
        await client.post(f"{api_prefix}/agents", json={
            "name": name, "description": f"Desc for {name}",
        })
    resp = await client.get(f"{api_prefix}/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["agents"]) >= 2


async def test_get_agent(client, api_prefix, created_agent):
    agent_id = created_agent["id"]
    resp = await client.get(f"{api_prefix}/agents/{agent_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == agent_id
    assert data["name"] == created_agent["name"]


async def test_get_agent_not_found(client, api_prefix):
    resp = await client.get(f"{api_prefix}/agents/00000000-0000-0000-0000-000000000099")
    assert resp.status_code == 404


async def test_update_agent(client, api_prefix, created_agent):
    agent_id = created_agent["id"]
    resp = await client.patch(f"{api_prefix}/agents/{agent_id}", json={
        "name": "Updated Agent",
        "description": "New description",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Agent"
    assert data["description"] == "New description"


async def test_delete_agent(client, api_prefix, created_agent):
    agent_id = created_agent["id"]
    resp = await client.delete(f"{api_prefix}/agents/{agent_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
    # Verify gone
    resp2 = await client.get(f"{api_prefix}/agents/{agent_id}")
    assert resp2.status_code == 404


async def test_execute_agent(client, api_prefix, created_agent):
    agent_id = created_agent["id"]
    resp = await client.post(f"{api_prefix}/agents/{agent_id}/execute", json={
        "subject": "Test trigger"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["agent_id"] == agent_id
    assert "execution_id" in data


async def test_correct_agent(client, api_prefix, created_agent):
    agent_id = created_agent["id"]
    resp = await client.post(f"{api_prefix}/agents/{agent_id}/correct", json={
        "correction": "Use formal tone in replies",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "correction_stored"
    assert data["agent_id"] == agent_id
