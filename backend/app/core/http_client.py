"""Shared HTTP client with connection pooling for outbound requests."""

import asyncio
import httpx
from typing import Optional
from app.core.logger import get_logger

logger = get_logger("http_client")

_client: Optional[httpx.AsyncClient] = None
_init_lock: asyncio.Lock = asyncio.Lock()


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=30.0,
        ),
        follow_redirects=True,
        headers={"User-Agent": "Gnosis/1.0"},
    )


async def init_http_client() -> None:
    """Create the shared httpx session. Call once during app startup."""
    global _client
    async with _init_lock:
        if _client is not None and not _client.is_closed:
            return
        _client = _build_client()
        logger.info("http_client_created")


async def close_http_client() -> None:
    """Close the shared session. Call during app shutdown."""
    global _client
    async with _init_lock:
        if _client and not _client.is_closed:
            await _client.aclose()
            logger.info("http_client_closed")
            _client = None


def get_http_client() -> httpx.AsyncClient:
    """Return the shared httpx client.

    Eagerly creates one if not yet initialised. The creation itself is
    a single synchronous operation (no awaits inside ``_build_client``),
    so under a single asyncio event loop two concurrent first-callers
    cannot race past the ``is None`` check before the assignment lands.
    For belt-and-braces safety against multiple event loops or threaded
    callers, prefer ``init_http_client()`` at startup.
    """
    global _client
    if _client is None or _client.is_closed:
        _client = _build_client()
        logger.info("http_client_created")
    return _client
