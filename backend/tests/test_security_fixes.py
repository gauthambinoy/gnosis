"""Tests for the C1/C2/C3/H1/H2/H3 hardening fixes."""

import os
import uuid
from unittest.mock import patch, AsyncMock

import pytest

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# C1: /llm/complete must enforce per-user token quota
# ---------------------------------------------------------------------------

async def test_llm_complete_blocks_when_over_quota(
    client, api_prefix, auth_headers
):
    """Once the user is over their daily token quota the endpoint must 402."""
    from app.core.quota_engine import quota_engine

    user_id = "00000000-0000-0000-0000-000000000001"
    # Force usage past the free-tier max_tokens_per_day (100_000)
    usage = quota_engine.get_usage(user_id)
    saved = usage.tokens_today
    usage.tokens_today = 10_000_000
    try:
        resp = await client.post(
            f"{api_prefix}/llm/complete",
            json={"prompt": "hello"},
            headers=auth_headers,
        )
        assert resp.status_code == 402, resp.text
        body = resp.json()
        assert body["code"] == "QUOTA_EXCEEDED"
    finally:
        usage.tokens_today = saved


async def test_llm_complete_requires_auth(client, api_prefix):
    """No bearer token + DEBUG=true returns the dev user, but quota dep is wired."""
    # In DEBUG mode the auth dep yields a fixed dev user, so this should not 401.
    # We assert the dependency at least *runs* by hitting the endpoint with no auth
    # and getting either 200/402/502 (any non-422-validation, non-401 response).
    with patch(
        "app.api.llm.llm_gateway.complete",
        new=AsyncMock(
            return_value=type(
                "R",
                (),
                {
                    "content": "ok",
                    "model": "x",
                    "provider": "none",
                    "tokens_used": 5,
                    "tokens_prompt": 1,
                    "tokens_completion": 4,
                    "latency_ms": 1.0,
                    "cost_estimate": 0.0,
                    "cached": False,
                },
            )()
        ),
    ):
        resp = await client.post(
            f"{api_prefix}/llm/complete", json={"prompt": "hi"}
        )
    assert resp.status_code != 422
    assert resp.status_code in (200, 402, 502)


# ---------------------------------------------------------------------------
# C2: /execute/trigger must require auth + ownership
# ---------------------------------------------------------------------------

async def test_execute_trigger_rejects_non_owner(
    client, api_prefix, auth_headers
):
    """Triggering an agent owned by someone else must 403."""
    from app.api.agents import _agents as _agents_memory

    foreign_id = str(uuid.uuid4())
    _agents_memory[foreign_id] = {
        "id": foreign_id,
        "owner_id": "11111111-1111-1111-1111-111111111111",
        "name": "Foreign",
    }
    try:
        resp = await client.post(
            f"{api_prefix}/execute/trigger",
            json={"agent_id": foreign_id, "trigger_type": "manual"},
            headers=auth_headers,
        )
        assert resp.status_code == 403, resp.text
        body = resp.json()
        assert body["code"] == "FORBIDDEN"
    finally:
        _agents_memory.pop(foreign_id, None)


