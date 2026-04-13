"""Gnosis Progressive Reasoning — escalates through complexity levels on demand."""
import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from app.core.memory_engine import memory_engine
from app.core.embeddings import embedding_service


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass
class ReasoningResult:
    level: int
    level_name: str
    content: Any
    confidence: float
    tokens_used: int
    latency_ms: float
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# LRU cache for reasoning results
# ---------------------------------------------------------------------------
class _ReasoningCache:
    def __init__(self, max_size: int = 2000):
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._max_size = max_size

    def _key(self, context: dict) -> str:
        raw = json.dumps(context, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:20]

    def get(self, context: dict) -> dict | None:
        key = self._key(context)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, context: dict, result: dict):
        key = self._key(context)
        if key in self._cache:
            self._cache.move_to_end(key)
        elif len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        self._cache[key] = result

    @property
    def size(self) -> int:
        return len(self._cache)


# ---------------------------------------------------------------------------
# Pattern library
# ---------------------------------------------------------------------------
@dataclass
class PatternRule:
    pattern: str  # human-readable description
    action: str  # what to do
    confidence: float = 0.9
    match_keywords: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Progressive Reasoner
# ---------------------------------------------------------------------------
LEVEL_NAMES = {
    0: "cache",
    1: "pattern_match",
    2: "classify",
    3: "standard",
    4: "deep",
}

CONFIDENCE_THRESHOLD = 0.7


