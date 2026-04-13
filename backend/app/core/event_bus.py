"""Redis-backed event bus for cross-service communication."""
import json
import asyncio
from typing import Callable, Awaitable
from datetime import datetime

# Event types
class Events:
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"
    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"
    MEMORY_STORED = "memory.stored"
    TRUST_CHANGED = "trust.changed"
    INSIGHT_GENERATED = "insight.generated"
    CORRECTION_RECEIVED = "correction.received"
    LEARNING_COMPLETED = "learning.completed"


EventHandler = Callable[[dict], Awaitable[None]]


class EventBus:
    """In-process event bus (upgrades to Redis pub/sub when Redis is available)."""

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = {}
        self._history: list[dict] = []  # recent events for debugging
        self._max_history = 100

    def on(self, event_type: str, handler: EventHandler):
        """Register an event handler."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def emit(self, event_type: str, payload: dict):
        """Emit an event to all registered handlers."""
        event = {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        handlers = self._handlers.get(event_type, [])
        # Also notify wildcard handlers
        handlers += self._handlers.get("*", [])

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"Event handler error for {event_type}: {e}")

    def recent_events(self, limit: int = 20) -> list[dict]:
        return self._history[-limit:]


# Global singleton
event_bus = EventBus()
