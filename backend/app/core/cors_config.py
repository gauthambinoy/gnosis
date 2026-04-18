"""CORS configuration from environment variables."""

import os
import warnings


def get_cors_origins() -> list:
    """Get CORS origins from environment. Defaults to localhost for dev."""
    origins_str = os.getenv("CORS_ORIGINS", "")
    if origins_str:
        return [o.strip() for o in origins_str.split(",") if o.strip()]
    # Default development origins — warn if used
    debug = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
    if not debug:
        warnings.warn(
            "CORS_ORIGINS not set in production. Set CORS_ORIGINS env var to your frontend domain(s).",
            stacklevel=2,
        )
    return [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]


def get_cors_config() -> dict:
    """Get full CORS middleware config."""
    return {
        "allow_origins": get_cors_origins(),
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "X-Idempotency-Key",
        ],
        "expose_headers": [
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-API-Version",
        ],
        "max_age": 3600,
    }
