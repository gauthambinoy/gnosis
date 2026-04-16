"""Shared HTTP client with connection pooling for outbound requests."""

import httpx
from typing import Optional
from app.core.logger import get_logger

logger = get_logger("http_client")

_client: Optional[httpx.AsyncClient] = None


async def init_http_client() -> None:
    """Create the shared httpx session. Call once during app startup."""
    global _client
    if _client is not None and not _client.is_closed:
        return
    _client = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=30.0,
        ),
        follow_redirects=True,
        headers={"User-Agent": "Gnosis/1.0"},
    )
    logger.info("http_client_created")


async def close_http_client() -> None:
    """Close the shared session. Call during app shutdown."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        logger.info("http_client_closed")
        _client = None


def get_http_client() -> httpx.AsyncClient:
    """Return the shared httpx client. Raises if not yet initialised."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0,
            ),
            follow_redirects=True,
            headers={"User-Agent": "Gnosis/1.0"},
        )
        logger.info("http_client_created")
    return _client
