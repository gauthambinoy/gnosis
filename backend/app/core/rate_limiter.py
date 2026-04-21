"""Per-user and per-IP rate limiting with sliding window.

Concurrency model
-----------------
The in-memory sliding-window state is protected by ``asyncio.Lock``s
created lazily per bucket. When Redis is available (see
``app.core.redis_client``) the limiter prefers an atomic
``INCR`` + ``EXPIRE`` strategy which sidesteps the in-process race
entirely.

Public synchronous methods (``check``, ``check_user``, ``check_ip``,
``set_user_limit``, ``get_stats``) are preserved for backwards
compatibility — under a single asyncio event loop they execute
without ``await`` and are therefore atomic.  The async variants
(``acheck``, ``acheck_user``, ``acheck_ip``) provide the
race-free, Redis-aware path used by the FastAPI dependency.
"""

import asyncio
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from app.core.logger import get_logger

logger = get_logger("rate_limiter")


class RateLimiter:
    def __init__(self):
        self.windows: dict[str, list[float]] = defaultdict(list)
        self.user_limits: dict[str, int] = {}  # user_id → custom limit
        self.default_limit = 100  # per minute
        self.premium_limit = 500
        self._bucket_locks: dict[str, asyncio.Lock] = {}
        self._locks_guard: asyncio.Lock | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_locks_guard(self) -> asyncio.Lock:
        if self._locks_guard is None:
            self._locks_guard = asyncio.Lock()
        return self._locks_guard

    async def _get_bucket_lock(self, key: str) -> asyncio.Lock:
        lock = self._bucket_locks.get(key)
        if lock is not None:
            return lock
        async with self._get_locks_guard():
            lock = self._bucket_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._bucket_locks[key] = lock
            return lock

    def _clean_window(self, key: str, window_seconds: int = 60):
        now = time.time()
        self.windows[key] = [t for t in self.windows[key] if now - t < window_seconds]

    def _check_locked(self, key: str, limit: int, window_seconds: int = 60) -> dict:
        """Pure read-modify-write against the in-memory window. Caller must hold the bucket lock."""
        self._clean_window(key, window_seconds)
        bucket = self.windows[key]
        current = len(bucket)
        if current >= limit:
            oldest = min(bucket) if bucket else time.time()
            return {
                "allowed": False,
                "remaining": 0,
                "reset_in": round(window_seconds - (time.time() - oldest), 1),
                "limit": limit,
            }
        bucket.append(time.time())
        return {
            "allowed": True,
            "remaining": limit - current - 1,
            "reset_in": float(window_seconds),
            "limit": limit,
        }

    # ------------------------------------------------------------------
    # Synchronous public API (race-free under single asyncio loop)
    # ------------------------------------------------------------------

    def check(self, key: str, limit: int = None) -> dict:
        """Check rate limit. Returns {allowed: bool, remaining: int, reset_in: float}."""
        limit = limit or self.default_limit
        return self._check_locked(key, limit)

    def check_user(self, user_id: str) -> dict:
        limit = self.user_limits.get(user_id, self.default_limit)
        return self.check(f"user:{user_id}", limit)

    def check_ip(self, ip: str) -> dict:
        return self.check(f"ip:{ip}", self.default_limit)

    def set_user_limit(self, user_id: str, limit: int):
        self.user_limits[user_id] = limit

    def get_stats(self) -> dict:
        return {
            "tracked_keys": len(self.windows),
            "custom_limits": len(self.user_limits),
        }

    # ------------------------------------------------------------------
    # Async public API — uses Redis when available, else per-bucket lock
    # ------------------------------------------------------------------

    async def _acheck_redis(
        self, key: str, limit: int, window_seconds: int = 60
    ) -> dict | None:
        """Try the Redis path. Returns None if Redis is unavailable or errors."""
        try:
            from app.core.redis_client import redis_manager
        except Exception:
            return None
        if not getattr(redis_manager, "available", False):
            return None
        client = redis_manager.client
        if client is None:
            return None
        redis_key = f"ratelimit:{key}"
        try:
            current = await client.incr(redis_key)
            if current == 1:
                await client.expire(redis_key, window_seconds)
                ttl = window_seconds
            else:
                ttl_raw = await client.ttl(redis_key)
                ttl = int(ttl_raw) if ttl_raw and int(ttl_raw) > 0 else window_seconds
            if current > limit:
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_in": float(ttl),
                    "limit": limit,
                }
            return {
                "allowed": True,
                "remaining": max(0, limit - int(current)),
                "reset_in": float(ttl),
                "limit": limit,
            }
        except Exception as exc:
            logger.warning(f"rate_limiter_redis_error: {exc}")
            return None

    async def acheck(self, key: str, limit: int = None) -> dict:
        limit = limit or self.default_limit
        redis_result = await self._acheck_redis(key, limit)
        if redis_result is not None:
            return redis_result
        bucket_lock = await self._get_bucket_lock(key)
        async with bucket_lock:
            return self._check_locked(key, limit)

    async def acheck_user(self, user_id: str) -> dict:
        limit = self.user_limits.get(user_id, self.default_limit)
        return await self.acheck(f"user:{user_id}", limit)

    async def acheck_ip(self, ip: str) -> dict:
        return await self.acheck(f"ip:{ip}", self.default_limit)


rate_limiter = RateLimiter()


async def require_rate_limit(request: Request):
    """FastAPI dependency for rate limiting. Apply to routers via dependencies=[Depends(require_rate_limit)]."""
    user_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from app.core.auth import decode_token

            payload = decode_token(auth_header.split(" ")[1])
            user_id = payload.get("sub")
        except Exception:
            pass

    if user_id:
        result = await rate_limiter.acheck_user(user_id)
    else:
        client_ip = request.client.host if request.client else "unknown"
        result = await rate_limiter.acheck_ip(client_ip)

    if not result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {result['reset_in']}s",
            headers={
                "Retry-After": str(int(result["reset_in"])),
                "X-RateLimit-Remaining": "0",
            },
        )

    request.state.rate_limit_remaining = result["remaining"]
    request.state.rate_limit_limit = result["limit"]