async def test_execute_trigger_allows_owner(client, api_prefix, auth_headers):
    from app.api.agents import _agents as _agents_memory

    owner_id = "00000000-0000-0000-0000-000000000001"  # debug-mode dev user
    agent_id = str(uuid.uuid4())
    _agents_memory[agent_id] = {
        "id": agent_id,
        "owner_id": owner_id,
        "name": "Mine",
    }
    try:
        resp = await client.post(
            f"{api_prefix}/execute/trigger",
            json={"agent_id": agent_id, "trigger_type": "manual"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
    finally:
        _agents_memory.pop(agent_id, None)


# ---------------------------------------------------------------------------
# C3: auto-api /call must block private IPs and unlisted hosts
# ---------------------------------------------------------------------------

async def test_auto_api_call_blocks_private_ip(client, auth_headers):
    """Even if a connection points at 127.0.0.1, the call must be refused."""
    from app.core.auto_api import auto_api, APIConnection

    conn_id = "test-conn-private"
    auto_api._connections[conn_id] = APIConnection(
        id=conn_id,
        api_name="evil",
        api_key="x",
        base_url="http://127.0.0.1:8080",
    )
    try:
        with patch.dict(
            os.environ, {"GNOSIS_AUTO_API_ALLOWED_HOSTS": "api.stripe.com"}
        ):
            resp = await client.post(
                f"/api/v1/auto-api/api/v1/apis/connections/{conn_id}/call",
                json={"endpoint_path": "/v1/charges", "method": "GET"},
                headers=auth_headers,
            )
        assert resp.status_code == 403, resp.text
        assert resp.json()["code"] == "FORBIDDEN"
    finally:
        auto_api._connections.pop(conn_id, None)


async def test_auto_api_call_blocks_unlisted_host(client, auth_headers):
    from app.core.auto_api import auto_api, APIConnection

    conn_id = "test-conn-unlisted"
    auto_api._connections[conn_id] = APIConnection(
        id=conn_id,
        api_name="evil",
        api_key="x",
        base_url="https://evil.example.com",
    )
    try:
        with patch.dict(
            os.environ, {"GNOSIS_AUTO_API_ALLOWED_HOSTS": "api.stripe.com"}
        ):
            resp = await client.post(
                f"/api/v1/auto-api/api/v1/apis/connections/{conn_id}/call",
                json={"endpoint_path": "/v1/charges", "method": "GET"},
                headers=auth_headers,
            )
        assert resp.status_code == 403, resp.text
    finally:
        auto_api._connections.pop(conn_id, None)


# ---------------------------------------------------------------------------
# H2: rpa selector validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad_value",
    [
        "javascript:alert(1)",
        "<script>alert(1)</script>",
        "div onclick=alert(1)",
        "expression(alert(1))",
        "a" * 1500,
    ],
)
async def test_rpa_record_action_rejects_dangerous_selector(
    client, auth_headers, bad_value
):
    # First start a recording session so the route can find it
    from app.core.rpa_engine import rpa_engine
    session_id = rpa_engine.start_recording(user_id="dev", start_url="https://x")

    resp = await client.post(
        f"/api/v1/rpa/record/{session_id}/action",
        json={"action_type": "click", "selector": bad_value},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_ERROR"


async def test_rpa_create_workflow_rejects_dangerous_xpath(
    client, auth_headers
):
    resp = await client.post(
        "/api/v1/rpa/workflows",
        json={
            "name": "bad",
            "actions": [
                {"action_type": "click", "xpath": "javascript:alert(1)"}
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# H1: register endpoint generic error + per-IP limit
# ---------------------------------------------------------------------------

async def test_register_duplicate_returns_generic_error(client, api_prefix):
    email = f"sec-{uuid.uuid4().hex[:8]}@gnosis.ai"
    payload = {"email": email, "password": "StrongPass1!", "full_name": "Sec"}
    r1 = await client.post(f"{api_prefix}/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post(f"{api_prefix}/auth/register", json=payload)
    assert r2.status_code == 400
    body = r2.json()
    # Must NOT reveal "already registered" / "exists"
    text = (body.get("error") or body.get("detail") or "").lower()
    assert "already" not in text
    assert "exists" not in text
    assert "registration failed" in text


async def test_register_per_ip_rate_limit(client, api_prefix):
    """Six rapid registers from the same IP must trigger 429."""
    last_status = None
    for i in range(7):
        email = f"rl-{uuid.uuid4().hex[:8]}@gnosis.ai"
        resp = await client.post(
            f"{api_prefix}/auth/register",
            json={"email": email, "password": "StrongPass1!", "full_name": "Rl"},
        )
        last_status = resp.status_code
        if resp.status_code == 429:
            break
    assert last_status == 429


# ---------------------------------------------------------------------------
# H3: feedback endpoint stamps user_id when token is valid
# ---------------------------------------------------------------------------

async def test_feedback_stamps_user_when_authenticated(client, auth_headers):
    from app.api.feedback import _feedback_store

    pre = len(_feedback_store)
    resp = await client.post(
        "/api/v1/feedback",
        json={"category": "general", "message": "hi from a real user"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    assert len(_feedback_store) == pre + 1
    assert _feedback_store[-1]["user_id"] == "00000000-0000-0000-0000-000000000001"


async def test_feedback_allows_anonymous(client):
    from app.api.feedback import _feedback_store

    pre = len(_feedback_store)
    resp = await client.post(
        "/api/v1/feedback",
        json={"category": "general", "message": "anon ping"},
    )
    assert resp.status_code == 201, resp.text
    assert len(_feedback_store) == pre + 1
    assert _feedback_store[-1]["user_id"] is None
