"""Gnosis Orchestrator — Perceive → Reason → Decide → Act execution engine."""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
import re
import time
import uuid

from app.core.memory_engine import MemoryEngine, memory_engine
from app.core.context_assembler import ContextAssembler, context_assembler
from app.core.event_bus import event_bus, Events
from app.core.embeddings import embedding_service
from app.core.execution_recorder import execution_recorder
from app.llm.router import ModelRouter, model_router
from app.ws.execution_stream import execution_stream
from app.core.confidence import confidence_engine

logger = logging.getLogger(__name__)


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
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExecutionResult:
    execution_id: str
    agent_id: str
    steps: list[ExecutionStep]
    status: str = "completed"
    total_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    confidence: dict = field(default_factory=dict)


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
    def _get_aws(self):
        """Lazy import to avoid circular dependency at module load."""
        try:
            from app.core.aws_services import aws_services
            return aws_services
        except Exception:
            return None

    async def execute(
        self, agent_id: str, trigger_type: str, trigger_data: dict,
        async_execution: bool = False,
    ) -> ExecutionResult:
        # If async_execution requested, try to queue via SQS
        if async_execution:
            aws = self._get_aws()
            if aws:
                user_input = trigger_data.get("body", trigger_data.get("content", ""))
                user_id = trigger_data.get("user_id", "")
                msg_id = await aws.send_execution_task(agent_id, user_input, user_id)
                if msg_id:
                    return ExecutionResult(
                        execution_id=msg_id,
                        agent_id=agent_id,
                        steps=[ExecutionStep(phase="queued", content=f"Queued via SQS: {msg_id}")],
                        status="queued",
                    )

        execution_id = str(uuid.uuid4())
        steps: list[ExecutionStep] = []
        total_start = time.time()

        # Start execution recording for replay
        task_summary = str(trigger_data.get("subject", trigger_data.get("title", str(trigger_type))))
        recording = execution_recorder.start_recording(agent_id, task_summary)

        await event_bus.emit(Events.EXECUTION_STARTED, {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "trigger_type": trigger_type,
        })

        try:
            # Phase 1 — Perceive
            await execution_stream.broadcast_phase(agent_id, "perceive", {"status": "started", "input": str(trigger_data)[:200]})
            perception = await self._perceive(trigger_type, trigger_data)
            steps.append(perception)
            execution_recorder.add_step(recording.id, "perceive", "completed", input_summary=str(trigger_data)[:200], output_summary=perception.content[:200], duration_ms=perception.latency_ms)
            await execution_stream.broadcast_phase(agent_id, "perceive", {"status": "completed", "duration_ms": perception.latency_ms})

            # Phase 2 — Memory Retrieval (parallel across tiers)
            await execution_stream.broadcast_phase(agent_id, "memory", {"status": "started"})
            memory_step = await self._retrieve_memory(agent_id, trigger_data)
            steps.append(memory_step)
            execution_recorder.add_step(recording.id, "memory", "completed", output_summary=memory_step.content[:200], duration_ms=memory_step.latency_ms)
            await execution_stream.broadcast_phase(agent_id, "memory", {"status": "completed", "duration_ms": memory_step.latency_ms})

            # Phase 3 — Context Assembly
            await execution_stream.broadcast_phase(agent_id, "context", {"status": "started"})
            context_step = await self._assemble_context(
                memory_step.metadata.get("memory_context"),
                perception.metadata.get("summary", ""),
            )
            steps.append(context_step)
            execution_recorder.add_step(recording.id, "context", "completed", output_summary=f"Assembled {context_step.metadata.get('estimated_tokens', 0)} tokens", duration_ms=context_step.latency_ms)
            await execution_stream.broadcast_phase(agent_id, "context", {"status": "completed", "duration_ms": context_step.latency_ms})

            # Phase 4 — Reasoning via LLM
            await execution_stream.broadcast_phase(agent_id, "reason", {"status": "started"})
            urgency = perception.metadata.get("urgency", "low")
            reasoning = await self._reason(agent_id, context_step, urgency)
            steps.append(reasoning)
            execution_recorder.add_step(recording.id, "reason", "completed", output_summary=reasoning.content[:200], duration_ms=reasoning.latency_ms, metadata={"tier": reasoning.metadata.get("tier")})
            await execution_stream.broadcast_phase(agent_id, "reason", {"status": "completed", "duration_ms": reasoning.latency_ms})

            # Phase 5 — Meta-cognition (confidence check)
            await execution_stream.broadcast_phase(agent_id, "meta", {"status": "started"})
            meta_step = self._meta_cognition(reasoning)
            steps.append(meta_step)
            execution_recorder.add_step(recording.id, "meta", "completed", output_summary=meta_step.content[:200], duration_ms=meta_step.latency_ms, metadata={"confidence": meta_step.confidence})
            await execution_stream.broadcast_phase(agent_id, "meta", {"status": "completed", "confidence": meta_step.confidence})

            # Phase 6 — Action execution
            await execution_stream.broadcast_phase(agent_id, "act", {"status": "started"})
            actions = await self._act(agent_id, meta_step)
            steps.extend(actions)
            act_latency = sum(a.latency_ms for a in actions)
            execution_recorder.add_step(recording.id, "act", "completed", output_summary=f"Executed {len(actions)} action(s)", duration_ms=act_latency)
            await execution_stream.broadcast_phase(agent_id, "act", {"status": "completed", "duration_ms": act_latency})

            status = "completed"
        except Exception as exc:
            steps.append(ExecutionStep(
                phase="error", content=str(exc), confidence=0.0,
                latency_ms=0.0,
            ))
            status = "failed"
            execution_recorder.add_step(recording.id, "error", "failed", output_summary=str(exc)[:200])

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

        # Compute confidence scoring
        mem_ctx = memory_step.metadata.get("memory_context")
        confidence = confidence_engine.score(
            memory_results=len(mem_ctx.relevant_past) if hasattr(mem_ctx, 'relevant_past') and mem_ctx else 0,
            memory_max_score=max((m.relevance_score for m in mem_ctx.relevant_past), default=0) if hasattr(mem_ctx, 'relevant_past') and mem_ctx else 0,
            context_tokens=len(str(context_step.content)) // 4 if context_step.content else 0,
            reasoning_level=2,
            response_length=len(str(reasoning.content)) if reasoning.content else 0,
        )
        result.confidence = {
            "overall": confidence.overall,
            "memory_match": confidence.memory_match,
            "model_certainty": confidence.model_certainty,
            "context_coverage": confidence.context_coverage,
            "reasoning_depth": confidence.reasoning_depth,
            "explanation": confidence.explanation,
        }

        # Phase 7 — Post-execution
        await execution_stream.broadcast_phase(agent_id, "post", {"status": "started"})
        await self._post_execution(agent_id, result)
        execution_recorder.add_step(recording.id, "post", "completed", output_summary=f"status={status} latency={total_ms:.0f}ms", duration_ms=result.total_latency_ms)
        execution_recorder.complete_recording(recording.id, status)
        await execution_stream.broadcast_phase(agent_id, "post", {"status": "completed", "duration_ms": result.total_latency_ms})

        # Log execution to DynamoDB (best-effort, never blocks return)
        try:
            aws = self._get_aws()
            if aws:
                await aws.log_execution(
                    agent_id=agent_id,
                    user_id=trigger_data.get("user_id", ""),
                    result={
                        "execution_id": execution_id,
                        "status": status,
                        "duration_ms": total_ms,
                        "tokens_used": sum(s.metadata.get("tokens", 0) for s in steps),
                        "total_cost_usd": total_cost,
                    },
                )
        except Exception:
            logger.debug("DynamoDB post-execution logging failed", exc_info=True)

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
            logger.warning("Orchestrator action execution failed", exc_info=True)

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
