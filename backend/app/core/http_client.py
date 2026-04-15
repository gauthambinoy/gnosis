"""Shared HTTP client with connection pooling for outbound requests."""

import aiohttp
from app.core.logger import get_logger

logger = get_logger("http_client")

_session: aiohttp.ClientSession | None = None


async def init_http_client() -> None:
    """Create the shared aiohttp session. Call once during app startup."""
    global _session
    if _session is not None:
        return
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
    _session = aiohttp.ClientSession(connector=connector)
    logger.info("◎ Shared HTTP client initialised (limit=100, per_host=10)")


async def close_http_client() -> None:
    """Close the shared session. Call during app shutdown."""
    global _session
    if _session is not None:
        await _session.close()
        _session = None
        logger.info("◎ Shared HTTP client closed")


def get_http_client() -> aiohttp.ClientSession:
    """Return the shared session. Raises if not yet initialised."""
    if _session is None:
        raise RuntimeError(
            "HTTP client not initialised – call init_http_client() during startup"
        )
    return _session
