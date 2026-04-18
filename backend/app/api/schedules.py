from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.core.scheduler import scheduler_engine
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/schedules", tags=["schedules"])


class CreateScheduleRequest(BaseModel):
    agent_id: str
    name: str = Field(min_length=1, max_length=200)
    cron_expression: str = Field(
        min_length=1,
        description="Cron expression or simplified: 'every:5m', 'daily:09:00', 'hourly'",
    )
    input_data: dict = Field(default_factory=dict)
    max_runs: Optional[int] = Field(None, ge=1)


class UpdateScheduleRequest(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    input_data: Optional[dict] = None
    max_runs: Optional[int] = None


@router.post("")
async def create_schedule(req: CreateScheduleRequest):
    schedule = scheduler_engine.create(
        agent_id=req.agent_id,
        name=req.name,
        cron_expression=req.cron_expression,
        input_data=req.input_data,
        max_runs=req.max_runs,
    )
    return asdict(schedule)


@router.get("/stats/overview")
async def schedule_stats():
    return scheduler_engine.stats


@router.get("")
async def list_schedules(agent_id: str = None):
    schedules = scheduler_engine.list_schedules(agent_id=agent_id)
    return {"schedules": [asdict(s) for s in schedules], "total": len(schedules)}


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: str):
    schedule = scheduler_engine.get(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return asdict(schedule)


@router.patch("/{schedule_id}")
async def update_schedule(schedule_id: str, req: UpdateScheduleRequest):
    updates = req.model_dump(exclude_none=True)
    schedule = scheduler_engine.update(schedule_id, **updates)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return asdict(schedule)


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str):
    if not scheduler_engine.delete(schedule_id):
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"deleted": True}


@router.post("/{schedule_id}/pause")
async def pause_schedule(schedule_id: str):
    if not scheduler_engine.pause(schedule_id):
        raise HTTPException(
            status_code=404, detail="Schedule not found or already paused"
        )
    return {"paused": True}


@router.post("/{schedule_id}/resume")
async def resume_schedule(schedule_id: str):
    if not scheduler_engine.resume(schedule_id):
        raise HTTPException(status_code=404, detail="Schedule not found or not paused")
    return {"resumed": True}
