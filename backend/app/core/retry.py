import asyncio
import random
import uuid
from datetime import datetime, timezone

from app.core.logger import get_logger

logger = get_logger("retry")


class DeadLetterQueue:
    """Stores permanently failed tasks for manual review."""

    def __init__(self):
        self.items: list[dict] = []

    def add(self, task_type: str, payload: dict, error: str, attempts: int):
        self.items.append({
            "id": str(uuid.uuid4()),
            "task_type": task_type,
            "payload": payload,
            "error": error,
            "attempts": attempts,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.error(f"DLQ: {task_type} failed after {attempts} attempts: {error}")

    def get_all(self, limit: int = 50) -> list[dict]:
        return self.items[-limit:]

    def retry(self, item_id: str) -> dict | None:
        for item in self.items:
            if item["id"] == item_id:
                self.items.remove(item)
                return item
        return None


dlq = DeadLetterQueue()


async def with_retry(
    func,
    *args,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    task_name: str = "task",
    **kwargs,
):
    """Execute async function with exponential backoff retry. DLQ on final failure."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = delay * (backoff ** attempt) * random.uniform(0.8, 1.2)
                logger.warning(f"Retry {attempt+1}/{max_retries} for {task_name}: {e}, waiting {wait}s")
                await asyncio.sleep(wait)

    dlq.add(task_name, {"args": str(args)}, str(last_error), max_retries)
    raise last_error
