"""Unit tests for the Python SDK (`gnosis_sdk`).

Covers retries, error classification, and Retry-After handling. Uses
``httpx.MockTransport`` so no real network is touched.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

# Make `sdk/python/gnosis_sdk` importable without packaging.
_SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "python"
sys.path.insert(0, str(_SDK_PATH))

from gnosis_sdk.client import (  # noqa: E402
    GnosisAuthError,
    GnosisClient,
    GnosisError,
    GnosisNetworkError,
    GnosisNotFoundError,
    GnosisRateLimitError,
    GnosisServerError,
)


def _client_with(transport: httpx.MockTransport, **kwargs) -> GnosisClient:
    """Build a SDK client whose internal httpx.Client uses the mock transport."""
    c = GnosisClient("http://api.test", **kwargs)
    c._client.close()
    c._client = httpx.Client(transport=transport, timeout=5)
    # Avoid actually sleeping during retry tests
    c._sleep_for_attempt = lambda *_a, **_k: None  # type: ignore[assignment]
    return c


def test_success_returns_json_body():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    c = _client_with(httpx.MockTransport(handler))
    assert c._get("/api/v1/anything") == {"ok": True}


def test_204_returns_none():
    c = _client_with(httpx.MockTransport(lambda req: httpx.Response(204)))
    assert c._delete("/x") is None


@pytest.mark.parametrize(
    "status,exc_type",
    [
        (401, GnosisAuthError),
        (403, GnosisAuthError),
        (404, GnosisNotFoundError),
        (409, GnosisError),
        (500, GnosisServerError),
    ],
)
def test_error_classification(status, exc_type):
    def handler(req):
        return httpx.Response(status, json={"detail": "x"})

    c = _client_with(httpx.MockTransport(handler), max_retries=0)
    with pytest.raises(exc_type) as ei:
        c._get("/x")
    assert ei.value.status_code == status


def test_429_carries_retry_after():
    def handler(req):
        return httpx.Response(429, headers={"Retry-After": "2"}, json={"detail": "slow"})

    c = _client_with(httpx.MockTransport(handler), max_retries=0)
    with pytest.raises(GnosisRateLimitError) as ei:
        c._get("/x")
    assert ei.value.retry_after == 2.0


def test_get_retries_on_500_then_succeeds():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(500, json={"detail": "boom"})
        return httpx.Response(200, json={"ok": True})

    c = _client_with(httpx.MockTransport(handler), max_retries=3)
    assert c._get("/x") == {"ok": True}
    assert calls["n"] == 3


def test_post_does_not_retry_on_500():
    """POST may not be idempotent — retries are unsafe by default."""
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(500, json={"detail": "boom"})

    c = _client_with(httpx.MockTransport(handler), max_retries=3)
    with pytest.raises(GnosisServerError):
        c._post("/x", {})
    assert calls["n"] == 1


def test_network_error_is_retried_for_idempotent_verbs():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] < 2:
            raise httpx.ConnectError("nope", request=req)
        return httpx.Response(200, json={"ok": True})

    c = _client_with(httpx.MockTransport(handler), max_retries=2)
    assert c._get("/x") == {"ok": True}
    assert calls["n"] == 2


def test_network_error_on_post_raises_immediately():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        raise httpx.ConnectError("nope", request=req)

    c = _client_with(httpx.MockTransport(handler), max_retries=3)
    with pytest.raises(GnosisNetworkError):
        c._post("/x", {})
    assert calls["n"] == 1


def test_login_sets_token():
    def handler(req):
        return httpx.Response(200, json={"access_token": "abc-123"})

    c = _client_with(httpx.MockTransport(handler))
    c.login("u@x", "pw")
    assert c._token == "abc-123"
    assert c._headers()["Authorization"] == "Bearer abc-123"


def test_context_manager_closes_client():
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json={}))
    with _client_with(transport) as c:
        assert c._client is not None
    # httpx marks the client as closed via .is_closed
    assert c._client.is_closed
