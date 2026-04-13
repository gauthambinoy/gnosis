"""Gnosis Memory Engine — 4-tier memory system."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class MemoryEntry:
    id: str
    agent_id: str
    tier: str  # episodic, semantic, procedural, correction
    content: str
    relevance_score: float = 1.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)


@dataclass
class MemoryContext:
    corrections: list[MemoryEntry]
    recent: list[dict]
    relevant_past: list[MemoryEntry]
    knowledge: list[MemoryEntry]
    procedures: list[MemoryEntry]


class MemoryEngine:
    """4-tier memory with parallel retrieval."""

    async def retrieve_context(self, agent_id: str, trigger_data: dict) -> MemoryContext:
        return MemoryContext(corrections=[], recent=[], relevant_past=[], knowledge=[], procedures=[])

    async def store(self, agent_id: str, tier: str, content: str, metadata: dict | None = None) -> MemoryEntry:
        return MemoryEntry(id="mem-placeholder", agent_id=agent_id, tier=tier, content=content, metadata=metadata or {})

    async def store_correction(self, agent_id: str, original_action: str, correction: str, context: dict) -> MemoryEntry:
        return await self.store(agent_id=agent_id, tier="correction", content=f"CORRECTION: Was '{original_action}' → Should be '{correction}'", metadata={"original": original_action, "correction": correction, "context": context})
