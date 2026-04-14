from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
from app.core.logger import get_logger
from app.core.error_response import (
    ErrorResponse,
    GnosisException,
    NotFoundError as _NewNotFound,
    ValidationError as _NewValidation,
    AuthError as _NewAuth,
    ForbiddenError as _NewForbidden,
    RateLimitError as _NewRateLimit,
)
from app.middleware.request_id import get_request_id

logger = get_logger("errors")

# ---------------------------------------------------------------------------
# Legacy aliases — existing code that imports from here keeps working
# ---------------------------------------------------------------------------

class GnosisError(Exception):
    """Base Gnosis exception (legacy). Prefer GnosisException from error_response."""
    def __init__(self, message: str, status_code: int = 500, detail: dict = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)

class NotFoundError(GnosisError):
    def __init__(self, resource: str, id: str):
        super().__init__(f"{resource} '{id}' not found", 404)

class AuthenticationError(GnosisError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, 401)

class ForbiddenError(GnosisError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, 403)

class ValidationError(GnosisError):
    def __init__(self, message: str):
        super().__init__(message, 422)

class RateLimitError(GnosisError):
    def __init__(self):
        super().__init__("Rate limit exceeded", 429)


# ---------------------------------------------------------------------------
# Unified error handler registration
# ---------------------------------------------------------------------------

def _error_body(*, error: str, code: str, status: int, detail=None) -> dict:
    """Build a unified error response dict with the current trace_id."""
    return ErrorResponse.build(
        error=error,
        code=code,
        detail=detail,
        trace_id=get_request_id(),
    )


def register_error_handlers(app: FastAPI):
    # --- New GnosisException hierarchy (error_response.py) -----------------
    @app.exception_handler(GnosisException)
    async def gnosis_exception_handler(request: Request, exc: GnosisException):
        logger.error(
            "%s %s",
            exc.status_code,
            exc.message,
            extra={"extra_data": {"path": str(request.url), "method": request.method, "trace_id": get_request_id()}},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(error=exc.message, code=exc.code, status=exc.status_code, detail=exc.detail),
        )

    # --- Legacy GnosisError (kept for backwards compat) --------------------
    @app.exception_handler(GnosisError)
    async def gnosis_error_handler(request: Request, exc: GnosisError):
        logger.error(
            "%s %s",
            exc.status_code,
            exc.message,
            extra={"extra_data": {"path": str(request.url), "method": request.method, "trace_id": get_request_id()}},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(error=exc.message, code="LEGACY_ERROR", status=exc.status_code, detail=exc.detail),
        )

    # --- Starlette / FastAPI HTTPException ---------------------------------
    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        detail_str = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(error=detail_str, code="HTTP_ERROR", status=exc.status_code),
        )

    # --- Catch-all for unhandled exceptions --------------------------------
    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        trace_id = get_request_id()
        logger.error(
            "Unhandled: %s",
            exc,
            extra={"extra_data": {"traceback": traceback.format_exc(), "path": str(request.url), "trace_id": trace_id}},
        )
        from app.core.sentry_integration import error_tracker
        error_tracker.capture_exception(exc, {"path": str(request.url), "trace_id": trace_id})

        from app.config import get_settings
        settings = get_settings()
        show_detail = getattr(settings, "debug", False)

        return JSONResponse(
            status_code=500,
            content=_error_body(
                error="Internal server error",
                code="INTERNAL_ERROR",
                status=500,
                detail=str(exc) if show_detail else None,
            ),
        )
