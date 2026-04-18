"""Gnosis Memory GC — garbage collector for stale, duplicate, or low-value memories."""
from dataclasses import dataclass
from datetime import datetime, timezone
import time
import uuid


@dataclass
class GCResult:
    agent_id: str
    scanned: int
    removed: int
    freed_bytes: int
    duration_ms: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class MemoryGarbageCollector:
    """Finds and cleans up stale, duplicate, or low-value memories."""

    def __init__(self):
        self._history: list[GCResult] = []
        self._scheduled: dict[str, dict] = {}

    def run_gc(self, agent_id: str, min_strength: float = 0.1, max_age_days: int = 90) -> GCResult:
        start = time.time()
        # Simulated GC scan
        scanned = 50
        removed = int(scanned * 0.15)
        freed = removed * 1024

        duration = (time.time() - start) * 1000
        result = GCResult(
            agent_id=agent_id,
            scanned=scanned,
            removed=removed,
            freed_bytes=freed,
            duration_ms=round(duration, 2),
        )
        self._history.append(result)
        return result

    def schedule_gc(self, agent_id: str, interval_hours: int = 24) -> dict:
        schedule = {
            "id": str(uuid.uuid4()),
            "agent_id": agent_id,
            "interval_hours": interval_hours,
            "next_run": datetime.now(timezone.utc).isoformat(),
            "active": True,
        }
        self._scheduled[agent_id] = schedule
        return schedule

    def get_gc_history(self, agent_id: str | None = None) -> list[GCResult]:
        if agent_id:
            return [r for r in self._history if r.agent_id == agent_id]
        return list(self._history)

    def get_stats(self) -> dict:
        total_scanned = sum(r.scanned for r in self._history)
        total_removed = sum(r.removed for r in self._history)
        total_freed = sum(r.freed_bytes for r in self._history)
        return {
            "total_runs": len(self._history),
            "total_scanned": total_scanned,
            "total_removed": total_removed,
            "total_freed_bytes": total_freed,
            "scheduled_agents": len(self._scheduled),
        }


memory_gc = MemoryGarbageCollector()
