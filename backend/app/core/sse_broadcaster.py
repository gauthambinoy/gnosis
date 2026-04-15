"""Server-Sent Events broadcaster for real-time dashboard updates."""
import asyncio
import json
import logging
from typing import Dict, Set, AsyncGenerator
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.sse")

class SSEBroadcaster:
    """Manages SSE connections and broadcasts events to subscribers."""

    def __init__(self):
        self._channels: Dict[str, Set[asyncio.Queue]] = {}  # channel -> set of queues
        self._event_count = 0

    def subscribe(self, channel: str) -> asyncio.Queue:
        """Subscribe to a channel. Returns a queue that receives events."""
        if channel not in self._channels:
            self._channels[channel] = set()
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._channels[channel].add(queue)
        logger.info(f"SSE subscriber added to {channel} (total: {len(self._channels[channel])})")
        return queue

    def unsubscribe(self, channel: str, queue: asyncio.Queue):
        """Unsubscribe from a channel."""
        if channel in self._channels:
            self._channels[channel].discard(queue)
            if not self._channels[channel]:
                del self._channels[channel]

    async def publish(self, channel: str, event_type: str, data: dict):
        """Publish an event to all subscribers of a channel."""
        if channel not in self._channels:
            return

        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._event_count += 1

        dead_queues = set()
        for queue in self._channels[channel]:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead_queues.add(queue)

        for q in dead_queues:
            self._channels[channel].discard(q)

    async def broadcast(self, event_type: str, data: dict):
        """Broadcast to ALL channels."""
        for channel in list(self._channels.keys()):
            await self.publish(channel, event_type, data)

    async def event_stream(self, channel: str) -> AsyncGenerator[str, None]:
        """Generate SSE events for a subscriber."""
        queue = self.subscribe(channel)
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'channel': channel})}\n\n"

            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f": keepalive\n\n"
        finally:
            self.unsubscribe(channel, queue)

    @property
    def stats(self) -> dict:
        return {
            "channels": len(self._channels),
            "total_subscribers": sum(len(subs) for subs in self._channels.values()),
            "total_events": self._event_count,
            "channel_details": {ch: len(subs) for ch, subs in self._channels.items()},
        }

sse_broadcaster = SSEBroadcaster()
