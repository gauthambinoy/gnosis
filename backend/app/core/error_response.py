"""
DEPRECATED: All functionality has moved to app/core/error_handling.py

This module is kept for backwards compatibility only.
Import from app.core.error_handling instead.
"""

# Re-export everything from the new consolidated module for backwards compat
from app.core.error_handling import (
    ErrorResponse,
    GnosisException,
    NotFoundError,
    ValidationError,
    AuthError,
    ForbiddenError,
    RateLimitError,
    LLMError,
    ExternalServiceError,
)

__all__ = [
    "ErrorResponse",
    "GnosisException",
    "NotFoundError",
    "ValidationError",
    "AuthError",
    "ForbiddenError",
    "RateLimitError",
    "LLMError",
    "ExternalServiceError",
]
