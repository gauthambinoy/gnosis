from pydantic import BaseModel, Field
from typing import Optional


class ExecuteRequest(BaseModel):
    agent_id: str
    trigger_type: str = Field(
        default="manual", pattern="^(manual|webhook|schedule|pipeline)$"
    )
    trigger_data: dict = Field(default_factory=dict)


class ExecutionResponse(BaseModel):
    execution_id: str
    agent_id: str
    status: str


class ExecutionStatus(BaseModel):
    execution_id: str
    agent_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
