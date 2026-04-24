import logging

import redis.asyncio as redis
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class RedisManager:
    """Manages Redis connections for the platform."""

    def __init__(self):
        self._client: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None
        self._available = False

    async def connect(self):
        """Connect to Redis. Gracefully handle unavailability."""
        try:
            self._client = redis.from_url(settings.redis_url, decode_responses=True)
            await self._client.ping()
            self._available = True
            logger.info("redis.connected url=%s", settings.redis_url)
        except Exception as e:
            self._available = False
            logger.warning(
                "redis.unavailable error=%r — using in-memory fallback", e
            )

    @property
    def available(self) -> bool:
        return self._available

    @property
    def client(self) -> redis.Redis | None:
        return self._client if self._available else None

    async def get(self, key: str) -> str | None:
        if not self._available:
            return None
        return await self._client.get(key)

    async def set(self, key: str, value: str, ttl: int = 300):
        if not self._available:
            return
        await self._client.set(key, value, ex=ttl)

    async def delete(self, key: str):
        if not self._available:
            return
        await self._client.delete(key)

    async def publish(self, channel: str, message: str):
        """Publish event to Redis pub/sub."""
        if not self._available:
            return
        await self._client.publish(channel, message)

    async def subscribe(self, *channels):
        """Subscribe to Redis channels."""
        if not self._available:
            return None
        self._pubsub = self._client.pubsub()
        await self._pubsub.subscribe(*channels)
        return self._pubsub

    async def close(self):
        if self._client:
            await self._client.close()


redis_manager = RedisManager()
