from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
from app.core.event_bus import event_bus, Events

router = APIRouter()


class AgentCreate(BaseModel):
    name: str
    description: str
    personality: Optional[str] = "professional"
    avatar_emoji: Optional[str] = "◎"
    trigger_type: Optional[str] = "manual"
    trigger_config: Optional[dict] = {}
    integrations: Optional[list[str]] = []
    guardrails: Optional[list[str]] = []


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    personality: Optional[str] = None
    avatar_emoji: Optional[str] = None
    status: Optional[str] = None


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
    page: int
    per_page: int


# In-memory store (replaced by DB session in future)
_agents: dict[str, dict] = {}


def _make_agent(data: AgentCreate) -> dict:
    now = datetime.utcnow().isoformat()
    return {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "description": data.description,
        "personality": data.personality or "professional",
        "avatar_emoji": data.avatar_emoji or "◎",
        "status": "idle",
        "trigger_type": data.trigger_type or "manual",
        "trigger_config": data.trigger_config or {},
        "trust_level": 0,
        "total_executions": 0,
        "successful_executions": 0,
        "failed_executions": 0,
        "total_corrections": 0,
        "accuracy": 0.0,
        "avg_latency_ms": 0.0,
        "total_tokens_used": 0,
        "total_cost_usd": 0.0,
        "time_saved_minutes": 0.0,
        "memory_count": 0,
        "integrations": data.integrations or [],
        "guardrails": data.guardrails or [],
        "created_at": now,
        "updated_at": now,
    }


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(data: AgentCreate):
    agent = _make_agent(data)
    _agents[agent["id"]] = agent
    await event_bus.emit(Events.AGENT_CREATED, {"agent_id": agent["id"], "name": agent["name"]})
    return AgentResponse(**agent)


@router.get("", response_model=AgentListResponse)
async def list_agents(page: int = 1, per_page: int = 20, status: Optional[str] = None):
    agents = list(_agents.values())
    if status:
        agents = [a for a in agents if a["status"] == status]
    total = len(agents)
    start = (page - 1) * per_page
    return AgentListResponse(
        agents=[AgentResponse(**a) for a in agents[start:start + per_page]],
        total=total, page=page, per_page=per_page,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse(**_agents[agent_id])


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, data: AgentUpdate):
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    updates = data.model_dump(exclude_none=True)
    _agents[agent_id].update(updates)
    _agents[agent_id]["updated_at"] = datetime.utcnow().isoformat()
    await event_bus.emit(Events.AGENT_UPDATED, {"agent_id": agent_id, **updates})
    return AgentResponse(**_agents[agent_id])


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    name = _agents[agent_id]["name"]
    del _agents[agent_id]
    await event_bus.emit(Events.AGENT_DELETED, {"agent_id": agent_id, "name": name})
    return {"status": "deleted", "id": agent_id}


@router.post("/{agent_id}/execute")
async def trigger_execution(agent_id: str, trigger_data: dict = {}):
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    execution_id = str(uuid.uuid4())
    _agents[agent_id]["status"] = "active"
    _agents[agent_id]["total_executions"] += 1
    await event_bus.emit(Events.EXECUTION_STARTED, {"execution_id": execution_id, "agent_id": agent_id})
    # Simulate completion
    _agents[agent_id]["successful_executions"] += 1
    _agents[agent_id]["status"] = "idle"
    total = _agents[agent_id]["total_executions"]
    success = _agents[agent_id]["successful_executions"]
    _agents[agent_id]["accuracy"] = success / total if total > 0 else 0.0
    _agents[agent_id]["time_saved_minutes"] += 2.5
    _agents[agent_id]["updated_at"] = datetime.utcnow().isoformat()
    await event_bus.emit(Events.EXECUTION_COMPLETED, {"execution_id": execution_id, "agent_id": agent_id, "status": "completed"})
    return {"execution_id": execution_id, "agent_id": agent_id, "status": "completed"}


@router.post("/{agent_id}/correct")
async def correct_agent(agent_id: str, original: str = "", correction: str = "", context: dict = {}):
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    _agents[agent_id]["total_corrections"] += 1
    _agents[agent_id]["updated_at"] = datetime.utcnow().isoformat()
    await event_bus.emit(Events.CORRECTION_RECEIVED, {"agent_id": agent_id, "original": original, "correction": correction})
    return {"status": "correction_stored", "agent_id": agent_id}
