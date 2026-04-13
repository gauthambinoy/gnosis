import json
from app.core.redis_client import redis_manager


class SessionStore:
    """Redis-backed session store for auth tokens."""

    def __init__(self):
        self._memory_sessions: dict[str, dict] = {}

    async def store_session(self, user_id: str, token_jti: str, ttl: int = 3600):
        """Store active session in Redis."""
        session_data = json.dumps({"user_id": user_id, "active": True})
        if redis_manager.available:
            await redis_manager.set(f"session:{token_jti}", session_data, ttl=ttl)
            # Track per-user sessions for bulk revocation
            await redis_manager.client.sadd(f"user_sessions:{user_id}", token_jti)
            await redis_manager.client.expire(f"user_sessions:{user_id}", ttl)
        else:
            self._memory_sessions[token_jti] = {"user_id": user_id, "active": True}

    async def is_valid_session(self, token_jti: str) -> bool:
        """Check if session is still valid (not revoked)."""
        if redis_manager.available:
            data = await redis_manager.get(f"session:{token_jti}")
            if data is None:
                return False
            session = json.loads(data)
            return session.get("active", False)
        else:
            session = self._memory_sessions.get(token_jti)
            return session is not None and session.get("active", False)

    async def revoke_session(self, token_jti: str):
        """Revoke a session (logout)."""
        if redis_manager.available:
            await redis_manager.delete(f"session:{token_jti}")
        else:
            self._memory_sessions.pop(token_jti, None)

    async def revoke_all_sessions(self, user_id: str):
        """Revoke all sessions for a user."""
        if redis_manager.available:
            members = await redis_manager.client.smembers(f"user_sessions:{user_id}")
            for jti in members:
                await redis_manager.delete(f"session:{jti}")
            await redis_manager.delete(f"user_sessions:{user_id}")
        else:
            to_remove = [
                jti for jti, s in self._memory_sessions.items()
                if s.get("user_id") == user_id
            ]
            for jti in to_remove:
                del self._memory_sessions[jti]


session_store = SessionStore()
