"""Gnosis Orchestrator — Perceive → Reason → Decide → Act execution engine."""
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import re
import time
import uuid

from app.core.memory_engine import MemoryEngine, memory_engine
from app.core.context_assembler import ContextAssembler, context_assembler
from app.core.event_bus import event_bus, Events
from app.core.embeddings import embedding_service
from app.llm.router import ModelRouter, model_router


# ---------------------------------------------------------------------------
# Keyword-based urgency classification (no LLM)
# ---------------------------------------------------------------------------
URGENCY_KEYWORDS: dict[str, list[str]] = {
    "critical": [
        "urgent", "emergency", "critical", "outage", "down", "breach",
        "security", "attack", "p0", "sev0", "incident",
    ],
    "high": [
        "important", "asap", "deadline", "blocker", "escalate", "p1",
        "sev1", "broken", "failure", "crash",
    ],
    "medium": [
        "request", "review", "update", "check", "follow-up", "task",
        "question", "p2",
    ],
}

URGENCY_TIER_MAP: dict[str, str] = {
    "critical": "L3",
    "high": "L2",
    "medium": "L2",
    "low": "L1",
}

TRUST_CONFIDENCE_THRESHOLD = 0.6


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class ExecutionStep:
    phase: str
    content: str
    confidence: float = 0.0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionResult:
    execution_id: str
    agent_id: str
    steps: list[ExecutionStep]
    status: str = "completed"
    total_latency_ms: float = 0.0
    total_cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
