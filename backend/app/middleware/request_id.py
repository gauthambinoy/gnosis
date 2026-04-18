"""Request-ID middleware — generates a unique trace ID for every request."""

from __future__ import annotations

import contextvars
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logger import get_logger

logger = get_logger("request_id")

# Context variable accessible from anywhere during request processing
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)


def get_request_id() -> str:
    """Return the current request's trace ID (empty string outside a request)."""
    return request_id_ctx.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique X-Request-ID to every request/response and log timing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_ctx.set(rid)
        request.state.request_id = rid

        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "%s %s → %s (%.1fms) [%s]",
                request.method,
                request.url.path,
                getattr(response, "status_code", "ERR")
                if "response" in dir()
                else "ERR",
                duration_ms,
                rid,
            )
            request_id_ctx.reset(token)

        response.headers["X-Request-ID"] = rid
        return response
