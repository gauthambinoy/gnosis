"""Redis-backed sliding window rate limiter."""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.config import get_settings

logger = logging.getLogger("gnosis.rate_limiter")
settings = get_settings()

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-user sliding window rate limiter. Uses in-memory fallback if Redis unavailable."""

    def __init__(self, app, requests_per_minute: int = 60, burst: int = 10):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.burst = burst
        self._windows: dict = {}  # Fallback in-memory store

    def _get_key(self, request: Request) -> str:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            return f"rl:{auth[7:20]}"  # Use token prefix as key
        forwarded = request.headers.get("x-forwarded-for", "")
        ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        return f"rl:{ip}"

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in (
            "/health",
            "/health/ready",
            "/health/live",
            "/health/detailed",
            f"{settings.api_prefix}/health",
            f"{settings.api_prefix}/health/ready",
            f"{settings.api_prefix}/health/live",
            f"{settings.api_prefix}/health/detailed",
            "/docs",
            "/openapi.json",
        ):
            return await call_next(request)

        key = self._get_key(request)
        now = time.time()
        window_start = now - 60

        # Try Redis first
        try:
            from app.core.redis_client import redis_manager
            if redis_manager._client:
                pipe = redis_manager._client.pipeline()
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, 120)
                results = await pipe.execute()
                count = results[2]

                if count > self.rpm + self.burst:
                    logger.warning(f"Rate limit exceeded: {key}, count={count}")
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded", "retry_after": 60},
                        headers={"Retry-After": "60", "X-RateLimit-Limit": str(self.rpm), "X-RateLimit-Remaining": "0"},
                    )

                response = await call_next(request)
                response.headers["X-RateLimit-Limit"] = str(self.rpm)
                response.headers["X-RateLimit-Remaining"] = str(max(0, self.rpm - count))
                return response
        except Exception:
            pass

        # Fallback: in-memory sliding window
        if key not in self._windows:
            self._windows[key] = []
        self._windows[key] = [t for t in self._windows[key] if t > window_start]
        self._windows[key].append(now)

        if len(self._windows[key]) > self.rpm + self.burst:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"}, headers={"Retry-After": "60"})

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.rpm - len(self._windows[key])))
        return response
