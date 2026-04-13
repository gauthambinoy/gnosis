"""Model Router — routes requests to the right tier/provider based on complexity."""
import time
import hashlib
import json
from typing import AsyncIterator
from app.llm.client import gateway, LLMResponse


class ResponseCache:
    """Simple in-memory cache for LLM responses."""
    
    def __init__(self, max_size: int = 1000):
        self._cache: dict[str, dict] = {}
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def _key(self, messages: list[dict]) -> str:
        content = json.dumps(messages, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(self, messages: list[dict]) -> dict | None:
        key = self._key(messages)
        if key in self._cache:
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def set(self, messages: list[dict], response: dict):
        key = self._key(messages)
        if len(self._cache) >= self._max_size:
            # Evict oldest
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = response

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def stats(self) -> dict:
        return {"hits": self._hits, "misses": self._misses, "hit_rate": self.hit_rate, "size": len(self._cache)}


# L0: Reflex (cache hit) — 0 tokens
# L1: Classify (fast/cheap model) — ~50 tokens
# L2: Standard (mid model) — ~300 tokens
# L3: Deep (premium model) — ~800 tokens

TIER_CONFIG = {
    "L0": {"name": "Reflex", "description": "Cache hit, 0 tokens", "max_tokens": 0},
    "L1": {"name": "Classify", "description": "Fast classification", "max_tokens": 256},
    "L2": {"name": "Standard", "description": "Standard reasoning", "max_tokens": 2048},
    "L3": {"name": "Deep", "description": "Complex analysis", "max_tokens": 4096},
}


class ModelRouter:
    """Routes requests through progressive reasoning tiers."""

    def __init__(self):
        self.cache = ResponseCache()
        self._cost_tracker = {"total_tokens": 0, "total_cost_usd": 0.0, "requests": 0}

    async def classify_complexity(self, messages: list[dict]) -> str:
        """Determine which reasoning tier a request needs."""
        last_msg = messages[-1].get("content", "") if messages else ""
        word_count = len(last_msg.split())

        # Simple heuristics (replaced by L1 model classification later)
        if word_count < 10:
            return "L1"
        elif word_count < 50:
            return "L2"
        else:
            return "L3"

    async def route(self, messages: list[dict], force_tier: str | None = None) -> AsyncIterator[str]:
        """Route a request through the appropriate tier."""
        # L0: Check cache first
        cached = self.cache.get(messages)
        if cached and not force_tier:
            yield cached["content"]
            return

        tier = force_tier or await self.classify_complexity(messages)
        
        start = time.time()
        full_response = ""
        
        try:
            async for token in gateway.think(tier, messages):
                full_response += token
                yield token
        except ValueError:
            # No provider for this tier, fall back
            for fallback_tier in ["L2", "L1", "L3"]:
                if fallback_tier != tier:
                    try:
                        async for token in gateway.think(fallback_tier, messages):
                            full_response += token
                            yield token
                        break
                    except ValueError:
                        continue

        latency_ms = (time.time() - start) * 1000

        # Cache the response
        if full_response:
            self.cache.set(messages, {"content": full_response, "tier": tier, "latency_ms": latency_ms})

        # Track costs
        self._cost_tracker["requests"] += 1
        self._cost_tracker["total_tokens"] += len(full_response) // 4

    @property
    def stats(self) -> dict:
        return {
            "cache": self.cache.stats,
            "cost": self._cost_tracker,
            "tiers": TIER_CONFIG,
        }


# Global singleton
model_router = ModelRouter()
