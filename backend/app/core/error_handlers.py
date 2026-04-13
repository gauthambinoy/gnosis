from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
from app.core.logger import get_logger

logger = get_logger("errors")

class GnosisError(Exception):
    """Base Gnosis exception."""
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

def register_error_handlers(app: FastAPI):
    @app.exception_handler(GnosisError)
    async def gnosis_error_handler(request: Request, exc: GnosisError):
        logger.error(f"{exc.status_code} {exc.message}", extra={"extra_data": {"path": str(request.url), "method": request.method}})
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "detail": exc.detail}
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail}
        )
    
    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled: {exc}", extra={"extra_data": {"traceback": traceback.format_exc(), "path": str(request.url)}})
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )
