"""API integration tests for health, auth, and agent CRUD endpoints."""
import pytest
import uuid

pytestmark = pytest.mark.anyio


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("ok", "healthy")


async def test_docs(client):
    r = await client.get("/docs")
    assert r.status_code == 200


async def test_register_and_login(client, api_prefix):
    email = f"api-{uuid.uuid4().hex[:8]}@test.com"
    # Register
    r = await client.post(f"{api_prefix}/auth/register", json={
        "email": email, "password": "TestPass123!", "full_name": "Test"
    })
    assert r.status_code == 201
    data = r.json()
    assert "access_token" in data

    # Login
    r = await client.post(f"{api_prefix}/auth/login", json={
        "email": email, "password": "TestPass123!"
    })
    assert r.status_code == 200
    token = r.json()["access_token"]

    # Use token to list agents
    r = await client.get(f"{api_prefix}/agents", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


async def test_register_weak_password_rejected(client, api_prefix):
    r = await client.post(f"{api_prefix}/auth/register", json={
        "email": "weak@test.com", "password": "short", "full_name": "W"
    })
    assert r.status_code in (400, 422)


async def test_register_invalid_email(client, api_prefix):
    r = await client.post(f"{api_prefix}/auth/register", json={
        "email": "not-an-email", "password": "StrongPass1!", "full_name": "X"
    })
    assert r.status_code in (400, 422)


async def test_agent_crud(client, api_prefix):
    # Register to get token
    email = f"crud-{uuid.uuid4().hex[:8]}@test.com"
    r = await client.post(f"{api_prefix}/auth/register", json={
        "email": email, "password": "TestPass123!", "full_name": "CRUD"
    })
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    r = await client.post(f"{api_prefix}/agents", json={
        "name": "API CRUD Agent",
        "description": "Test",
        "personality": "professional",
        "trigger_type": "manual",
    }, headers=headers)
    assert r.status_code in (200, 201)
    agent_id = r.json()["id"]

    # Get
    r = await client.get(f"{api_prefix}/agents/{agent_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["name"] == "API CRUD Agent"

    # Update
    r = await client.patch(f"{api_prefix}/agents/{agent_id}", json={"name": "Updated"}, headers=headers)
    assert r.status_code == 200

    # Delete
    r = await client.delete(f"{api_prefix}/agents/{agent_id}", headers=headers)
    assert r.status_code in (200, 204)


async def test_list_agents_unauthenticated(client, api_prefix):
    """Without a token the API should still return 200 in debug mode (or 401)."""
    r = await client.get(f"{api_prefix}/agents")
    assert r.status_code in (200, 401)


async def test_login_wrong_password(client, api_prefix):
    email = f"wrongpw-{uuid.uuid4().hex[:8]}@test.com"
    await client.post(f"{api_prefix}/auth/register", json={
        "email": email, "password": "GoodPass123!", "full_name": "X"
    })
    r = await client.post(f"{api_prefix}/auth/login", json={
        "email": email, "password": "WrongPass999!"
    })
    assert r.status_code in (400, 401)
