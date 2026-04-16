"""Idempotency key support for task deduplication."""
import time
import hashlib
from typing import Optional, Any


class IdempotencyStore:
    def __init__(self, ttl_seconds: int = 3600):
        self._store: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl_seconds

    def _cleanup(self):
        now = time.time()
        expired = [k for k, (ts, _) in self._store.items() if now - ts > self._ttl]
        for k in expired:
            del self._store[k]

    def check(self, key: str) -> Optional[Any]:
        self._cleanup()
        if key in self._store:
            _, result = self._store[key]
            return result
        return None

    def store(self, key: str, result: Any):
        self._store[key] = (time.time(), result)

    @staticmethod
    def generate_key(user_id: str, action: str, payload: str) -> str:
        raw = f"{user_id}:{action}:{payload}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]


idempotency_store = IdempotencyStore()
