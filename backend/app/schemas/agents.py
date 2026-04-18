from pydantic import BaseModel, Field


class CreateAgentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=1000)
    personality: str = Field(
        default="professional", pattern="^(professional|friendly|concise|creative)$"
    )
    avatar_emoji: str = Field(default="🤖", max_length=10)
    trigger_type: str = Field(
        default="manual",
        pattern="^(manual|email_received|schedule_daily|schedule_hourly|webhook|calendar_event)$",
    )
    integrations: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)


class UpdateAgentRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    personality: str | None = None
    avatar_emoji: str | None = None
    integrations: list[str] | None = None
    guardrails: list[str] | None = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str
    personality: str
    avatar_emoji: str
    status: str
    trigger_type: str
    trust_level: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    total_corrections: int
    accuracy: float
    avg_latency_ms: float
    total_tokens_used: int
    total_cost_usd: float
    time_saved_minutes: float
    memory_count: int
    integrations: list[str]
    guardrails: list[str]
    created_at: str
    updated_at: str


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int
    page: int = 1
    per_page: int = 20


class ExecuteResponse(BaseModel):
    execution_id: str
    agent_id: str
    status: str


class CorrectRequest(BaseModel):
    correction: str = Field(..., min_length=1, max_length=2000)


class CorrectResponse(BaseModel):
    status: str
    agent_id: str