class ProgressiveReasoner:
    """Starts with cheapest reasoning and escalates only if needed.

    Level 0 — Cache check (0 tokens)
    Level 1 — Pattern match against procedural memory (0 tokens)
    Level 2 — Classify intent with cheap heuristics (≈50 tokens equiv)
    Level 3 — Standard reasoning (≈300 tokens)
    Level 4 — Deep analysis with chain-of-thought (≈800 tokens)

    Returns as soon as confidence ≥ threshold at any level.
    """

    def __init__(self, confidence_threshold: float = CONFIDENCE_THRESHOLD):
        self._cache = _ReasoningCache()
        self._pattern_rules: list[PatternRule] = []
        self.confidence_threshold = confidence_threshold
        self._stats = {
            "level_hits": {i: 0 for i in range(5)},
            "total_requests": 0,
            "total_tokens_saved": 0,
        }

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    async def reason(self, context: dict, budget_tokens: int = 800) -> ReasoningResult:
        """Progressive reasoning — returns as soon as confidence is high enough."""
        self._stats["total_requests"] += 1
        start = time.time()

        # Level 0 — Cache check (0 tokens)
        cached = self._check_cache(context)
        if cached is not None:
            self._stats["level_hits"][0] += 1
            self._stats["total_tokens_saved"] += budget_tokens
            return ReasoningResult(
                level=0, level_name="cache", content=cached["content"],
                confidence=cached.get("confidence", 1.0),
                tokens_used=0,
                latency_ms=(time.time() - start) * 1000,
                metadata={"source": "cache"},
            )

        # Level 1 — Pattern match (0 tokens)
        agent_id = context.get("agent_id", "default")
        procedures = await self._load_procedures(agent_id)
        pattern_result = self._pattern_match(context, procedures)
        if pattern_result is not None and pattern_result.get("confidence", 0) >= self.confidence_threshold:
            self._stats["level_hits"][1] += 1
            self._stats["total_tokens_saved"] += budget_tokens
            self._cache.set(context, pattern_result)
            return ReasoningResult(
                level=1, level_name="pattern_match",
                content=pattern_result["content"],
                confidence=pattern_result["confidence"],
                tokens_used=0,
                latency_ms=(time.time() - start) * 1000,
                metadata={"matched_pattern": pattern_result.get("pattern")},
            )

        # Level 2 — Classify intent (cheap, ~50 token equivalent)
        if budget_tokens >= 50:
            classify_result = await self._classify(context)
            if classify_result["confidence"] >= self.confidence_threshold:
                self._stats["level_hits"][2] += 1
                self._stats["total_tokens_saved"] += (budget_tokens - 50)
                self._cache.set(context, classify_result)
                return ReasoningResult(
                    level=2, level_name="classify",
                    content=classify_result["content"],
                    confidence=classify_result["confidence"],
                    tokens_used=classify_result.get("tokens", 50),
                    latency_ms=(time.time() - start) * 1000,
                    metadata={"intent": classify_result.get("intent")},
                )

        # Level 3 — Standard reasoning (~300 tokens)
        if budget_tokens >= 300:
            standard_result = await self._standard_reason(context)
            if standard_result["confidence"] >= self.confidence_threshold:
                self._stats["level_hits"][3] += 1
                self._stats["total_tokens_saved"] += (budget_tokens - 300)
                self._cache.set(context, standard_result)
                return ReasoningResult(
                    level=3, level_name="standard",
                    content=standard_result["content"],
                    confidence=standard_result["confidence"],
                    tokens_used=standard_result.get("tokens", 300),
                    latency_ms=(time.time() - start) * 1000,
                )

        # Level 4 — Deep analysis (~800 tokens)
        if budget_tokens >= 800:
            deep_result = await self._deep_reason(context)
            self._stats["level_hits"][4] += 1
            self._cache.set(context, deep_result)
            return ReasoningResult(
                level=4, level_name="deep",
                content=deep_result["content"],
                confidence=deep_result["confidence"],
                tokens_used=deep_result.get("tokens", 800),
                latency_ms=(time.time() - start) * 1000,
                metadata={"chain_of_thought": deep_result.get("reasoning")},
            )

        # Budget exhausted — return best effort from classify
        fallback = await self._classify(context)
        self._stats["level_hits"][2] += 1
        return ReasoningResult(
            level=2, level_name="classify_fallback",
            content=fallback["content"],
            confidence=fallback["confidence"],
            tokens_used=fallback.get("tokens", 50),
            latency_ms=(time.time() - start) * 1000,
            metadata={"budget_exhausted": True},
        )

    # ------------------------------------------------------------------
    # Level 0 — Cache
    # ------------------------------------------------------------------
    def _check_cache(self, context: dict) -> dict | None:
        return self._cache.get(context)

    # ------------------------------------------------------------------
    # Level 1 — Pattern match
    # ------------------------------------------------------------------
    def _pattern_match(self, context: dict, procedures: list[dict]) -> dict | None:
        """Match context against procedural memories and registered patterns."""
        query_text = _extract_text(context).lower()

        if not query_text:
            return None

        # Check registered pattern rules first
        for rule in self._pattern_rules:
            if rule.match_keywords and all(kw in query_text for kw in rule.match_keywords):
                return {
                    "content": rule.action,
                    "confidence": rule.confidence,
                    "pattern": rule.pattern,
                }

        # Check procedural memories
        if not procedures:
            return None

        best_match = None
        best_score = 0.0

        query_words = set(query_text.split())
        for proc in procedures:
            proc_text = proc.get("content", "").lower()
            proc_words = set(proc_text.split())
            if not proc_words:
                continue
            # Jaccard-ish overlap
            overlap = len(query_words & proc_words)
            score = overlap / max(len(query_words | proc_words), 1)
            if score > best_score:
                best_score = score
                best_match = proc

        if best_match and best_score >= 0.3:
            return {
                "content": best_match.get("content", ""),
                "confidence": min(best_score * 1.5, 0.95),
                "pattern": "procedural_memory",
            }

        return None

    async def _load_procedures(self, agent_id: str) -> list[dict]:
        """Load procedural memories for pattern matching."""
        try:
            memories = await memory_engine.get_agent_memories(agent_id, tier="procedural", limit=50)
            return [{"content": m.content, "metadata": m.metadata} for m in memories]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Level 2 — Classify
    # ------------------------------------------------------------------
    async def _classify(self, context: dict) -> dict:
        """Cheap intent classification using keyword heuristics."""
        text = _extract_text(context)
        text_lower = text.lower()

        # Intent classification via keyword matching
        intent_map = {
            "send": (["send", "email", "message", "notify", "post"], "action_send"),
            "query": (["find", "search", "look", "get", "fetch", "list", "show"], "action_query"),
            "create": (["create", "new", "add", "make", "generate", "build"], "action_create"),
            "update": (["update", "edit", "change", "modify", "fix"], "action_update"),
            "delete": (["delete", "remove", "cancel", "revoke"], "action_delete"),
            "analyze": (["analyze", "compare", "review", "evaluate", "assess"], "action_analyze"),
            "greet": (["hello", "hi", "hey", "thanks", "ok", "ack"], "greeting"),
        }

        best_intent = "unknown"
        best_score = 0
        for intent, (keywords, label) in intent_map.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_intent = label

        confidence = min(0.5 + best_score * 0.15, 0.95)

        return {
            "content": f"Intent: {best_intent}",
            "confidence": confidence,
            "intent": best_intent,
            "tokens": 50,
        }

    # ------------------------------------------------------------------
    # Level 3 — Standard reasoning
    # ------------------------------------------------------------------
    async def _standard_reason(self, context: dict) -> dict:
        """Standard reasoning — uses memory context to build a response."""
        text = _extract_text(context)
        agent_id = context.get("agent_id", "default")

        # Retrieve relevant memories
        try:
            memories = await memory_engine.search_memories(agent_id, text, limit=5)
            memory_context = "\n".join(
                f"- {m.content}" for m in memories
            ) if memories else "No relevant memories found."
        except Exception:
            memory_context = "Memory unavailable."

        # Build reasoning
        reasoning = {
            "trigger": text[:200],
            "relevant_memories": memory_context,
            "suggested_action": "process_request",
        }

        # Confidence based on memory relevance
        if memories:
            avg_relevance = sum(m.relevance_score for m in memories) / len(memories)
            confidence = min(0.6 + avg_relevance * 0.3, 0.95)
        else:
            confidence = 0.5

        return {
            "content": reasoning,
            "confidence": confidence,
            "tokens": 300,
            "memory_count": len(memories) if memories else 0,
        }

    # ------------------------------------------------------------------
    # Level 4 — Deep reasoning (chain-of-thought)
    # ------------------------------------------------------------------
    async def _deep_reason(self, context: dict) -> dict:
        """Deep analysis with chain-of-thought reasoning."""
        text = _extract_text(context)
        agent_id = context.get("agent_id", "default")

        # Get broader memory context
        try:
            memories = await memory_engine.search_memories(agent_id, text, limit=10)
            corrections = await memory_engine.get_agent_memories(agent_id, tier="correction", limit=5)
        except Exception:
            memories = []
            corrections = []

        # Chain-of-thought steps
        steps = []

        # Step 1: Understand the request
        steps.append(f"Understanding: {text[:300]}")

        # Step 2: Check corrections
        if corrections:
            steps.append(f"Corrections to respect: {len(corrections)} active corrections")
            for c in corrections[:3]:
                steps.append(f"  ⚠ {c.content[:100]}")

        # Step 3: Relevant experience
        if memories:
            steps.append(f"Relevant experience: {len(memories)} similar situations found")
            avg_score = sum(m.relevance_score for m in memories) / len(memories)
            steps.append(f"  Average relevance: {avg_score:.2f}")

        # Step 4: Synthesize
        steps.append("Synthesis: combining corrections, experience, and request to form response")

        # Step 5: Confidence assessment
        correction_boost = 0.1 if corrections else 0.0
        memory_boost = min(len(memories) * 0.05, 0.2) if memories else 0.0
        confidence = min(0.6 + correction_boost + memory_boost, 0.95)

        steps.append(f"Confidence: {confidence:.2f}")

        return {
            "content": {
                "reasoning_chain": steps,
                "suggested_action": "execute_with_context",
                "corrections_applied": len(corrections),
                "memories_used": len(memories),
            },
            "confidence": confidence,
            "reasoning": steps,
            "tokens": 800,
        }

    # ------------------------------------------------------------------
    # Pattern management
    # ------------------------------------------------------------------
    def add_pattern(self, pattern: str, action: str, keywords: list[str], confidence: float = 0.9):
        """Register a pattern rule for Level 1 matching."""
        self._pattern_rules.append(PatternRule(
            pattern=pattern, action=action,
            confidence=confidence, match_keywords=keywords,
        ))

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    @property
    def stats(self) -> dict:
        return {
            **self._stats,
            "cache_size": self._cache.size,
            "pattern_rules": len(self._pattern_rules),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _extract_text(context: dict) -> str:
    """Pull human-readable text from a context dict."""
    parts = []
    for key in ("query", "content", "body", "subject", "text", "trigger", "message"):
        if val := context.get(key):
            parts.append(str(val))
    if not parts:
        parts.append(" ".join(str(v) for v in context.values()))
    return " ".join(parts)[:1000]


# Global singleton
progressive_reasoner = ProgressiveReasoner()
