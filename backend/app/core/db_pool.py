"""Database connection pool monitoring and management."""

from app.core.database import engine
from app.core.logger import get_logger

logger = get_logger("db_pool")

class DBPoolManager:
    def get_pool_status(self) -> dict:
        try:
            pool = engine.pool
            return {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "status": "healthy" if pool.checkedout() < pool.size() else "busy",
            }
        except Exception as e:
            return {"status": "unavailable", "error": str(e)}

db_pool_manager = DBPoolManager()
