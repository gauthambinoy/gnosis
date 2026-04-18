from pydantic import BaseModel, Field
from typing import Optional, List


class ScheduleCreate(BaseModel):
    agent_id: str
    name: str = Field(min_length=1, max_length=200)
    cron_expression: str = Field(
        min_length=1,
        description="Cron expression or simplified: 'every:5m', 'daily:09:00', 'hourly'",
    )
    input_data: dict = Field(default_factory=dict)
    max_runs: Optional[int] = Field(None, ge=1)


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    input_data: Optional[dict] = None
    max_runs: Optional[int] = None


class ScheduleResponse(BaseModel):
    model_config = {"extra": "allow"}

    id: str
    agent_id: str
    name: str
    cron_expression: str
    status: str = "active"
    input_data: dict = Field(default_factory=dict)
    max_runs: Optional[int] = None
    run_count: int = 0
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    created_at: str = ""
    error_count: int = 0
    last_error: Optional[str] = None


class ScheduleListResponse(BaseModel):
    schedules: List[ScheduleResponse]
    total: int


class DeletedResponse(BaseModel):
    deleted: bool


class PausedResponse(BaseModel):
    paused: bool


class ResumedResponse(BaseModel):
    resumed: bool
