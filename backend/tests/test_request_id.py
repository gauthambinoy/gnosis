"""Tests for RequestIDMiddleware — header passthrough, auto-generation, format."""

import re

import pytest

pytest_plugins = ["anyio"]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_request_id_passthrough(client):
    """Client-supplied X-Request-ID is echoed back unchanged."""
    resp = await client.get("/health", headers={"X-Request-ID": "abc123"})
    assert resp.headers.get("X-Request-ID") == "abc123"


@pytest.mark.anyio
async def test_request_id_auto_generated(client):
    """Requests without X-Request-ID receive a non-empty generated id."""
    resp = await client.get("/health")
    rid = resp.headers.get("X-Request-ID")
    assert rid, "Expected a non-empty X-Request-ID header in the response"


@pytest.mark.anyio
async def test_request_id_format(client):
    """Auto-generated id matches uuid4.hex format: 32 lowercase hex chars."""
    resp = await client.get("/health")
    rid = resp.headers.get("X-Request-ID", "")
    assert re.fullmatch(r"^[a-f0-9]{32}$", rid), (
        f"X-Request-ID '{rid}' does not match expected uuid4 hex format"
    )
