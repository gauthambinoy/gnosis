from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class APIVersionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-API-Version"] = "1.0.0"
        response.headers["X-Gnosis-Version"] = "1.0.0"
        # Deprecation headers for future use
        if "/api/v1/" in str(request.url):
            response.headers["Sunset"] = ""  # Will be set when v2 launches
        return response
