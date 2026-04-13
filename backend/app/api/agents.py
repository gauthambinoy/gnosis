from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

router = APIRouter()


class AgentCreate(BaseModel):
    name: str
    description: str
    personality: Optional[str] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str
    personality: Optional[str] = None
    status: str = "idle"
    trust_level: int = 0
    total_actions: int = 0
    accuracy: float = 0.0
    time_saved_minutes: float = 0.0
    created_at: datetime


class AgentList(BaseModel):
    agents: list[AgentResponse]
    total: int
    page: int
    per_page: int


# In-memory store (replaced by DB in p1-db-models)
_agents: dict[str, dict] = {}


@router.post("", response_model=AgentResponse)
async def create_agent(data: AgentCreate):
    agent_id = str(uuid.uuid4())
    agent = {
        "id": agent_id,
        "name": data.name,
        "description": data.description,
        "personality": data.personality,
        "status": "idle",
        "trust_level": 0,
        "total_actions": 0,
        "accuracy": 0.0,
        "time_saved_minutes": 0.0,
        "created_at": datetime.utcnow(),
    }
    _agents[agent_id] = agent
    return AgentResponse(**agent)


@router.get("", response_model=AgentList)
async def list_agents(page: int = 1, per_page: int = 20, status: Optional[str] = None):
    agents = list(_agents.values())
    if status:
        agents = [a for a in agents if a["status"] == status]
    total = len(agents)
    start = (page - 1) * per_page
    end = start + per_page
    return AgentList(
        agents=[AgentResponse(**a) for a in agents[start:end]],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse(**_agents[agent_id])


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, data: AgentCreate):
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    _agents[agent_id].update(
        name=data.name,
        description=data.description,
        personality=data.personality,
    )
    return AgentResponse(**_agents[agent_id])


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    del _agents[agent_id]
    return {"status": "deleted", "id": agent_id}
