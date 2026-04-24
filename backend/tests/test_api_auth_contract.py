"""Security contract: every API route under /api/v1 (except an explicit allow
list of public endpoints) MUST require authentication.

This catches the H4 class of bugs where someone forgets
``Depends(get_current_user_id)`` on a new router. It's parametrized over the
live route table, so every newly-added endpoint is automatically covered.
"""

from __future__ import annotations

import re

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(autouse=True)
def _exercise_real_auth(disable_auth_override):
    """The conftest installs a default get_current_user_id override that
    auto-authenticates every request as TEST_USER_ID. The auth contract test
    must clear that override so we exercise the production auth dependency.
    """
    yield


# Endpoints that are intentionally public.
_PUBLIC_PREFIXES = (
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/healthz",
    "/livez",
    "/readyz",
    "/startup",
    "/metrics",
    "/manifest.json",
    "/sw.js",
    "/api/v1/health",
    "/api/v1/pwa",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    # OAuth callback is reached via redirect with a state code; auth happens inside.
    "/api/v1/integrations/google/callback",
    "/api/v1/integrations/slack/callback",
)


_PUBLIC_EXACT = {
    "/api/v1/templates",
    "/api/v1/marketplace/api/v1/marketplace/categories",
    "/api/v1/marketplace/api/v1/marketplace/browse",
    "/api/v1/marketplace/api/v1/marketplace/stats",
    "/api/v1/marketplace/api/v1/marketplace/{agent_id}/reviews",
    "/api/v1/billing/api/v1/billing/plans",
    "/api/v1/auth/sso/providers",
    "/api/v1/security/api/v1/security/csrf-token",
    "/api/v1/auto-api/api/v1/apis/catalog",
    "/api/v1/auto-api/api/v1/apis/categories",
    "/api/v1/internal-marketplace/",
}


def _is_public(path: str) -> bool:
    if path in _PUBLIC_EXACT:
        return True
    if any(path == p or path.startswith(p + "/") or path.startswith(p + "?") for p in _PUBLIC_PREFIXES):
        return True
    if "callback" in path:
        return True
    return False


def _materialize_path(path: str) -> str:
    """Replace `{param}` placeholders with synthetic but valid-looking values."""
    return re.sub(r"\{[^}]+\}", "00000000-0000-0000-0000-000000000000", path)


def _collect_protected_routes() -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for r in app.routes:
        path = getattr(r, "path", "") or ""
        methods = getattr(r, "methods", None) or set()
        if not path.startswith("/api/v1"):
            continue
        if _is_public(path):
            continue
        for m in methods:
            if m in {"HEAD", "OPTIONS"}:
                continue
            key = (m, path)
            if key in seen:
                continue
            seen.add(key)
            out.append(key)
    return out


_ROUTES = _collect_protected_routes()


@pytest.mark.asyncio
@pytest.mark.parametrize("method,template", _ROUTES, ids=[f"{m} {p}" for m, p in _ROUTES])
async def test_protected_route_requires_auth(method: str, template: str):
    """Every /api/v1 route (except the allow list) must reject anonymous calls.

    Acceptable rejection signals:
      - 401 / 403 (auth missing or invalid)
      - 422 (request shape rejected before auth — fine, still not leaking data)
      - 405 (method not allowed on a path-param materialization quirk)
      - 404 (some routers 404 unknown IDs before checking auth — acceptable
        because no data is leaked; the security failure mode we're guarding
        against is 200 OK without credentials).

    Forbidden:
      - 200 / 201 / 204 (success without auth)
      - 500 (unhandled exception path — must be a clean rejection)
    """
    path = _materialize_path(template)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        if method == "GET":
            resp = await ac.get(path)
        elif method == "DELETE":
            resp = await ac.delete(path)
        elif method == "POST":
            resp = await ac.post(path, json={})
        elif method == "PATCH":
            resp = await ac.patch(path, json={})
        elif method == "PUT":
            resp = await ac.put(path, json={})
        else:
            pytest.skip(f"unsupported method {method}")

    assert resp.status_code not in {200, 201, 204}, (
        f"{method} {path} returned {resp.status_code} without auth — "
        f"missing Depends(get_current_user_id)?"
    )
    assert resp.status_code != 500, (
        f"{method} {path} returned 500 without auth — unhandled exception "
        f"in auth path; body={resp.text[:200]}"
    )


def test_some_routes_were_collected():
    """Sanity: ensure the parametrize set is non-empty so a routing
    regression doesn't silently zero out coverage."""
    assert len(_ROUTES) >= 50, f"only {len(_ROUTES)} protected routes found"
