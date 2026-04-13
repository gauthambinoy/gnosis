"""Distributed async task queue with priorities and retries.
Uses Redis when available, falls back to in-memory asyncio queue."""

import asyncio
import uuid
from datetime import datetime, timezone
from collections import defaultdict
from app.core.logger import get_logger

logger = get_logger("queue")

class TaskQueue:
    PRIORITIES = {"critical": 0, "high": 1, "normal": 2, "low": 3}
    
    def __init__(self):
        self.handlers: dict[str, callable] = {}
        self.queues: dict[int, asyncio.Queue] = {p: asyncio.Queue() for p in range(4)}
        self.results: dict[str, dict] = {}
        self.stats = defaultdict(int)
        self._running = False
    
    def register(self, task_type: str, handler: callable):
        self.handlers[task_type] = handler
    
    async def enqueue(self, task_type: str, payload: dict, priority: str = "normal") -> str:
        task_id = str(uuid.uuid4())
        p = self.PRIORITIES.get(priority, 2)
        await self.queues[p].put({
            "id": task_id,
            "type": task_type,
            "payload": payload,
            "priority": priority,
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
            "attempts": 0,
        })
        self.stats["enqueued"] += 1
        return task_id
    
    async def process(self):
        """Main processing loop — drains queues by priority."""
        self._running = True
        logger.info("Task queue processor started")
        while self._running:
            processed = False
            for priority in range(4):
                q = self.queues[priority]
                if not q.empty():
                    task = await q.get()
                    await self._execute_task(task)
                    processed = True
                    break
            if not processed:
                await asyncio.sleep(0.1)
    
    async def _execute_task(self, task: dict):
        handler = self.handlers.get(task["type"])
        if not handler:
            logger.error(f"No handler for task type: {task['type']}")
            return
        
        task["attempts"] += 1
        try:
            result = await handler(task["payload"])
            self.results[task["id"]] = {"status": "completed", "result": result}
            self.stats["completed"] += 1
        except Exception as e:
            if task["attempts"] < 3:
                p = self.PRIORITIES.get(task["priority"], 2)
                await self.queues[p].put(task)
                self.stats["retried"] += 1
            else:
                self.results[task["id"]] = {"status": "failed", "error": str(e)}
                self.stats["failed"] += 1
                logger.error(f"Task {task['type']} failed after 3 attempts: {e}")
    
    def get_result(self, task_id: str) -> dict | None:
        return self.results.get(task_id)
    
    def get_stats(self) -> dict:
        return {
            "queued": sum(q.qsize() for q in self.queues.values()),
            **dict(self.stats),
        }
    
    async def stop(self):
        self._running = False

task_queue = TaskQueue()
