from pydantic import BaseModel, Field
from typing import Optional, List, Any


class StepInput(BaseModel):
    agent_id: str
    name: str = "Untitled Step"
    transform_input: Optional[str] = None
    condition: Optional[str] = None
    timeout_seconds: int = Field(default=300, ge=1)
    max_retries: int = Field(default=1, ge=0)


class PipelineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    steps: List[StepInput] = Field(default_factory=list)


class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class AddStepRequest(BaseModel):
    agent_id: str
    name: str = "New Step"
    transform_input: Optional[str] = None
    condition: Optional[str] = None


class ExecutePipelineRequest(BaseModel):
    input_data: dict = Field(default_factory=dict)


class PipelineStepResponse(BaseModel):
    model_config = {"extra": "allow"}

    id: str
    agent_id: str
    name: str
    order: int
    transform_input: Optional[str] = None
    condition: Optional[str] = None
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 1


class PipelineResponse(BaseModel):
    model_config = {"extra": "allow"}

    id: str
    name: str
    description: str = ""
    steps: List[PipelineStepResponse] = Field(default_factory=list)
    status: str = "draft"
    created_at: str = ""
    updated_at: str = ""
    created_by: Optional[str] = None


class PipelineListResponse(BaseModel):
    pipelines: List[PipelineResponse]
    total: int


class StepResultResponse(BaseModel):
    model_config = {"extra": "allow"}

    step_id: str
    status: Any  # StepStatus enum serialized
    output: dict = Field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class PipelineRunResponse(BaseModel):
    model_config = {"extra": "allow"}

    id: str
    pipeline_id: str
    status: Any
    initial_input: dict = Field(default_factory=dict)
    step_results: List[StepResultResponse] = Field(default_factory=list)
    current_step: int = 0
    started_at: str = ""
    completed_at: Optional[str] = None
    total_duration_ms: float = 0


class PipelineRunListResponse(BaseModel):
    runs: List[PipelineRunResponse]
    total: int


class DeletedResponse(BaseModel):
    deleted: bool
