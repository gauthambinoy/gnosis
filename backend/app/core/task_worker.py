import asyncio
from datetime import datetime, timezone


class TaskWorker:
    """Background task scheduler for periodic jobs."""

    def __init__(self):
        self.tasks: dict[str, dict] = {}
        self._running = False

    def register(self, name: str, func, interval_seconds: int):
        """Register a periodic task."""
        self.tasks[name] = {
            "func": func,
            "interval": interval_seconds,
            "last_run": None,
            "run_count": 0,
            "errors": 0,
        }

    async def start(self):
        """Start the background worker loop."""
        self._running = True
        print("◎ Task worker started")
        while self._running:
            now = datetime.now(timezone.utc)
            for name, task in self.tasks.items():
                if task["last_run"] is None or \
                   (now - task["last_run"]).total_seconds() >= task["interval"]:
                    try:
                        await task["func"]()
                        task["last_run"] = now
                        task["run_count"] += 1
                    except Exception as e:
                        task["errors"] += 1
                        print(f"⚠ Task {name} failed: {e}")
            await asyncio.sleep(10)

    async def stop(self):
        self._running = False

    def status(self) -> dict:
        return {
            name: {k: str(v) for k, v in t.items() if k != "func"}
            for name, t in self.tasks.items()
        }


task_worker = TaskWorker()
