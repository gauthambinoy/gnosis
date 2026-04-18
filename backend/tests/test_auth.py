"""Tests for auth endpoints: register, login, refresh."""

import uuid

import pytest

pytestmark = pytest.mark.anyio


async def test_register_success(client, api_prefix):
    email = f"reg-{uuid.uuid4().hex[:8]}@gnosis.ai"
    resp = await client.post(
        f"{api_prefix}/auth/register",
        json={"email": email, "password": "StrongPass1!", "full_name": "Alice"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == email
    assert data["user"]["full_name"] == "Alice"


async def test_register_duplicate(client, api_prefix):
    email = f"dup-{uuid.uuid4().hex[:8]}@gnosis.ai"
    payload = {"email": email, "password": "StrongPass1!", "full_name": "Bob"}
    resp1 = await client.post(f"{api_prefix}/auth/register", json=payload)
    assert resp1.status_code == 201
    resp2 = await client.post(f"{api_prefix}/auth/register", json=payload)
    assert resp2.status_code == 400


async def test_login_success(client, api_prefix, registered_user):
    resp = await client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == registered_user["email"]
    assert "access_token" in data


async def test_login_wrong_password(client, api_prefix, registered_user):
    resp = await client.post(
        f"{api_prefix}/auth/login",
        json={"email": registered_user["email"], "password": "WrongPassword!"},
    )
    assert resp.status_code == 401


async def test_login_nonexistent(client, api_prefix):
    resp = await client.post(
        f"{api_prefix}/auth/login",
        json={"email": "nobody@nowhere.com", "password": "Whatever1!"},
    )
    assert resp.status_code == 401


async def test_refresh_token(client, api_prefix, registered_user):
    resp = await client.post(
        f"{api_prefix}/auth/refresh",
        json={"refresh_token": registered_user["refresh_token"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    # New access token issued successfully
    assert len(data["access_token"]) > 20
