"""Gnosis Auto-API Discovery — Connect to any API by name."""

import ipaddress
import logging
import os
import socket
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional
from app.core.auto_api import auto_api
from app.core.auth import get_current_user_id
from app.core.rate_limiter import rate_limiter
from app.core.error_handling import (
    ForbiddenError,
    RateLimitError,
    ValidationError,
)
from app.config import get_settings

logger = logging.getLogger("gnosis.auto_api")
_settings = get_settings()

router = APIRouter(prefix="/api/v1/apis", tags=["auto-api"])


# ─── Security helpers ───


_AUTO_API_CALL_LIMIT_PER_MIN = 30


def _allowed_hosts() -> set[str]:
    """Read GNOSIS_AUTO_API_ALLOWED_HOSTS at call time (test-friendly)."""
    raw = os.environ.get("GNOSIS_AUTO_API_ALLOWED_HOSTS") or getattr(
        _settings, "auto_api_allowed_hosts", ""
    )
    return {h.strip().lower() for h in (raw or "").split(",") if h.strip()}


def _is_private_ip(host: str) -> bool:
    """Resolve host and reject private/loopback/link-local/multicast IPs."""
    try:
        # Direct IP literal
        ip = ipaddress.ip_address(host)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        # Unresolvable host — reject as a precaution
        return True
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr.split("%")[0])
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return True
    return False


def _enforce_outbound_call_security(target_url: str, user_id: str) -> None:
    """Validate that the outbound URL is allowed: host whitelist + private-IP block."""
    parsed = urlparse(target_url)
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValidationError("Invalid target URL: missing host")

    if _is_private_ip(host):
        logger.warning(
            "auto_api blocked private/loopback host '%s' for user %s", host, user_id
        )
        raise ForbiddenError("Outbound calls to private/loopback addresses are blocked")

    allowed = _allowed_hosts()
    if not allowed:
        if _settings.debug:
            logger.warning(
                "GNOSIS_AUTO_API_ALLOWED_HOSTS is empty — allowing host '%s' "
                "ONLY because DEBUG=true. Set the env var before deploying.",
                host,
            )
            return
        raise ForbiddenError(
            "Auto-API outbound calls are disabled: set GNOSIS_AUTO_API_ALLOWED_HOSTS"
        )

    # Allow exact match or subdomain match
    if host in allowed:
        return
    for allowed_host in allowed:
        if host.endswith("." + allowed_host):
            return
    raise ForbiddenError(f"Host '{host}' is not in GNOSIS_AUTO_API_ALLOWED_HOSTS")


def _enforce_call_rate_limit(user_id: str) -> None:
    result = rate_limiter.check(
        f"auto_api_call:{user_id}", limit=_AUTO_API_CALL_LIMIT_PER_MIN
    )
    if not result["allowed"]:
        raise RateLimitError(
            "Auto-API call rate limit exceeded",
            detail=result,
        )


# ─── Request Models ───


class ConnectRequest(BaseModel):
    api_name: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1, max_length=500)
    extra_config: Optional[dict] = None


class CallAPIRequest(BaseModel):
    endpoint_path: str = Field(min_length=1)
    method: str = Field(default="GET")
    body: Optional[dict] = None
    params: Optional[dict] = None


# ─── Catalog ───


# PUBLIC: read-only public catalog of known APIs; no user data
@router.get("/catalog")
async def list_catalog(category: Optional[str] = Query(None)):
    """List all known APIs in the catalog."""
    apis = auto_api.list_catalog(category=category or "")
    return {"apis": apis, "count": len(apis)}


# PUBLIC: read-only catalog entry metadata
@router.get("/catalog/{name}")
async def get_api_info(name: str):
    """Get detailed info about a specific API."""
    info = auto_api.get_api_info(name)
    if not info:
        raise HTTPException(
            status_code=404, detail=f"API '{name}' not found in catalog"
        )
    return info


# PUBLIC: read-only catalog search
@router.get("/search")
async def search_apis(q: str = Query(..., min_length=1, description="Search query")):
    """Search APIs by name, description, or category."""
    results = auto_api.search_api(q)
    return {"results": results, "count": len(results)}


# PUBLIC: read-only catalog categories
@router.get("/categories")
async def list_categories():
    """List all API categories."""
    categories = auto_api.get_categories()
    return {"categories": sorted(categories)}


# ─── Connections ───


@router.post("/connect")
async def connect_api(req: ConnectRequest, user_id: str = Depends(get_current_user_id)):
    """Connect to an API with credentials."""
    result = auto_api.connect(req.api_name, req.api_key, req.extra_config)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/connections")
async def list_connections(user_id: str = Depends(get_current_user_id)):
    """List all API connections."""
    connections = auto_api.list_connections()
    # Mask API keys in response
    for c in connections:
        if c.get("api_key"):
            c["api_key"] = c["api_key"][:4] + "***"
    return {"connections": connections, "count": len(connections)}


@router.get("/connections/{connection_id}")
async def get_connection(connection_id: str, user_id: str = Depends(get_current_user_id)):
    """Get a specific connection (key masked)."""
    conn = auto_api.get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn


@router.post("/connections/{connection_id}/test")
async def test_connection(connection_id: str, user_id: str = Depends(get_current_user_id)):
    """Test an API connection."""
    result = await auto_api.test_connection(connection_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/connections/{connection_id}/call")
async def call_api(
    connection_id: str,
    req: CallAPIRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Make an API call through a connection."""
    _enforce_call_rate_limit(user_id)

    conn = auto_api.get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    base_url = conn.get("base_url") or ""
    target_url = f"{base_url}{req.endpoint_path}"
    _enforce_outbound_call_security(target_url, user_id)

    result = await auto_api.call_api(
        connection_id, req.endpoint_path, req.method, req.body, req.params
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: str, user_id: str = Depends(get_current_user_id)):
    """Delete an API connection."""
    removed = auto_api.delete_connection(connection_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"status": "deleted", "connection_id": connection_id}


# ─── Code Generation ───


@router.get("/generate/{name}")
async def generate_connector(name: str, user_id: str = Depends(get_current_user_id)):
    """Generate a Python connector class for an API."""
    code = auto_api.generate_connector_code(name)
    if not code:
        raise HTTPException(status_code=404, detail=f"API '{name}' not found")
    return {"api": name, "language": "python", "code": code}


# ─── Stats ───


@router.get("/stats")
async def get_stats(user_id: str = Depends(get_current_user_id)):
    """Get Auto-API engine statistics."""
    return auto_api.get_stats()
