"""Additional unit tests for WebhookDispatcher (HMAC, dispatch, deliveries)."""

import hmac
import hashlib
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.core.webhook_dispatcher import WebhookDispatcher


@pytest.fixture
def wd():
    return WebhookDispatcher()


@pytest.mark.anyio
async def test_dispatch_no_matching_endpoints_noop(wd):
    # Should not raise even when no endpoints registered
    await wd.dispatch("execution.completed", {})


@pytest.mark.anyio
async def test_dispatch_calls_httpx_post(wd):
    ep = wd.register("https://example.com/h", ["execution.completed"], secret="s")

    mock_resp = MagicMock(status_code=200)
    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        await wd.dispatch("execution.completed", {"x": 1})

    assert mock_client.post.await_count == 1
    args, kwargs = mock_client.post.call_args
    # url is first positional arg
    assert args[0] == "https://example.com/h"
    headers = kwargs["headers"]
    assert headers["X-Gnosis-Event"] == "execution.completed"
    sig_header = headers["X-Gnosis-Signature"]
    assert sig_header.startswith("sha256=")
    body = kwargs["content"]
    expected = hmac.new(b"s", body.encode(), hashlib.sha256).hexdigest()
    assert sig_header == f"sha256={expected}"
    deliveries = wd.get_deliveries(endpoint_id=ep.id)
    assert deliveries[0]["status"] == "delivered"


@pytest.mark.anyio
async def test_dispatch_failure_increments_count(wd):
    ep = wd.register("https://example.com/h", ["*"])

    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=Exception("net down"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        await wd.dispatch("anything", {})

    assert ep.failure_count == 1
    deliveries = wd.get_deliveries(endpoint_id=ep.id)
    assert deliveries[0]["status"] == "failed"


@pytest.mark.anyio
async def test_dispatch_filters_inactive(wd):
    ep = wd.register("https://example.com/h", ["*"])
    ep.active = False
    mock_client = MagicMock()
    mock_client.post = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=mock_client):
        await wd.dispatch("evt", {})
    mock_client.post.assert_not_awaited()


def test_register_and_unregister(wd):
    ep = wd.register("https://x", ["*"])
    assert wd.unregister(ep.id) is True
    assert wd.unregister(ep.id) is False


def test_stats_shape(wd):
    wd.register("https://a", ["*"])
    s = wd.stats
    assert s["total_endpoints"] == 1
    assert s["active_endpoints"] == 1
