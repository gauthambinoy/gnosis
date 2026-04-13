from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import event_bus, Events
from app.core.database import get_db
from app.models.agent import Agent, AgentStatus
from app.models.memory import Memory, MemoryTier
from app.core.memory_engine import memory_engine

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AgentCreate(BaseModel):
    name: str
    description: str
    personality: Optional[str] = "professional"
    avatar_emoji: Optional[str] = "◎"
    trigger_type: Optional[str] = "manual"
    trigger_config: Optional[dict] = {}
    integrations: Optional[list[str]] = []
    guardrails: Optional[list[str]] = []
    owner_id: Optional[str] = None


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


# ---------------------------------------------------------------------------
# In-memory fallback (demo mode)
# ---------------------------------------------------------------------------
_agents: dict[str, dict] = {}


def _use_db() -> bool:
    from app.core.database import db_available as _flag
    return _flag


def _agent_to_response(agent: Agent) -> AgentResponse:
    """Convert an ORM Agent to the API response schema."""
    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        personality=agent.personality or "professional",
        avatar_emoji=agent.avatar_emoji or "◎",
        status=agent.status.value if isinstance(agent.status, AgentStatus) else str(agent.status),
        trigger_type=agent.trigger_type or "manual",
        trust_level=agent.trust_level or 0,
        total_executions=agent.total_executions or 0,
        successful_executions=agent.successful_executions or 0,
        failed_executions=agent.failed_executions or 0,
        total_corrections=agent.total_corrections or 0,
        accuracy=agent.accuracy or 0.0,
        avg_latency_ms=agent.avg_latency_ms or 0.0,
        total_tokens_used=agent.total_tokens_used or 0,
        total_cost_usd=agent.total_cost_usd or 0.0,
        time_saved_minutes=agent.time_saved_minutes or 0.0,
        memory_count=agent.memory_count or 0,
        integrations=agent.integrations or [],
        guardrails=agent.guardrails or [],
        created_at=agent.created_at.isoformat() if agent.created_at else datetime.utcnow().isoformat(),
        updated_at=agent.updated_at.isoformat() if agent.updated_at else datetime.utcnow().isoformat(),
    )


def _make_agent_dict(data: AgentCreate) -> dict:
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


# A default owner UUID used in demo mode / when no owner_id is supplied
_DEFAULT_OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(data: AgentCreate, db: AsyncSession = Depends(get_db)):
    if _use_db():
        agent = Agent(
            id=uuid.uuid4(),
            owner_id=uuid.UUID(data.owner_id) if data.owner_id else _DEFAULT_OWNER_ID,
            name=data.name,
            description=data.description,
            personality=data.personality or "professional",
            avatar_emoji=data.avatar_emoji or "◎",
            trigger_type=data.trigger_type or "manual",
            trigger_config=data.trigger_config or {},
            integrations=data.integrations or [],
            guardrails=data.guardrails or [],
            status=AgentStatus.idle,
        )
        db.add(agent)
        await db.flush()
        await event_bus.emit(Events.AGENT_CREATED, {"agent_id": str(agent.id), "name": agent.name})
        return _agent_to_response(agent)

    # Fallback
    agent = _make_agent_dict(data)
    _agents[agent["id"]] = agent
    await event_bus.emit(Events.AGENT_CREATED, {"agent_id": agent["id"], "name": agent["name"]})
    return AgentResponse(**agent)


