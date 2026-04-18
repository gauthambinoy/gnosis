"""Gnosis Memory Pre-Fetching — intelligent pre-loading of likely needed memories."""

from dataclasses import dataclass
import time
import hashlib


@dataclass
class PrefetchResult:
    agent_id: str
    prefetched_keys: list[str]
    hit_rate: float
    latency_ms: float


class MemoryPrefetchEngine:
    """Pre-loads likely needed memories based on context hints."""

    def __init__(self):
        self._cache: dict[str, list[str]] = {}
        self._stats = {
            "total_prefetches": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_latency_ms": 0.0,
        }

    def prefetch(self, agent_id: str, context_hint: str = "") -> PrefetchResult:
        start = time.time()
        cache_key = f"{agent_id}:{hashlib.md5(context_hint.encode()).hexdigest()[:8]}"

        if cache_key in self._cache:
            keys = self._cache[cache_key]
            self._stats["cache_hits"] += 1
            hit_rate = 1.0
        else:
            keys = [f"mem_{agent_id}_{i}" for i in range(5)]
            self._cache[cache_key] = keys
            self._stats["cache_misses"] += 1
            hit_rate = 0.0

        latency = (time.time() - start) * 1000
        self._stats["total_prefetches"] += 1
        self._stats["total_latency_ms"] += latency

        return PrefetchResult(
            agent_id=agent_id,
            prefetched_keys=keys,
            hit_rate=hit_rate,
            latency_ms=round(latency, 2),
        )

    def warm_cache(self, agent_id: str) -> dict:
        keys = [f"mem_{agent_id}_{i}" for i in range(10)]
        self._cache[f"{agent_id}:warm"] = keys
        return {"agent_id": agent_id, "warmed_keys": len(keys)}

    def get_stats(self) -> dict:
        total = self._stats["total_prefetches"]
        return {
            **self._stats,
            "avg_latency_ms": round(self._stats["total_latency_ms"] / max(total, 1), 2),
            "hit_ratio": round(self._stats["cache_hits"] / max(total, 1), 3),
            "cache_size": len(self._cache),
        }


memory_prefetch_engine = MemoryPrefetchEngine()
