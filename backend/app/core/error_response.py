"""Unified error response model and exception hierarchy for Gnosis."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error envelope returned by every error handler."""

    error: str
    code: str
    detail: Any = None
    trace_id: str = ""
    timestamp: str = ""

    @classmethod
    def build(
        cls,
        *,
        error: str,
        code: str,
        detail: Any = None,
        trace_id: str = "",
    ) -> dict:
        return cls(
            error=error,
            code=code,
            detail=detail,
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ).model_dump()


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


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
    status_code = 404
    code = "NOT_FOUND"

    def __init__(self, message: str = "Resource not found", **kwargs):
        super().__init__(message, **kwargs)


class ValidationError(GnosisException):
    status_code = 422
    code = "VALIDATION_ERROR"

    def __init__(self, message: str = "Validation failed", **kwargs):
        super().__init__(message, **kwargs)


class AuthError(GnosisException):
    status_code = 401
    code = "AUTH_ERROR"

    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(message, **kwargs)


class ForbiddenError(GnosisException):
    status_code = 403
    code = "FORBIDDEN"

    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(message, **kwargs)


class RateLimitError(GnosisException):
    status_code = 429
    code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        super().__init__(message, **kwargs)


class LLMError(GnosisException):
    status_code = 502
    code = "LLM_ERROR"

    def __init__(self, message: str = "LLM service error", **kwargs):
        super().__init__(message, **kwargs)


class ExternalServiceError(GnosisException):
    status_code = 502
    code = "EXTERNAL_SERVICE_ERROR"

    def __init__(self, message: str = "External service error", **kwargs):
        super().__init__(message, **kwargs)