@router.get("", response_model=AgentListResponse)
async def list_agents(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    if _use_db():
        query = select(Agent)
        if status:
            query = query.where(Agent.status == status)
        count_q = select(sa_func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar() or 0
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await db.execute(query)
        agents = result.scalars().all()
        return AgentListResponse(
            agents=[_agent_to_response(a) for a in agents],
            total=total, page=page, per_page=per_page,
        )

    # Fallback
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
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    if _use_db():
        result = await db.execute(select(Agent).where(Agent.id == uuid.UUID(agent_id)))
        agent = result.scalars().first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return _agent_to_response(agent)

    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse(**_agents[agent_id])


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, data: AgentUpdate, db: AsyncSession = Depends(get_db)):
    if _use_db():
        result = await db.execute(select(Agent).where(Agent.id == uuid.UUID(agent_id)))
        agent = result.scalars().first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        updates = data.model_dump(exclude_none=True)
        for key, value in updates.items():
            if key == "status":
                value = AgentStatus(value)
            setattr(agent, key, value)
        await db.flush()
        await event_bus.emit(Events.AGENT_UPDATED, {"agent_id": agent_id, **updates})
        return _agent_to_response(agent)

    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    updates = data.model_dump(exclude_none=True)
    _agents[agent_id].update(updates)
    _agents[agent_id]["updated_at"] = datetime.utcnow().isoformat()
    await event_bus.emit(Events.AGENT_UPDATED, {"agent_id": agent_id, **updates})
    return AgentResponse(**_agents[agent_id])


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    if _use_db():
        result = await db.execute(select(Agent).where(Agent.id == uuid.UUID(agent_id)))
        agent = result.scalars().first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        name = agent.name
        await db.delete(agent)
        await db.flush()
        await event_bus.emit(Events.AGENT_DELETED, {"agent_id": agent_id, "name": name})
        return {"status": "deleted", "id": agent_id}

    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    name = _agents[agent_id]["name"]
    del _agents[agent_id]
    await event_bus.emit(Events.AGENT_DELETED, {"agent_id": agent_id, "name": name})
    return {"status": "deleted", "id": agent_id}


@router.post("/{agent_id}/execute")
async def trigger_execution(agent_id: str, trigger_data: dict = {}, db: AsyncSession = Depends(get_db)):
    if _use_db():
        result = await db.execute(select(Agent).where(Agent.id == uuid.UUID(agent_id)))
        agent = result.scalars().first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        execution_id = str(uuid.uuid4())
        agent.status = AgentStatus.active
        agent.total_executions = (agent.total_executions or 0) + 1
        await event_bus.emit(Events.EXECUTION_STARTED, {"execution_id": execution_id, "agent_id": agent_id})
        # Simulate completion
        agent.successful_executions = (agent.successful_executions or 0) + 1
        agent.status = AgentStatus.idle
        total = agent.total_executions
        success = agent.successful_executions
        agent.accuracy = success / total if total > 0 else 0.0
        agent.time_saved_minutes = (agent.time_saved_minutes or 0.0) + 2.5
        await db.flush()
        await event_bus.emit(Events.EXECUTION_COMPLETED, {"execution_id": execution_id, "agent_id": agent_id, "status": "completed"})
        return {"execution_id": execution_id, "agent_id": agent_id, "status": "completed"}

    # Fallback
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    execution_id = str(uuid.uuid4())
    _agents[agent_id]["status"] = "active"
    _agents[agent_id]["total_executions"] += 1
    await event_bus.emit(Events.EXECUTION_STARTED, {"execution_id": execution_id, "agent_id": agent_id})
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
async def correct_agent(agent_id: str, original: str = "", correction: str = "", context: dict = {}, db: AsyncSession = Depends(get_db)):
    if _use_db():
        result = await db.execute(select(Agent).where(Agent.id == uuid.UUID(agent_id)))
        agent = result.scalars().first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        agent.total_corrections = (agent.total_corrections or 0) + 1
        # Dual-write: store correction memory in DB
        mem = Memory(
            id=uuid.uuid4(),
            agent_id=agent.id,
            tier=MemoryTier.correction,
            content=f"CORRECTION: do NOT '{original}', instead '{correction}'",
            extra_metadata={"original": original, "correction": correction, "context": context},
        )
        db.add(mem)
        agent.memory_count = (agent.memory_count or 0) + 1
        await db.flush()
        # Also store in vector engine
        try:
            await memory_engine.store_correction(agent_id, original, correction, context)
        except Exception:
            pass  # vector store failure is non-fatal
        await event_bus.emit(Events.CORRECTION_RECEIVED, {"agent_id": agent_id, "original": original, "correction": correction})
        return {"status": "correction_stored", "agent_id": agent_id}

    # Fallback
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    _agents[agent_id]["total_corrections"] += 1
    _agents[agent_id]["updated_at"] = datetime.utcnow().isoformat()
    await event_bus.emit(Events.CORRECTION_RECEIVED, {"agent_id": agent_id, "original": original, "correction": correction})
    return {"status": "correction_stored", "agent_id": agent_id}
