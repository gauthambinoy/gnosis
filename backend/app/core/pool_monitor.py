"""Gnosis Pool Monitor — monitor DB and Redis connection pool health."""
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class PoolHealth:
    name: str
    total: int
    active: int
    idle: int
    waiting: int
    overflow: int
    health: str


class PoolMonitor:
    """Monitors connection pool health for database and Redis."""

    def __init__(self):
        self._history: list[dict] = []

    def check_db_pool(self) -> PoolHealth:
        try:
            from app.core.database import engine
            pool = engine.pool
            health = PoolHealth(
                name="database",
                total=pool.size(),
                active=pool.checkedout(),
                idle=pool.checkedin(),
                waiting=0,
                overflow=pool.overflow(),
                health="healthy" if pool.checkedout() < pool.size() else "saturated",
            )
        except Exception:
            health = PoolHealth(name="database", total=0, active=0, idle=0, waiting=0, overflow=0, health="unavailable")
        self._record(health)
        return health

    def check_redis_pool(self) -> PoolHealth:
        try:
            from app.core.redis_client import redis_pool
            info = redis_pool.connection_pool
            health = PoolHealth(
                name="redis",
                total=info.max_connections or 0,
                active=len(info._in_use_connections) if hasattr(info, "_in_use_connections") else 0,
                idle=len(info._available_connections) if hasattr(info, "_available_connections") else 0,
                waiting=0,
                overflow=0,
                health="healthy",
            )
        except Exception:
            health = PoolHealth(name="redis", total=0, active=0, idle=0, waiting=0, overflow=0, health="unavailable")
        self._record(health)
        return health

    def get_all_pools(self) -> list[PoolHealth]:
        return [self.check_db_pool(), self.check_redis_pool()]

    def _record(self, health: PoolHealth):
        from dataclasses import asdict
        entry = asdict(health)
        entry["checked_at"] = datetime.now(timezone.utc).isoformat()
        self._history.append(entry)
        if len(self._history) > 1000:
            self._history = self._history[-500:]


pool_monitor = PoolMonitor()