class Orchestrator:
    """Production-ready orchestrator with the full 7-phase loop."""

    def __init__(
        self,
        memory: MemoryEngine | None = None,
        assembler: ContextAssembler | None = None,
        router: ModelRouter | None = None,
    ):
        self.memory = memory or memory_engine
        self.assembler = assembler or context_assembler
        self.router = router or model_router
        self._metrics: dict[str, dict] = {}  # agent_id -> counters

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    async def execute(
        self, agent_id: str, trigger_type: str, trigger_data: dict
    ) -> ExecutionResult:
        execution_id = str(uuid.uuid4())
        steps: list[ExecutionStep] = []
        total_start = time.time()

        await event_bus.emit(Events.EXECUTION_STARTED, {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "trigger_type": trigger_type,
        })

        try:
            # Phase 1 — Perceive
            perception = await self._perceive(trigger_type, trigger_data)
            steps.append(perception)

            # Phase 2 — Memory Retrieval (parallel across tiers)
            memory_step = await self._retrieve_memory(agent_id, trigger_data)
            steps.append(memory_step)

            # Phase 3 — Context Assembly
            context_step = await self._assemble_context(
                memory_step.metadata.get("memory_context"),
                perception.metadata.get("summary", ""),
            )
            steps.append(context_step)

            # Phase 4 — Reasoning via LLM
            urgency = perception.metadata.get("urgency", "low")
            reasoning = await self._reason(agent_id, context_step, urgency)
            steps.append(reasoning)

            # Phase 5 — Meta-cognition (confidence check)
            meta_step = self._meta_cognition(reasoning)
            steps.append(meta_step)

            # Phase 6 — Action execution
            actions = await self._act(agent_id, meta_step)
            steps.extend(actions)

            status = "completed"
        except Exception as exc:
            steps.append(ExecutionStep(
                phase="error", content=str(exc), confidence=0.0,
                latency_ms=0.0,
            ))
            status = "failed"

        total_ms = (time.time() - total_start) * 1000
        total_cost = sum(s.cost_usd for s in steps)

        result = ExecutionResult(
            execution_id=execution_id,
            agent_id=agent_id,
            steps=steps,
            status=status,
            total_latency_ms=total_ms,
            total_cost_usd=total_cost,
        )

        # Phase 7 — Post-execution
        await self._post_execution(agent_id, result)
        return result

    # ------------------------------------------------------------------
    # Phase 1 — Perceive
    # ------------------------------------------------------------------
    async def _perceive(
        self, trigger_type: str, trigger_data: dict
    ) -> ExecutionStep:
        start = time.time()

        sender = trigger_data.get("sender", trigger_data.get("from", "unknown"))
        subject = trigger_data.get("subject", trigger_data.get("title", ""))
        body = trigger_data.get("body", trigger_data.get("content", ""))

        # Extract simple intent keywords from text
        text_blob = f"{subject} {body}".lower()
        intent_keywords = [
            w for w in re.findall(r"[a-z]+", text_blob)
            if len(w) > 3
        ][:10]

        urgency = self._classify_urgency(text_blob)

        summary = (
            f"[{trigger_type}] from={sender} subject={subject!r} "
            f"urgency={urgency} intents={intent_keywords[:5]}"
        )

        latency = (time.time() - start) * 1000
        step = ExecutionStep(
            phase="perceive",
            content=summary,
            confidence=1.0,
            latency_ms=latency,
            metadata={
                "sender": sender,
                "subject": subject,
                "intent_keywords": intent_keywords,
                "urgency": urgency,
                "summary": summary,
                "trigger_type": trigger_type,
                "trigger_data": trigger_data,
            },
        )
        await event_bus.emit("orchestrator.phase", {
            "phase": "perceive", "latency_ms": latency, "urgency": urgency,
        })
        return step

    @staticmethod
    def _classify_urgency(text: str) -> str:
        text_lower = text.lower()
        for level in ("critical", "high", "medium"):
            if any(kw in text_lower for kw in URGENCY_KEYWORDS[level]):
                return level
        return "low"

    # ------------------------------------------------------------------
    # Phase 2 — Memory Retrieval (parallel)
    # ------------------------------------------------------------------
    async def _retrieve_memory(
        self, agent_id: str, trigger_data: dict
    ) -> ExecutionStep:
        start = time.time()

        query = " ".join(str(v) for v in trigger_data.values())[:500] or "general"

        async def _search(tier: str):
            try:
                return await self.memory.search_memories(agent_id, f"{tier}: {query}", limit=5)
            except Exception:
                return []

        correction_hits, episodic_hits, semantic_hits, procedural_hits = (
            await asyncio.gather(
                _search("correction"),
                _search("episodic"),
                _search("semantic"),
                _search("procedural"),
            )
        )

        # Also fetch full context (vector search across all tiers)
        mem_ctx = await self.memory.retrieve_context(agent_id, trigger_data)

        latency = (time.time() - start) * 1000
        total_hits = (
            len(correction_hits) + len(episodic_hits)
            + len(semantic_hits) + len(procedural_hits)
        )

        step = ExecutionStep(
            phase="memory",
            content=f"Retrieved {total_hits} memories in {latency:.0f}ms",
            confidence=1.0,
            latency_ms=latency,
            metadata={
                "memory_context": mem_ctx,
                "correction_count": len(correction_hits),
                "episodic_count": len(episodic_hits),
                "semantic_count": len(semantic_hits),
                "procedural_count": len(procedural_hits),
            },
        )
        await event_bus.emit("orchestrator.phase", {
            "phase": "memory", "latency_ms": latency, "total_hits": total_hits,
        })
        return step

    # ------------------------------------------------------------------
    # Phase 3 — Context Assembly
    # ------------------------------------------------------------------
    async def _assemble_context(
        self, mem_ctx, trigger_summary: str
    ) -> ExecutionStep:
        start = time.time()

        if mem_ctx is None:
            prompt = trigger_summary or "No context available."
        else:
            prompt = self.assembler.assemble(mem_ctx, trigger_summary)

        token_est = len(prompt) // 4
        latency = (time.time() - start) * 1000

        step = ExecutionStep(
            phase="context",
            content=prompt,
            confidence=1.0,
            latency_ms=latency,
            metadata={"estimated_tokens": token_est},
        )
        await event_bus.emit("orchestrator.phase", {
            "phase": "context", "latency_ms": latency, "tokens": token_est,
        })
        return step

    # ------------------------------------------------------------------
    # Phase 4 — Reasoning (LLM call via model router)
    # ------------------------------------------------------------------
    async def _reason(
        self, agent_id: str, context_step: ExecutionStep, urgency: str
    ) -> ExecutionStep:
        start = time.time()

        tier = URGENCY_TIER_MAP.get(urgency, "L1")
        messages = [
            {"role": "system", "content": (
                "You are a Gnosis AI agent. Analyze the context and decide "
                "what actions to take. Respond with JSON: "
                '{"reasoning": "...", "confidence": 0.0-1.0, '
                '"actions": [{"type": "...", "params": {...}}]}'
            )},
            {"role": "user", "content": context_step.content},
        ]

        full_response = ""
        try:
            async for token in self.router.route(messages, force_tier=tier):
                full_response += token
        except Exception as exc:
            full_response = (
                f'{{"reasoning": "LLM unavailable: {exc}", '
                f'"confidence": 0.0, "actions": []}}'
            )

        latency = (time.time() - start) * 1000
        step = ExecutionStep(
            phase="reason",
            content=full_response,
            confidence=0.8,
            latency_ms=latency,
            metadata={"tier": tier, "urgency": urgency},
        )
        await event_bus.emit("orchestrator.phase", {
            "phase": "reason", "latency_ms": latency, "tier": tier,
        })
        return step

    # ------------------------------------------------------------------
    # Phase 5 — Meta-cognition
    # ------------------------------------------------------------------
    @staticmethod
    def _meta_cognition(reasoning: ExecutionStep) -> ExecutionStep:
        content = reasoning.content
        confidence = 0.0

        # Try to extract confidence from LLM JSON response
        match = re.search(r'"confidence"\s*:\s*([0-9.]+)', content)
        if match:
            try:
                confidence = float(match.group(1))
            except ValueError:
                confidence = 0.0

        exceeds_threshold = confidence >= TRUST_CONFIDENCE_THRESHOLD

        return ExecutionStep(
            phase="meta_cognition",
            content=(
                f"Confidence={confidence:.2f}, "
                f"threshold={TRUST_CONFIDENCE_THRESHOLD}, "
                f"approved={'yes' if exceeds_threshold else 'no'}"
            ),
            confidence=confidence,
            metadata={
                "trust_approved": exceeds_threshold,
                "raw_confidence": confidence,
                "threshold": TRUST_CONFIDENCE_THRESHOLD,
            },
        )

    # ------------------------------------------------------------------
    # Phase 6 — Action execution
    # ------------------------------------------------------------------
    async def _act(
        self, agent_id: str, meta_step: ExecutionStep
    ) -> list[ExecutionStep]:
        start = time.time()

        if not meta_step.metadata.get("trust_approved", False):
            return [ExecutionStep(
                phase="act",
                content="Action blocked — confidence below trust threshold",
                confidence=meta_step.confidence,
                latency_ms=(time.time() - start) * 1000,
                metadata={"blocked": True},
            )]

        # In production this would dispatch to real integrations.
        # For now, return a placeholder action list.
        latency = (time.time() - start) * 1000
        action_step = ExecutionStep(
            phase="act",
            content="Actions queued for execution (integration placeholder)",
            confidence=meta_step.confidence,
            latency_ms=latency,
            metadata={"actions": [], "blocked": False},
        )
        await event_bus.emit("orchestrator.phase", {
            "phase": "act", "latency_ms": latency,
        })
        return [action_step]

    # ------------------------------------------------------------------
    # Phase 7 — Post-execution
    # ------------------------------------------------------------------
    async def _post_execution(
        self, agent_id: str, result: ExecutionResult
    ) -> None:
        # Store as episodic memory
        try:
            summary = (
                f"Execution {result.execution_id}: status={result.status} "
                f"steps={len(result.steps)} latency={result.total_latency_ms:.0f}ms"
            )
            await self.memory.store(
                agent_id=agent_id,
                tier="episodic",
                content=summary,
                metadata={
                    "execution_id": result.execution_id,
                    "status": result.status,
                    "total_latency_ms": result.total_latency_ms,
                    "total_cost_usd": result.total_cost_usd,
                },
            )
        except Exception:
            pass

        # Update agent metrics
        metrics = self._metrics.setdefault(agent_id, {
            "executions": 0, "total_latency_ms": 0.0, "failures": 0,
        })
        metrics["executions"] += 1
        metrics["total_latency_ms"] += result.total_latency_ms
        if result.status == "failed":
            metrics["failures"] += 1

        # Emit completion event
        event_type = (
            Events.EXECUTION_COMPLETED
            if result.status == "completed"
            else Events.EXECUTION_FAILED
        )
        await event_bus.emit(event_type, {
            "execution_id": result.execution_id,
            "agent_id": agent_id,
            "status": result.status,
            "total_latency_ms": result.total_latency_ms,
            "total_cost_usd": result.total_cost_usd,
            "step_count": len(result.steps),
        })

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def agent_metrics(self, agent_id: str) -> dict:
        return self._metrics.get(agent_id, {
            "executions": 0, "total_latency_ms": 0.0, "failures": 0,
        })
