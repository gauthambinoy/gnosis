"""Gnosis Agent Scheduler — Cron-based agent execution scheduling."""

import asyncio
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Awaitable
from enum import Enum
import uuid
import re
import logging

logger = logging.getLogger("gnosis.scheduler")


class ScheduleStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"  # For one-shot schedules
    ERROR = "error"


@dataclass
class Schedule:
    id: str
    agent_id: str
    name: str
    cron_expression: str  # "*/5 * * * *" or simplified: "every:5m", "daily:09:00", "weekly:mon:09:00"
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    input_data: dict = field(default_factory=dict)
    max_runs: Optional[int] = None  # None = unlimited
    run_count: int = 0
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error_count: int = 0
    last_error: Optional[str] = None


class CronParser:
    """Parse simplified cron expressions into next-run times."""

    PRESETS = {
        "every_minute": "*/1 * * * *",
        "every_5m": "*/5 * * * *",
        "every_15m": "*/15 * * * *",
        "every_30m": "*/30 * * * *",
        "hourly": "0 * * * *",
        "daily": "0 9 * * *",
        "weekly": "0 9 * * 1",
    }

    @classmethod
    def parse_interval(cls, expression: str) -> Optional[timedelta]:
        """Parse simplified expressions like 'every:5m', 'every:1h', 'every:30s'."""
        if expression in cls.PRESETS:
            expression = cls.PRESETS[expression]

        match = re.match(r"every:(\d+)([smhd])", expression)
        if match:
            value, unit = int(match.group(1)), match.group(2)
            units = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
            return timedelta(**{units[unit]: value})

        # daily:HH:MM
        match = re.match(r"daily:(\d{2}):(\d{2})", expression)
        if match:
            return timedelta(days=1)

        # Simple interval from cron */N format
        match = re.match(r"\*/(\d+) \* \* \* \*", expression)
        if match:
            return timedelta(minutes=int(match.group(1)))

        # Default: every hour for unrecognized
        return timedelta(hours=1)

    @classmethod
    def next_run_time(cls, expression: str, after: datetime = None) -> datetime:
        now = after or datetime.now(timezone.utc)
        interval = cls.parse_interval(expression)
        if interval:
            return now + interval
        return now + timedelta(hours=1)


class SchedulerEngine:
    """In-memory agent scheduler with async execution loop."""

    def __init__(self):
        self._schedules: Dict[str, Schedule] = {}
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._execute_fn: Optional[Callable[[str, dict], Awaitable]] = None

    def set_executor(self, fn: Callable[[str, dict], Awaitable]):
        """Set the function to call when executing a scheduled agent."""
        self._execute_fn = fn

    async def start(self):
        """Start the scheduler loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler started")

    async def stop(self):
        """Stop the scheduler loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")

    async def _run_loop(self):
        """Main scheduler loop — checks every 10 seconds for due schedules."""
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                for schedule in list(self._schedules.values()):
                    if schedule.status != ScheduleStatus.ACTIVE:
                        continue
                    if (
                        schedule.next_run
                        and datetime.fromisoformat(schedule.next_run) <= now
                    ):
                        await self._execute_schedule(schedule)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
            await asyncio.sleep(10)

    async def _execute_schedule(self, schedule: Schedule):
        """Execute a scheduled agent run."""
        try:
            if self._execute_fn:
                await self._execute_fn(schedule.agent_id, schedule.input_data)
            schedule.run_count += 1
            schedule.last_run = datetime.now(timezone.utc).isoformat()

            # Check max runs
            if schedule.max_runs and schedule.run_count >= schedule.max_runs:
                schedule.status = ScheduleStatus.COMPLETED
                schedule.next_run = None
            else:
                schedule.next_run = CronParser.next_run_time(
                    schedule.cron_expression
                ).isoformat()

            logger.info(f"Schedule {schedule.id} executed (run #{schedule.run_count})")
        except Exception as e:
            schedule.error_count += 1
            schedule.last_error = str(e)
            schedule.next_run = CronParser.next_run_time(
                schedule.cron_expression
            ).isoformat()
            logger.error(f"Schedule {schedule.id} failed: {e}")
            if schedule.error_count >= 5:
                schedule.status = ScheduleStatus.ERROR
                logger.warning(
                    f"Schedule {schedule.id} disabled after 5 consecutive errors"
                )

    # CRUD operations
    def create(
        self,
        agent_id: str,
        name: str,
        cron_expression: str,
        input_data: dict = None,
        max_runs: int = None,
    ) -> Schedule:
        schedule = Schedule(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            name=name,
            cron_expression=cron_expression,
            input_data=input_data or {},
            max_runs=max_runs,
            next_run=CronParser.next_run_time(cron_expression).isoformat(),
        )
        self._schedules[schedule.id] = schedule
        logger.info(f"Schedule created: {schedule.id} for agent {agent_id}")
        return schedule

    def get(self, schedule_id: str) -> Optional[Schedule]:
        return self._schedules.get(schedule_id)

    def list_schedules(self, agent_id: str = None) -> list[Schedule]:
        schedules = list(self._schedules.values())
        if agent_id:
            schedules = [s for s in schedules if s.agent_id == agent_id]
        return sorted(schedules, key=lambda s: s.created_at, reverse=True)

    def update(self, schedule_id: str, **kwargs) -> Optional[Schedule]:
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            return None
        for key, value in kwargs.items():
            if hasattr(schedule, key) and key not in ("id", "created_at"):
                setattr(schedule, key, value)
        if "cron_expression" in kwargs:
            schedule.next_run = CronParser.next_run_time(
                kwargs["cron_expression"]
            ).isoformat()
        return schedule

    def delete(self, schedule_id: str) -> bool:
        return self._schedules.pop(schedule_id, None) is not None

    def pause(self, schedule_id: str) -> bool:
        schedule = self._schedules.get(schedule_id)
        if schedule:
            schedule.status = ScheduleStatus.PAUSED
            return True
        return False

    def resume(self, schedule_id: str) -> bool:
        schedule = self._schedules.get(schedule_id)
        if schedule and schedule.status == ScheduleStatus.PAUSED:
            schedule.status = ScheduleStatus.ACTIVE
            schedule.next_run = CronParser.next_run_time(
                schedule.cron_expression
            ).isoformat()
            return True
        return False

    @property
    def stats(self) -> dict:
        statuses = {}
        for s in self._schedules.values():
            statuses[s.status] = statuses.get(s.status, 0) + 1
        return {"total": len(self._schedules), "by_status": statuses}


scheduler_engine = SchedulerEngine()
