"""Per-user and per-IP rate limiting with sliding window."""

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
    
    def _clean_window(self, key: str, window_seconds: int = 60):
        now = time.time()
        self.windows[key] = [t for t in self.windows[key] if now - t < window_seconds]
    
    def check(self, key: str, limit: int = None) -> dict:
        """Check rate limit. Returns {allowed: bool, remaining: int, reset_in: float}."""
        limit = limit or self.default_limit
        self._clean_window(key)
        
        current = len(self.windows[key])
        if current >= limit:
            oldest = min(self.windows[key]) if self.windows[key] else time.time()
            return {
                "allowed": False,
                "remaining": 0,
                "reset_in": round(60 - (time.time() - oldest), 1),
                "limit": limit,
            }
        
        self.windows[key].append(time.time())
        return {
            "allowed": True,
            "remaining": limit - current - 1,
            "reset_in": 60.0,
            "limit": limit,
        }
    
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

rate_limiter = RateLimiter()
