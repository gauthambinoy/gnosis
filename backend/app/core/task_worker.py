import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DEFAULT_TASK_TIMEOUT = 300  # 5 minutes


async def execute_with_timeout(coro, timeout_seconds=DEFAULT_TASK_TIMEOUT):
    """Wrap a coroutine with a timeout guard."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.error(f"Task timed out after {timeout_seconds}s")
        raise


class TaskWorker:
    """Background task scheduler for periodic jobs."""

    def __init__(self):
        self.tasks: dict[str, dict] = {}
        self._running = False

    def register(
        self,
        name: str,
        func,
        interval_seconds: int,
        timeout_seconds: int = DEFAULT_TASK_TIMEOUT,
    ):
        """Register a periodic task."""
        self.tasks[name] = {
            "func": func,
            "interval": interval_seconds,
            "timeout": timeout_seconds,
            "last_run": None,
            "run_count": 0,
            "errors": 0,
        }

    async def start(self):
        """Start the background worker loop."""
        self._running = True
        logger.info("task_worker.started")
        while self._running:
            now = datetime.now(timezone.utc)
            for name, task in self.tasks.items():
                if (
                    task["last_run"] is None
                    or (now - task["last_run"]).total_seconds() >= task["interval"]
                ):
                    try:
                        await execute_with_timeout(task["func"](), task["timeout"])
                        task["last_run"] = now
                        task["run_count"] += 1
                    except asyncio.TimeoutError:
                        task["errors"] += 1
                        logger.error(
                            "task_worker.timeout name=%s timeout=%ss",
                            name,
                            task["timeout"],
                        )
                    except Exception:
                        task["errors"] += 1
                        logger.exception("task_worker.failed name=%s", name)
            await asyncio.sleep(10)

    async def stop(self):
        self._running = False

    def status(self) -> dict:
        return {
            name: {k: str(v) for k, v in t.items() if k != "func"}
            for name, t in self.tasks.items()
        }


task_worker = TaskWorker()
