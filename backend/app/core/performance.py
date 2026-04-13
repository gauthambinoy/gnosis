"""Performance utilities for the Gnosis platform.

Provides caching, connection pooling, timing decorators,
and metrics collection.
"""

import time
import asyncio
import logging
import threading
from functools import wraps
from collections import OrderedDict
from typing import Any

import aiohttp

logger = logging.getLogger("gnosis.performance")


class LRUCache:
    """Thread-safe LRU cache with TTL support."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any:
        """Retrieve a value by key. Returns None if missing or expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            if time.time() - entry["created_at"] > self.ttl_seconds:
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return entry["value"]

    def set(self, key: str, value: Any) -> None:
        """Store a value, evicting the oldest entry if at capacity."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = {"value": value, "created_at": time.time()}
            else:
                if len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)
                self._cache[key] = {"value": value, "created_at": time.time()}

    def invalidate(self, key: str) -> None:
        """Remove a specific key from the cache."""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
            }


class ConnectionPool:
    """Manages reusable HTTP connections for external integrations."""

    def __init__(self, max_connections: int = 50):
        self.max_connections = max_connections
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()

    async def get_session(self) -> aiohttp.ClientSession:
        """Return a shared aiohttp session, creating one if needed."""
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    connector = aiohttp.TCPConnector(
                        limit=self.max_connections,
                        ttl_dns_cache=300,
                        enable_cleanup_closed=True,
                    )
                    self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def close_all(self) -> None:
        """Close the shared session and release all connections."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None


def timed(func):
    """Decorator that logs execution time for sync and async functions."""
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = (time.perf_counter() - start) * 1000
                logger.info("%s completed in %.1fms", func.__qualname__, elapsed)
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = (time.perf_counter() - start) * 1000
                logger.info("%s completed in %.1fms", func.__qualname__, elapsed)
        return sync_wrapper


def cached(ttl: int = 300, max_size: int = 100):
    """Decorator for caching async function results with TTL.

    Args:
        ttl: Time-to-live in seconds for cached entries.
        max_size: Maximum number of cached results.
    """
    _cache = LRUCache(max_size=max_size, ttl_seconds=ttl)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build a cache key from function name + arguments
            key_parts = [func.__qualname__] + [repr(a) for a in args] + [f"{k}={v!r}" for k, v in sorted(kwargs.items())]
            key = ":".join(key_parts)

            result = _cache.get(key)
            if result is not None:
                return result

            result = await func(*args, **kwargs)
            _cache.set(key, result)
            return result

        wrapper.cache = _cache
        return wrapper
    return decorator


class PerformanceMonitor:
    """Collects and reports performance metrics."""

    def __init__(self):
        self._metrics: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def record(self, metric: str, value: float) -> None:
        """Record a metric value."""
        with self._lock:
            if metric not in self._metrics:
                self._metrics[metric] = []
            self._metrics[metric].append(value)

    def get_stats(self) -> dict:
        """Return summary statistics for all metrics."""
        with self._lock:
            result = {}
            for metric, values in self._metrics.items():
                if not values:
                    continue
                sorted_vals = sorted(values)
                result[metric] = {
                    "count": len(values),
                    "avg": round(sum(values) / len(values), 4),
                    "min": round(sorted_vals[0], 4),
                    "max": round(sorted_vals[-1], 4),
                    "p95": round(self._percentile(sorted_vals, 95), 4),
                }
            return result

    def get_p95(self, metric: str) -> float:
        """Return the 95th percentile for a specific metric."""
        with self._lock:
            values = self._metrics.get(metric, [])
            if not values:
                return 0.0
            return round(self._percentile(sorted(values), 95), 4)

    def get_avg(self, metric: str) -> float:
        """Return the average for a specific metric."""
        with self._lock:
            values = self._metrics.get(metric, [])
            if not values:
                return 0.0
            return round(sum(values) / len(values), 4)

    @staticmethod
    def _percentile(sorted_values: list[float], pct: float) -> float:
        """Compute the given percentile from a sorted list."""
        if not sorted_values:
            return 0.0
        k = (len(sorted_values) - 1) * (pct / 100.0)
        f = int(k)
        c = f + 1
        if c >= len(sorted_values):
            return sorted_values[-1]
        d = k - f
        return sorted_values[f] + d * (sorted_values[c] - sorted_values[f])
