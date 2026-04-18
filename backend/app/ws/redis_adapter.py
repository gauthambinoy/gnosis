"""Redis pub/sub adapter for WebSocket scaling across multiple server instances."""

import json
import asyncio
from app.core.redis_client import redis_manager
from app.core.logger import get_logger

logger = get_logger("ws.redis")


class WebSocketRedisAdapter:
    """Bridges local WebSocket manager with Redis pub/sub for horizontal scaling."""

    CHANNEL = "gnosis:ws:broadcast"

    def __init__(self):
        self._listener_task = None
        self._local_broadcast = None  # Set to ws_manager.broadcast

    def set_local_broadcaster(self, func):
        self._local_broadcast = func

    async def publish(self, event_type: str, data: dict, room: str = None):
        """Publish WS message to all server instances via Redis."""
        message = json.dumps({"event": event_type, "data": data, "room": room})
        if redis_manager.available:
            await redis_manager.publish(self.CHANNEL, message)
        elif self._local_broadcast:
            await self._local_broadcast(event_type, data)

    async def start_listener(self):
        """Subscribe to Redis channel and broadcast to local WS connections."""
        if not redis_manager.available:
            logger.info("Redis unavailable — WS adapter in local-only mode")
            return

        pubsub = await redis_manager.subscribe(self.CHANNEL)
        if not pubsub:
            return

        async def _listen():
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        data = json.loads(message["data"])
                        if self._local_broadcast:
                            await self._local_broadcast(data["event"], data["data"])
            except Exception as e:
                logger.error(f"WS Redis listener error: {e}")

        self._listener_task = asyncio.create_task(_listen())
        logger.info("WS Redis adapter listening")

    async def stop(self):
        if self._listener_task:
            self._listener_task.cancel()


ws_redis_adapter = WebSocketRedisAdapter()
