"""Gnosis Dead Letter Queue — Failed operations with retry capability."""

import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.dlq")


@dataclass
class DLQEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation: str = ""  # "execution", "pipeline", "webhook", "memory_store", etc.
    error: str = ""
    payload: dict = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    status: str = "pending"  # pending, retrying, resolved, expired
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_retry_at: Optional[str] = None
    resolved_at: Optional[str] = None


class DeadLetterQueue:
    """Stores failed operations for inspection and retry."""

    def __init__(self, max_entries: int = 5000):
        self._entries: Dict[str, DLQEntry] = {}
        self._max = max_entries

    def push(
        self, operation: str, error: str, payload: dict = None, max_retries: int = 3
    ) -> DLQEntry:
        entry = DLQEntry(
            operation=operation,
            error=error,
            payload=payload or {},
            max_retries=max_retries,
        )
        self._entries[entry.id] = entry

        # Trim if over limit
        if len(self._entries) > self._max:
            oldest = sorted(self._entries.values(), key=lambda e: e.created_at)
            for e in oldest[: len(self._entries) - self._max]:
                del self._entries[e.id]

        logger.warning(f"DLQ entry: [{operation}] {error[:100]}")
        return entry

    def get(self, entry_id: str) -> Optional[DLQEntry]:
        return self._entries.get(entry_id)

    def list_entries(
        self, operation: str = None, status: str = None, limit: int = 50
    ) -> List[dict]:
        entries = list(self._entries.values())
        if operation:
            entries = [e for e in entries if e.operation == operation]
        if status:
            entries = [e for e in entries if e.status == status]
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return [asdict(e) for e in entries[:limit]]

    def mark_resolved(self, entry_id: str) -> bool:
        entry = self._entries.get(entry_id)
        if entry:
            entry.status = "resolved"
            entry.resolved_at = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def retry(self, entry_id: str) -> Optional[dict]:
        entry = self._entries.get(entry_id)
        if not entry:
            return None
        if entry.retry_count >= entry.max_retries:
            entry.status = "expired"
            return {"status": "expired", "message": "Max retries exceeded"}
        entry.retry_count += 1
        entry.last_retry_at = datetime.now(timezone.utc).isoformat()
        entry.status = "retrying"
        return {
            "status": "retrying",
            "retry_count": entry.retry_count,
            "payload": entry.payload,
        }

    def purge_resolved(self) -> int:
        resolved = [
            eid
            for eid, e in self._entries.items()
            if e.status in ("resolved", "expired")
        ]
        for eid in resolved:
            del self._entries[eid]
        return len(resolved)

    @property
    def stats(self) -> dict:
        statuses = {}
        operations = {}
        for e in self._entries.values():
            statuses[e.status] = statuses.get(e.status, 0) + 1
            operations[e.operation] = operations.get(e.operation, 0) + 1
        return {
            "total": len(self._entries),
            "by_status": statuses,
            "by_operation": operations,
        }


dead_letter_queue = DeadLetterQueue()
