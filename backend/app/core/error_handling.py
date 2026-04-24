"""
Unified error handling system for Gnosis.

This module provides:
1. Exception hierarchy (GnosisException and subclasses)
2. Error response model (ErrorResponse)
3. Helper functions (safe_http_error)
4. Exception handlers registration

All three previous modules (error_handlers.py, safe_error.py, error_response.py)
are consolidated here with backwards compatibility maintained.
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logger import get_logger
from app.middleware.request_id import get_request_id

logger = get_logger("gnosis.errors")


# =============================================================================
# Error Response Model
# =============================================================================


class ErrorResponse(BaseModel):
    """Standard error envelope returned by all error handlers."""

    error: str  # Human-readable error message
    code: str  # Machine-readable error code (e.g., NOT_FOUND, VALIDATION_ERROR)
    detail: Any = None  # Additional context (validation details, nested errors)
    trace_id: str = ""  # Request trace ID for debugging
    timestamp: str = ""  # ISO 8601 timestamp

    @classmethod
    def build(
        cls,
        *,
        error: str,
        code: str,
        detail: Any = None,
        trace_id: str = "",
    ) -> dict:
        """Build an error response dict."""
        return cls(
            error=error,
            code=code,
            detail=detail,
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ).model_dump()


# =============================================================================
# Exception Hierarchy
# =============================================================================


class GnosisException(Exception):
    """Base exception for all Gnosis-specific errors."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        *,
        detail: Any = None,
        status_code: int | None = None,
        code: str | None = None,
    ):
        self.message = message
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        super().__init__(message)


class NotFoundError(GnosisException):
    """Resource not found (404)."""

    status_code = 404
    code = "NOT_FOUND"

    def __init__(self, message: str = "Resource not found", **kwargs):
        super().__init__(message, **kwargs)


class ValidationError(GnosisException):
    """Request validation failed (422)."""

    status_code = 422
    code = "VALIDATION_ERROR"

    def __init__(self, message: str = "Validation failed", **kwargs):
        super().__init__(message, **kwargs)


class AuthError(GnosisException):
    """Authentication failed (401)."""

    status_code = 401
    code = "AUTH_ERROR"

    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(message, **kwargs)


class ForbiddenError(GnosisException):
    """Insufficient permissions (403)."""

    status_code = 403
    code = "FORBIDDEN"

    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(message, **kwargs)


class RateLimitError(GnosisException):
    """Rate limit exceeded (429)."""

    status_code = 429
    code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        super().__init__(message, **kwargs)


class LLMError(GnosisException):
    """LLM service error (502)."""

    status_code = 502
    code = "LLM_ERROR"

    def __init__(self, message: str = "LLM service error", **kwargs):
        super().__init__(message, **kwargs)


class ExternalServiceError(GnosisException):
    """External service error (502)."""

    status_code = 502
    code = "EXTERNAL_SERVICE_ERROR"

    def __init__(self, message: str = "External service error", **kwargs):
        super().__init__(message, **kwargs)


class ConflictError(GnosisException):
    """Resource conflict (409)."""

    status_code = 409
    code = "CONFLICT"

    def __init__(self, message: str = "Resource conflict", **kwargs):
        super().__init__(message, **kwargs)


class QuotaExceededError(GnosisException):
    """User quota exceeded (402)."""

    status_code = 402
    code = "QUOTA_EXCEEDED"

    def __init__(self, message: str = "Quota exceeded", **kwargs):
        super().__init__(message, **kwargs)


# =============================================================================
# Legacy Exception Aliases (backwards compatibility)
# =============================================================================


class GnosisError(GnosisException):
    """
    DEPRECATED: Use GnosisException instead.
    Kept for backwards compatibility with existing code.
    """

    pass


# =============================================================================
# Helper Functions
# =============================================================================


def safe_http_error(
    e: Exception,
    message: str = "An error occurred",
    status_code: int = 400,
) -> None:
    """
    Log the real error, raise a sanitized HTTPException to client.
    
    This prevents internal details from leaking in error responses.
    Use this when handling third-party exceptions that may contain
    sensitive information.
    
    Args:
        e: The original exception to log
        message: Sanitized message to send to client
        status_code: HTTP status code
        
    Raises:
        HTTPException: With sanitized message
    """
    logger.error("API error: %s — %s", message, e, exc_info=True)
    raise HTTPException(status_code=status_code, detail=message)


# =============================================================================
# Error Handler Registration
# =============================================================================


def _build_error_body(
    *,
    error: str,
    code: str,
    status: int,
    detail: Any = None,
) -> dict:
    """Build a unified error response dict with the current trace_id.

    Falls back to a freshly-generated UUID4 when the request_id middleware
    isn't installed (e.g. in unit tests using a bare FastAPI() app); this
    guarantees error responses always carry a non-empty ``trace_id`` clients
    can quote in support tickets.
    """
    import uuid

    trace_id = get_request_id() or uuid.uuid4().hex
    return ErrorResponse.build(
        error=error,
        code=code,
        detail=detail,
        trace_id=trace_id,
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""

    @app.exception_handler(GnosisException)
    async def gnosis_exception_handler(request: Request, exc: GnosisException):
        """Handle GnosisException and all subclasses."""
        logger.error(
            "%s %s",
            exc.status_code,
            exc.message,
            extra={
                "extra_data": {
                    "path": str(request.url),
                    "method": request.method,
                    "trace_id": get_request_id(),
                }
            },
        )
        from fastapi.responses import JSONResponse
        
        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_body(
                error=exc.message,
                code=exc.code,
                status=exc.status_code,
                detail=exc.detail,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        """Handle FastAPI HTTPException (including validation errors)."""
        detail_str = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        from fastapi.responses import JSONResponse
        
        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_body(
                error=detail_str,
                code="HTTP_ERROR",
                status=exc.status_code,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        """Catch all unhandled exceptions and return safe 500 response."""
        trace_id = get_request_id()
        
        # Log full traceback for debugging
        logger.error(
            "Unhandled exception: %s",
            exc,
            extra={
                "extra_data": {
                    "traceback": traceback.format_exc(),
                    "path": str(request.url),
                    "method": request.method,
                    "trace_id": trace_id,
                }
            },
        )

        # Send to Sentry if available
        try:
            from app.core.sentry_integration import error_tracker
            error_tracker.capture_exception(
                exc, {"path": str(request.url), "trace_id": trace_id}
            )
        except (ImportError, Exception):
            pass

        from fastapi.responses import JSONResponse
        from app.config import get_settings

        settings = get_settings()
        show_detail = getattr(settings, "DEBUG", False)

        # Never expose internal error details in production
        detail = str(exc) if show_detail else None

        return JSONResponse(
            status_code=500,
            content=_build_error_body(
                error="Internal server error",
                code="INTERNAL_ERROR",
                status=500,
                detail=detail,
            ),
        )
