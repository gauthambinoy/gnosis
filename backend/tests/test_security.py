"""Security tests — injection, XSS, invalid UUIDs, expired tokens."""

import pytest
import uuid
from datetime import timedelta

pytestmark = pytest.mark.anyio


async def _register(client, api_prefix):
    """Helper: register a fresh user, return auth headers."""
    email = f"sec-{uuid.uuid4().hex[:8]}@test.com"
    r = await client.post(
        f"{api_prefix}/auth/register",
        json={"email": email, "password": "TestPass123!", "full_name": "Sec"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_sql_injection_in_agent_name(client, api_prefix):
    headers = await _register(client, api_prefix)
    r = await client.post(
        f"{api_prefix}/agents",
        json={
            "name": "'; DROP TABLE agents;--",
            "description": "test",
            "personality": "professional",
            "trigger_type": "manual",
        },
        headers=headers,
    )
    assert r.status_code in (200, 201)
    # Verify DB still works
    r2 = await client.get(f"{api_prefix}/agents", headers=headers)
    assert r2.status_code == 200


async def test_xss_in_agent_name(client, api_prefix):
    headers = await _register(client, api_prefix)
    r = await client.post(
        f"{api_prefix}/agents",
        json={
            "name": "<script>alert('xss')</script>",
            "description": "test",
            "personality": "professional",
            "trigger_type": "manual",
        },
        headers=headers,
    )
    assert r.status_code in (200, 201)


async def test_invalid_uuid_handled(client, api_prefix):
    headers = await _register(client, api_prefix)
    r = await client.get(f"{api_prefix}/agents/not-a-uuid", headers=headers)
    assert r.status_code in (400, 404, 422)


async def test_expired_token_rejected(client, api_prefix):
    from app.core.auth import create_access_token

    token = create_access_token(
        {"sub": "user-1", "type": "access"},
        expires_delta=timedelta(seconds=-10),
    )
    r = await client.get(
        f"{api_prefix}/agents", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 401


async def test_malformed_bearer_token(client, api_prefix):
    r = await client.get(
        f"{api_prefix}/agents",
        headers={"Authorization": "Bearer not.valid.jwt"},
    )
    assert r.status_code in (401, 403)


async def test_oversized_payload_rejected(client, api_prefix):
    headers = await _register(client, api_prefix)
    r = await client.post(
        f"{api_prefix}/agents",
        json={
            "name": "A" * 100_000,
            "description": "test",
        },
        headers=headers,
    )
    assert r.status_code in (400, 413, 422)


async def test_duplicate_registration(client, api_prefix):
    email = f"dup-{uuid.uuid4().hex[:8]}@test.com"
    payload = {"email": email, "password": "StrongPass1!", "full_name": "Dup"}
    r1 = await client.post(f"{api_prefix}/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post(f"{api_prefix}/auth/register", json=payload)
    assert r2.status_code == 400
