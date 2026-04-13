"""Unit tests for core engines: memory, context, builder, cost, trust, guardrails."""
import pytest

pytestmark = pytest.mark.anyio


# ── Memory Engine ────────────────────────────────────────────────────

async def test_memory_engine_store_search():
    from app.core.memory_engine import MemoryEngine
    engine = MemoryEngine()
    entry = await engine.store("agent-unit-1", "semantic", "The sky is blue")
    assert entry.agent_id == "agent-unit-1"
    assert entry.tier == "semantic"
    results = await engine.search_memories("agent-unit-1", "The sky is blue")
    assert len(results) >= 1
    assert any("sky" in r.content.lower() for r in results)


# ── Context Assembler ────────────────────────────────────────────────

def test_context_assembler():
    from app.core.context_assembler import ContextAssembler, MAX_CONTEXT_TOKENS, CHARS_PER_TOKEN
    from app.core.memory_engine import MemoryEntry, MemoryContext

    ctx = MemoryContext(
        corrections=[MemoryEntry(id="c1", agent_id="a", tier="correction", content="Never delete files")],
        recent=[MemoryEntry(id="r1", agent_id="a", tier="sensory", content="User said hello")],
        relevant_past=[MemoryEntry(id="e1", agent_id="a", tier="episodic", content="Handled ticket #42")],
        knowledge=[MemoryEntry(id="k1", agent_id="a", tier="semantic", content="CEO is Alice")],
        procedures=[MemoryEntry(id="p1", agent_id="a", tier="procedural", content="Always greet first")],
    )
    assembler = ContextAssembler()
    result = assembler.assemble(ctx, trigger_summary="New email from Bob")
    assert len(result) <= MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN
    assert "CORRECTIONS" in result
    assert "CURRENT TRIGGER" in result


def test_context_assembler_token_estimate():
    from app.core.context_assembler import ContextAssembler
    assembler = ContextAssembler()
    tokens = assembler.estimate_tokens("hello world test string")
    assert tokens > 0


# ── Agent Builder ────────────────────────────────────────────────────

async def test_agent_builder():
    from app.core.builder import AgentBuilder
    builder = AgentBuilder()
    config = await builder.build_from_description(
        "Monitor my Gmail inbox every day and log invoices to Google Sheets"
    )
    assert config.name
    assert config.trigger_type == "schedule"
    assert "gmail" in config.integrations_needed
    assert "sheets" in config.integrations_needed
    assert len(config.steps) >= 1


# ── Cost Tracker ─────────────────────────────────────────────────────

def test_cost_tracker():
    from app.core.cost_tracker import CostTracker
    tracker = CostTracker()
    tracker.record("agent-x", "L2", "gpt-4", 100, 50, 0.005)
    tracker.record("agent-x", "L1", "gpt-3.5", 50, 25, 0.001)
    stats = tracker.total_stats
    assert stats["total_tokens"] == 225
    assert stats["total_requests"] == 2
    agent = tracker.agent_stats("agent-x")
    assert agent["requests"] == 2
    records = tracker.recent_records(10)
    assert len(records) == 2


# ── Trust Engine ─────────────────────────────────────────────────────

def test_trust_engine_levels():
    from app.core.trust_engine import TrustEngine
    engine = TrustEngine()
    assert engine.get_trust_level("new-agent") == 0
    engine.set_trust_level("new-agent", 2)
    assert engine.get_trust_level("new-agent") == 2
    assert engine.LEVELS[2]["name"] == "Operator"
    assert "execute_safe" in engine.LEVELS[2]["permissions"]
    engine.set_trust_level("new-agent", 4)
    assert engine.get_trust_level("new-agent") == 4


def test_trust_engine_record():
    from app.core.trust_engine import TrustEngine
    engine = TrustEngine()
    for _ in range(5):
        engine.record_execution("rec-agent", success=True)
    engine.record_execution("rec-agent", success=False)
    history = engine._agent_history["rec-agent"]
    assert len(history) == 6
    successes = sum(1 for r in history if r["success"])
    assert successes == 5


# ── Guardrail Engine ─────────────────────────────────────────────────

async def test_guardrail_check_mass_email():
    from app.core.guardrails import GuardrailEngine
    engine = GuardrailEngine()
    result = await engine.check("agent-g", {"email_recipients": 15})
    assert result["passed"] is False
    assert len(result["violations"]) >= 1
    assert any(v["rule_id"] == "no-mass-email" for v in result["violations"])


async def test_guardrail_check_safe_action():
    from app.core.guardrails import GuardrailEngine
    engine = GuardrailEngine()
    result = await engine.check("agent-g", {"type": "read", "email_recipients": 3})
    assert result["passed"] is True


async def test_guardrail_pii_detection():
    from app.core.guardrails import GuardrailEngine
    engine = GuardrailEngine()
    result = await engine.check("agent-g", {"output": "SSN is 123-45-6789"})
    assert result["passed"] is False
    assert any(v["rule_id"] == "pii-check" for v in result["violations"])


async def test_guardrail_delete_action():
    from app.core.guardrails import GuardrailEngine
    engine = GuardrailEngine()
    result = await engine.check("agent-g", {"type": "delete"})
    assert result["passed"] is False
    assert any(v["rule_id"] == "no-delete" for v in result["violations"])
