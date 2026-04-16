"""Gnosis Execution Queue — priority-based execution scheduling."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
import heapq


@dataclass
class QueuedExecution:
    id: str
    agent_id: str
    task: str
    priority: int
    status: str = "queued"
    queued_at: str = ""
    started_at: str | None = None
    user_id: str = ""

    def __post_init__(self):
        if not self.queued_at:
            self.queued_at = datetime.now(timezone.utc).isoformat()


class ExecutionQueue:
    """Priority queue for agent execution scheduling."""

    def __init__(self):
        self._items: dict[str, QueuedExecution] = {}
        self._heap: list[tuple[int, str, str]] = []  # (-priority, queued_at, id)

    def enqueue(self, agent_id: str, task: str, priority: int = 5, user_id: str = "") -> QueuedExecution:
        priority = max(1, min(10, priority))
        item = QueuedExecution(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            task=task,
            priority=priority,
            user_id=user_id,
        )
        self._items[item.id] = item
        heapq.heappush(self._heap, (-priority, item.queued_at, item.id))
        return item

    def dequeue(self) -> QueuedExecution | None:
        while self._heap:
            _neg_pri, _ts, item_id = heapq.heappop(self._heap)
            item = self._items.get(item_id)
            if item and item.status == "queued":
                item.status = "running"
                item.started_at = datetime.now(timezone.utc).isoformat()
                return item
        return None

    def list_queue(self) -> list[QueuedExecution]:
        queued = [i for i in self._items.values() if i.status == "queued"]
        queued.sort(key=lambda x: (-x.priority, x.queued_at))
        return queued

    def get_position(self, item_id: str) -> int | None:
        item = self._items.get(item_id)
        if not item or item.status != "queued":
            return None
        queue = self.list_queue()
        for idx, q in enumerate(queue):
            if q.id == item_id:
                return idx + 1
        return None

    def cancel(self, item_id: str) -> bool:
        item = self._items.get(item_id)
        if item and item.status == "queued":
            item.status = "failed"
            return True
        return False

    def get_item(self, item_id: str) -> QueuedExecution | None:
        return self._items.get(item_id)


execution_queue = ExecutionQueue()
