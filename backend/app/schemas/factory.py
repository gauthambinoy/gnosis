from pydantic import BaseModel, Field
from typing import Optional


class FactoryRequest(BaseModel):
    """Natural language description of what to automate."""

    description: str = Field(
        min_length=5,
        max_length=2000,
        description="Natural language description of what you want to automate",
    )


class AgentBlueprintSchema(BaseModel):
    model_config = {"extra": "allow"}

    name: str = ""
    description: str = ""
    system_prompt: str = ""
    model: str = "fast"
    tools_needed: list[str] = Field(default_factory=list)
    input_schema: dict = Field(default_factory=dict)


class FactoryPlanResponse(BaseModel):
    """A deployment plan returned by the factory."""

    model_config = {"extra": "allow"}

    id: str
    status: str
    user_input: str = ""
    analysis: dict = Field(default_factory=dict)
    agents: list[dict] = Field(default_factory=list)
    pipeline: Optional[dict] = None
    schedule: Optional[dict] = None
    integrations: list[dict] = Field(default_factory=list)
    estimated_cost_per_run: str = ""
    created_at: float = 0
    deployed_at: float = 0
    created_agent_ids: list[str] = Field(default_factory=list)
    created_pipeline_id: str = ""
    created_schedule_id: str = ""


class FactoryDeployResponse(BaseModel):
    """Result of deploying a plan."""

    model_config = {"extra": "allow"}

    status: str
    plan_id: str = ""
    created_agent_ids: list[str] = Field(default_factory=list)
    created_pipeline_id: str = ""
    created_schedule_id: str = ""


class FactoryStatsResponse(BaseModel):
    model_config = {"extra": "allow"}

    total_plans: int = 0
    deployed: int = 0
    draft: int = 0
    total_agents_created: int = 0


class DeleteResponse(BaseModel):
    status: str


class IntentInfo(BaseModel):
    model_config = {"extra": "allow"}

    description: str
    keywords: list[str] = Field(default_factory=list)
    requires: list[str] = Field(default_factory=list)
    default_schedule: Optional[str] = None
