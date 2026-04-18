"""Automatic execution retry with exponential backoff."""
import asyncio
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.retry")

@dataclass
class RetryRecord:
    execution_id: str
    attempt: int = 0
    max_attempts: int = 3
    status: str = "pending"  # pending, retrying, succeeded, exhausted
    errors: List[str] = field(default_factory=list)
    next_retry_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None

class RetryEngine:
    """Manages automatic retries with exponential backoff."""

    def __init__(self, max_attempts: int = 3, base_delay: float = 2.0, max_delay: float = 60.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._records: Dict[str, RetryRecord] = {}
        self._retry_count = 0
        self._success_count = 0

    def _backoff_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        # Add jitter (±25%)
        import random
        jitter = delay * 0.25 * (random.random() * 2 - 1)
        return max(0.1, delay + jitter)

    async def execute_with_retry(self, execution_id: str, fn: Callable, *args, **kwargs) -> Any:
        """Execute a function with automatic retry on failure."""
        record = RetryRecord(execution_id=execution_id, max_attempts=self.max_attempts)
        self._records[execution_id] = record

        for attempt in range(self.max_attempts):
            record.attempt = attempt + 1
            record.status = "retrying" if attempt > 0 else "pending"

            try:
                result = await fn(*args, **kwargs)
                record.status = "succeeded"
                record.completed_at = datetime.now(timezone.utc).isoformat()
                self._success_count += 1
                if attempt > 0:
                    logger.info(f"Retry succeeded: {execution_id} on attempt {attempt + 1}")
                return result

            except Exception as e:
                record.errors.append(f"Attempt {attempt + 1}: {str(e)[:200]}")
                logger.warning(f"Execution failed: {execution_id}, attempt {attempt + 1}/{self.max_attempts}: {e}")

                if attempt < self.max_attempts - 1:
                    delay = self._backoff_delay(attempt)
                    record.next_retry_at = datetime.now(timezone.utc).isoformat()
                    self._retry_count += 1
                    logger.info(f"Retrying {execution_id} in {delay:.1f}s (attempt {attempt + 2})")
                    await asyncio.sleep(delay)
                else:
                    record.status = "exhausted"
                    record.completed_at = datetime.now(timezone.utc).isoformat()
                    logger.error(f"All retries exhausted: {execution_id}")
                    raise

    def get_record(self, execution_id: str) -> Optional[dict]:
        record = self._records.get(execution_id)
        return asdict(record) if record else None

    def list_records(self, status: str = None, limit: int = 50) -> List[dict]:
        records = list(self._records.values())
        if status:
            records = [r for r in records if r.status == status]
        records.sort(key=lambda r: r.created_at, reverse=True)
        return [asdict(r) for r in records[:limit]]

    @property
    def stats(self) -> dict:
        statuses = {}
        for r in self._records.values():
            statuses[r.status] = statuses.get(r.status, 0) + 1
        return {
            "total_tracked": len(self._records),
            "total_retries": self._retry_count,
            "total_successes": self._success_count,
            "by_status": statuses,
        }

retry_engine = RetryEngine()
