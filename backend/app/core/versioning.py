from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import re


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Adds API version headers and supports content-negotiation via Accept-Version."""

    CURRENT_VERSION = "1.0.0"
    SUPPORTED_VERSIONS = {"1.0.0", "1.0"}
    # Pattern to extract version from URL like /api/v1/ or /api/v2/
    URL_VERSION_RE = re.compile(r"/api/v(\d+)/")

    async def dispatch(self, request: Request, call_next):
        # Check Accept-Version header for content negotiation
        requested_version = request.headers.get("accept-version", "")
        if requested_version and requested_version not in self.SUPPORTED_VERSIONS:
            from starlette.responses import JSONResponse

            return JSONResponse(
                status_code=406,
                content={
                    "detail": f"Unsupported API version: {requested_version}",
                    "supported_versions": sorted(self.SUPPORTED_VERSIONS),
                    "current_version": self.CURRENT_VERSION,
                },
            )

        response = await call_next(request)
        response.headers["X-API-Version"] = self.CURRENT_VERSION
        response.headers["X-Gnosis-Version"] = self.CURRENT_VERSION

        # Deprecation headers for future use
        url_match = self.URL_VERSION_RE.search(str(request.url))
        if url_match:
            url_version = int(url_match.group(1))
            if url_version < 1:
                response.headers["Deprecation"] = "true"
                response.headers["Link"] = '</api/v1/>; rel="successor-version"'

        return response
