"""Model Router — routes requests to the right tier/provider based on complexity."""
import time
import hashlib
import json
from collections import OrderedDict
from typing import AsyncIterator
from app.llm.client import gateway, LLMResponse


# ---------------------------------------------------------------------------
# LRU Response Cache (max 1000 entries)
# ---------------------------------------------------------------------------
class ResponseCache:
    """LRU cache for LLM responses."""

    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, dict] = OrderedDict()
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
            self._cache.move_to_end(key)  # mark as recently used
            return self._cache[key]
        self._misses += 1
        return None

    def set(self, messages: list[dict], response: dict):
        key = self._key(messages)
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = response
            return
        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)  # evict least-recently-used
        self._cache[key] = response

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def stats(self) -> dict:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
            "size": len(self._cache),
            "max_size": self._max_size,
        }


# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------
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

# Mapping from classify_complexity labels to tier names
COMPLEXITY_TO_TIER = {
    "reflex": "L0",
    "classify": "L1",
    "standard": "L2",
    "deep": "L3",
}

# ---------------------------------------------------------------------------
# Keyword heuristics for classify_complexity(trigger_data)
# ---------------------------------------------------------------------------
DEEP_KEYWORDS = [
    "analyze", "compare", "strategy", "architecture", "plan", "debug",
    "investigate", "diagnose", "complex", "multi-step",
]
STANDARD_KEYWORDS = [
    "summarize", "draft", "review", "explain", "describe", "generate",
    "write", "update", "create",
]
CLASSIFY_KEYWORDS = [
    "classify", "categorize", "label", "tag", "route", "triage", "sort",
    "yes", "no",
]
REFLEX_KEYWORDS = [
    "ack", "ok", "thanks", "ping", "hello", "hi", "status",
]

# Default fallback chain order per tier
DEFAULT_FALLBACK_ORDER: dict[str, list[str]] = {
    "L3": ["L3", "L2", "L1"],
    "L2": ["L2", "L3", "L1"],
    "L1": ["L1", "L2"],
}


# ---------------------------------------------------------------------------
# Model Router
# ---------------------------------------------------------------------------
class ModelRouter:
    """Routes requests through progressive reasoning tiers with fallback."""

    def __init__(
        self,
        user_model_config: dict[str, dict] | None = None,
        fallback_order: dict[str, list[str]] | None = None,
    ):
        self.cache = ResponseCache()
        self._cost_tracker = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "requests": 0,
        }
        self._user_model_config = user_model_config or {}
        self._fallback_order = fallback_order or DEFAULT_FALLBACK_ORDER

    # ------------------------------------------------------------------
    # Complexity classification (keyword heuristics on trigger_data)
    # ------------------------------------------------------------------
    @staticmethod
    def classify_complexity(trigger_data: dict) -> str:
        """Return 'reflex' / 'classify' / 'standard' / 'deep' based on keywords."""
        text = " ".join(str(v) for v in trigger_data.values()).lower()

        if any(kw in text for kw in DEEP_KEYWORDS):
            return "deep"
        if any(kw in text for kw in STANDARD_KEYWORDS):
            return "standard"
        if any(kw in text for kw in CLASSIFY_KEYWORDS):
            return "classify"
        if any(kw in text for kw in REFLEX_KEYWORDS):
            return "reflex"

        # Fallback: length heuristic
        word_count = len(text.split())
        if word_count < 10:
            return "classify"
        elif word_count < 50:
            return "standard"
        return "deep"

    def _classify_tier_from_messages(self, messages: list[dict]) -> str:
        """Internal: map messages to a tier (used when no force_tier)."""
        last_msg = messages[-1].get("content", "") if messages else ""
        complexity = self.classify_complexity({"content": last_msg})
        return COMPLEXITY_TO_TIER.get(complexity, "L2")

    # ------------------------------------------------------------------
    # User model config helpers
    # ------------------------------------------------------------------
    def set_user_model_config(self, config: dict[str, dict]):
        """Set per-tier provider overrides.

        Format: {"L1": {"provider": "ollama", "model": "llama3.2", "api_key": ""}, ...}
        """
        self._user_model_config = config

    def _apply_user_config(self, tier: str):
        """If a user override exists for a tier, configure the gateway."""
        cfg = self._user_model_config.get(tier)
        if cfg:
            try:
                gateway.configure(
                    tier=tier,
                    provider_name=cfg["provider"],
                    api_key=cfg.get("api_key", ""),
                    model=cfg.get("model", ""),
                )
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Token estimation
    # ------------------------------------------------------------------
    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(len(text) // 4, 1)

    # ------------------------------------------------------------------
    # Route (with auto-fallback & token tracking)
    # ------------------------------------------------------------------
    async def route(
        self,
        messages: list[dict],
        force_tier: str | None = None,
    ) -> AsyncIterator[str]:
        """Route a request through the appropriate tier with fallback."""
        # L0: Check cache first
        cached = self.cache.get(messages)
        if cached and not force_tier:
            yield cached["content"]
            return

        tier = force_tier or self._classify_tier_from_messages(messages)

        # Apply user overrides if present
        self._apply_user_config(tier)

        # Build ordered list of tiers to try
        tiers_to_try = self._fallback_order.get(tier, [tier])
        if tier not in tiers_to_try:
            tiers_to_try = [tier] + tiers_to_try

        input_text = json.dumps(messages)
        input_tokens = self._estimate_tokens(input_text)

        start = time.time()
        full_response = ""

        for attempt_tier in tiers_to_try:
            self._apply_user_config(attempt_tier)
            try:
                async for token in gateway.think(attempt_tier, messages):
                    full_response += token
                    yield token
                break  # success — stop trying
            except (ValueError, Exception):
                full_response = ""
                continue

        latency_ms = (time.time() - start) * 1000
        output_tokens = self._estimate_tokens(full_response)

        # Cache the response
        if full_response:
            self.cache.set(messages, {
                "content": full_response,
                "tier": tier,
                "latency_ms": latency_ms,
            })

        # Track token usage
        self._cost_tracker["requests"] += 1
        self._cost_tracker["total_input_tokens"] += input_tokens
        self._cost_tracker["total_output_tokens"] += output_tokens

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    @property
    def stats(self) -> dict:
        return {
            "cache": self.cache.stats,
            "cost": self._cost_tracker,
            "tiers": TIER_CONFIG,
            "user_overrides": list(self._user_model_config.keys()),
        }


# Global singleton
model_router = ModelRouter()
