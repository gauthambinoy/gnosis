"""Tests for SecurityHeadersMiddleware: ensures baseline security headers
are applied to every response."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.security_headers import (
    HSTS_HEADER_VALUE,
    SECURITY_HEADERS,
    SecurityHeadersMiddleware,
)


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return app


def test_security_headers_present_on_get():
    client = TestClient(_build_app())
    resp = client.get("/ping")
    assert resp.status_code == 200
    for name, value in SECURITY_HEADERS.items():
        assert resp.headers.get(name) == value, f"missing/incorrect header: {name}"


def test_hsts_absent_on_http():
    client = TestClient(_build_app())
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert "strict-transport-security" not in {k.lower() for k in resp.headers.keys()}


def test_hsts_present_on_https():
    # TestClient lets us set the URL scheme via base_url.
    client = TestClient(_build_app(), base_url="https://testserver")
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.headers.get("Strict-Transport-Security") == HSTS_HEADER_VALUE


def test_csp_includes_frame_ancestors_none():
    client = TestClient(_build_app())
    resp = client.get("/ping")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors 'none'" in csp
    assert "default-src 'self'" in csp


def test_x_frame_options_deny():
    client = TestClient(_build_app())
    resp = client.get("/ping")
    assert resp.headers.get("X-Frame-Options") == "DENY"
