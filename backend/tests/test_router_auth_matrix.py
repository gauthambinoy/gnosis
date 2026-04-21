"""Regression test — every endpoint in ``app/api/`` must either declare an auth
dependency or be explicitly listed in ``PUBLIC_ALLOWLIST`` below.

This fails loudly when someone adds a new unauthenticated endpoint, forcing a
reviewer decision.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

API_DIR = pathlib.Path(__file__).resolve().parent.parent / "app" / "api"

# (router_file_name, http_method_upper, path_string) — every entry must be
# justified with a ``# PUBLIC: …`` comment in the router source as well.
PUBLIC_ALLOWLIST: set[tuple[str, str, str]] = {
    # Health & liveness probes (required by load balancers/uptime monitors).
    ("health.py", "GET", "/health"),
    ("health.py", "GET", "/health/ready"),
    ("health.py", "GET", "/health/live"),
    ("health.py", "GET", "/health/deep"),
    ("health.py", "GET", "/health/detailed"),
    ("health_check.py", "GET", "/health"),
    ("health_check.py", "GET", "/health/detailed"),
    ("health_check.py", "GET", "/health/live"),
    ("health_check.py", "GET", "/health/ready"),
    # PWA bootstrap — must load pre-login.
    ("pwa.py", "GET", "/manifest"),
    ("pwa.py", "GET", "/config"),
    # Anonymous feedback submission (uses optional bearer).
    ("feedback.py", "POST", ""),
    # Marketplace public browse surface.
    ("marketplace.py", "GET", "/categories"),
    ("marketplace.py", "GET", "/browse"),
    ("marketplace.py", "GET", "/stats"),
    ("marketplace.py", "GET", "/{agent_id}"),
    ("marketplace.py", "GET", "/{agent_id}/reviews"),
    # Template catalog browse.
    ("templates.py", "GET", ""),
    ("templates.py", "GET", "/{template_id}"),
    # Auto-API public catalog (no secrets).
    ("auto_api.py", "GET", "/catalog"),
    ("auto_api.py", "GET", "/catalog/{name}"),
    ("auto_api.py", "GET", "/search"),
    ("auto_api.py", "GET", "/categories"),
    # Billing pricing page.
    ("billing.py", "GET", "/plans"),
    # SSO / OAuth initiation and provider-driven callbacks.
    ("sso.py", "GET", "/providers"),
    ("sso.py", "POST", "/authorize"),
    ("sso.py", "POST", "/callback"),
    ("integrations.py", "GET", "/{provider}/callback"),
    # Pre-login CSRF token.
    ("security_dashboard.py", "GET", "/csrf-token"),
    # External webhook invocation (HMAC-protected).
    ("webhook_triggers.py", "POST", "/trigger/{trigger_id}"),
    # Internal marketplace browse.
    ("internal_marketplace.py", "GET", "/"),
    ("internal_marketplace.py", "GET", "/{listing_id}"),
    # Auth endpoints — by definition must be reachable without a token.
    ("auth.py", "POST", "/register"),
    ("auth.py", "POST", "/login"),
    ("auth.py", "POST", "/refresh"),
}

AUTH_DEP_NAMES = {"get_current_user_id", "require_auth", "get_optional_user_id"}
ROUTER_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def _iter_router_files() -> list[pathlib.Path]:
    return sorted(
        p for p in API_DIR.glob("*.py") if p.name not in {"__init__.py"}
    )


def _endpoint_has_auth(func: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    """Return True if any argument of ``func`` is ``Depends(<auth-dep>)``."""
    for arg in list(func.args.args) + list(func.args.kwonlyargs):
        pass  # args carry no defaults; defaults are on func.args.defaults
    # We walk all default values (positional + kw-only) looking for a Depends() call
    # whose callable is one of AUTH_DEP_NAMES.
    defaults = list(func.args.defaults) + list(func.args.kw_defaults)
    for default in defaults:
        if default is None:
            continue
        if not isinstance(default, ast.Call):
            continue
        if not (
            isinstance(default.func, ast.Name) and default.func.id == "Depends"
        ):
            continue
        if not default.args:
            continue
        target = default.args[0]
        if isinstance(target, ast.Name) and target.id in AUTH_DEP_NAMES:
            return True
        if isinstance(target, ast.Attribute) and target.attr in AUTH_DEP_NAMES:
            return True
    return False


def _collect_endpoints(
    path: pathlib.Path,
) -> list[tuple[str, str, ast.AsyncFunctionDef | ast.FunctionDef]]:
    """Return [(http_method_upper, path_string, func_node), …] for ``path``."""
    tree = ast.parse(path.read_text(), filename=str(path))
    endpoints: list[tuple[str, str, ast.AsyncFunctionDef | ast.FunctionDef]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            if not isinstance(deco.func, ast.Attribute):
                continue
            method = deco.func.attr
            if method not in ROUTER_METHODS:
                continue
            # Only care about @router.<method>(...) / @some_router.<method>(...)
            if not deco.args:
                continue
            first = deco.args[0]
            if not isinstance(first, ast.Constant) or not isinstance(
                first.value, str
            ):
                continue
            endpoints.append((method.upper(), first.value, node))
    return endpoints


def _build_cases() -> list[tuple[str, str, str, bool]]:
    cases: list[tuple[str, str, str, bool]] = []
    for path in _iter_router_files():
        for method, route, func in _collect_endpoints(path):
            cases.append(
                (path.name, method, route, _endpoint_has_auth(func))
            )
    return cases


_CASES = _build_cases()


def test_cases_collected() -> None:
    """Sanity check — the test must actually discover endpoints."""
    assert _CASES, "No router endpoints discovered — check API_DIR path"
    assert len(_CASES) > 100, f"Only {len(_CASES)} endpoints discovered"


@pytest.mark.parametrize(
    ("router_file", "method", "route", "has_auth"),
    _CASES,
    ids=[f"{f}::{m} {r}" for (f, m, r, _) in _CASES],
)
def test_endpoint_has_auth_or_is_public(
    router_file: str, method: str, route: str, has_auth: bool
) -> None:
    """Every endpoint must declare auth OR be on the public allowlist."""
    if has_auth:
        return
    key = (router_file, method, route)
    assert key in PUBLIC_ALLOWLIST, (
        f"Endpoint {method} {route} in {router_file} has no auth dependency "
        f"and is not in PUBLIC_ALLOWLIST. Either add "
        f"`user_id: str = Depends(get_current_user_id)` to the signature, "
        f"or add the tuple {key!r} to PUBLIC_ALLOWLIST with a justification "
        f"(and a `# PUBLIC: …` comment in the router source)."
    )


def test_allowlist_has_no_stale_entries() -> None:
    """PUBLIC_ALLOWLIST entries must correspond to real endpoints."""
    real = {(f, m, r) for (f, m, r, _) in _CASES}
    stale = PUBLIC_ALLOWLIST - real
    assert not stale, f"Stale PUBLIC_ALLOWLIST entries: {sorted(stale)}"
