"""HTTP security headers middleware.

Applies a baseline set of security-related response headers to every
response. HSTS is only emitted on HTTPS requests so local HTTP development
is not affected.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.anthropic.com https://api.openai.com; "
        "frame-ancestors 'none'"
    ),
}

HSTS_HEADER_VALUE = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds baseline HTTP security headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value

        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = HSTS_HEADER_VALUE

        return response
