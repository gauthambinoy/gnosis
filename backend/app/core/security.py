"""Security middleware for the Gnosis platform.

Provides rate limiting, security headers, request logging,
and basic input sanitization at the middleware layer.
"""

import re
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("gnosis.security")

# Patterns commonly used in injection attacks
INJECTION_PATTERNS = [
    re.compile(r"<script\b", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),  # onerror=, onclick=, etc.
    re.compile(
        r"(\b(union|select|insert|update|delete|drop|alter)\b.*\b(from|into|table|set)\b)",
        re.IGNORECASE,
    ),
    re.compile(r"--\s*$"),  # SQL comment at end
    re.compile(r";\s*(drop|delete|update|insert)\b", re.IGNORECASE),
]


def _contains_injection(value: str) -> bool:
    """Return True if value matches a known injection pattern."""
    for pattern in INJECTION_PATTERNS:
        if pattern.search(value):
            return True
    return False


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security headers + rate limiting + request logging."""

    def __init__(self, app, rate_limit: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds
        self.request_counts: dict[str, dict] = {}  # ip → {count, window_start}

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, ip: str) -> bool:
        now = time.time()
        entry = self.request_counts.get(ip)

        if entry is None or (now - entry["window_start"]) > self.window_seconds:
            self.request_counts[ip] = {"count": 1, "window_start": now}
            return False

        entry["count"] += 1
        return entry["count"] > self.rate_limit

    def _check_query_params(self, request: Request) -> str | None:
        """Return the offending param name if injection detected, else None."""
        for key, value in request.query_params.items():
            if _contains_injection(value):
                return key
        return None

    def _add_security_headers(self, response: Response) -> None:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        client_ip = self._get_client_ip(request)

        # Rate limiting
        if self._is_rate_limited(client_ip):
            logger.warning("Rate limit exceeded for %s", client_ip)
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                media_type="application/json",
            )

        # Sanitize query params for injection patterns
        bad_param = self._check_query_params(request)
        if bad_param:
            logger.warning(
                "Injection attempt in param '%s' from %s", bad_param, client_ip
            )
            return Response(
                content='{"detail":"Invalid query parameter."}',
                status_code=400,
                media_type="application/json",
            )

        # Process request
        response = await call_next(request)

        # Security headers
        self._add_security_headers(response)

        # Request timing
        elapsed_ms = (time.time() - start) * 1000
        logger.info(
            "%s %s %s %.1fms %s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            client_ip,
        )

        return response
