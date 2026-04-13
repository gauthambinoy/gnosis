"""Sentry-compatible error tracking without the SDK dependency.
Captures errors and can forward to Sentry DSN or log locally."""

from datetime import datetime, timezone
from app.core.logger import get_logger

logger = get_logger("sentry")

class ErrorTracker:
    """Lightweight error tracker — captures, deduplicates, and reports errors."""
    
    def __init__(self):
        self.errors: list[dict] = []
        self.error_counts: dict[str, int] = {}  # error_key → count
        self.dsn: str | None = None
        self.max_errors = 1000
    
    def configure(self, dsn: str | None = None):
        self.dsn = dsn
        if dsn:
            logger.info("Error tracking configured with DSN")
    
    def capture_exception(self, exc: Exception, context: dict = None):
        error_key = f"{type(exc).__name__}:{str(exc)[:100]}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        entry = {
            "id": f"err-{len(self.errors)}",
            "type": type(exc).__name__,
            "message": str(exc),
            "count": self.error_counts[error_key],
            "context": context or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.errors.append(entry)
        
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
        
        logger.error(f"Captured: {error_key} (occurrence #{self.error_counts[error_key]})")
    
    def get_recent(self, limit: int = 20) -> list[dict]:
        return list(reversed(self.errors[-limit:]))
    
    def get_top_errors(self, limit: int = 10) -> list[dict]:
        sorted_errors = sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"error": k, "count": v} for k, v in sorted_errors[:limit]]
    
    def get_stats(self) -> dict:
        return {
            "total_captured": len(self.errors),
            "unique_errors": len(self.error_counts),
            "top_3": self.get_top_errors(3),
        }

error_tracker = ErrorTracker()
