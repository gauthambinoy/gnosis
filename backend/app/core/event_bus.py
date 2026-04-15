"""Redis-backed event bus for cross-service communication."""
import logging
import json
import asyncio
from typing import Callable, Awaitable
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

REDIS_CHANNEL = "gnosis:events"

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
    """In-process event bus with Redis pub/sub for distributed events."""

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
        """Emit an event to all registered handlers and Redis pub/sub."""
        event = {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Publish to Redis if available (non-blocking, best-effort)
        try:
            from app.core.redis_client import redis_manager
            if redis_manager.available:
                await redis_manager.publish(REDIS_CHANNEL, json.dumps(event))
        except Exception:
            logger.debug("Redis publish failed, event delivered in-process only", exc_info=True)

        handlers = self._handlers.get(event_type, [])
        # Also notify wildcard handlers
        handlers += self._handlers.get("*", [])

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"Event handler error for {event_type}: {e}")

    async def subscribe_redis(self):
        """Subscribe to Redis pub/sub channel for distributed event listening.

        Returns a pubsub object to iterate over, or None if Redis is unavailable.
        """
        try:
            from app.core.redis_client import redis_manager
            return await redis_manager.subscribe(REDIS_CHANNEL)
        except Exception:
            return None

    def recent_events(self, limit: int = 20) -> list[dict]:
        return self._history[-limit:]


# Global singleton
event_bus = EventBus()
