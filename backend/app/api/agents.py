import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timezone
import uuid

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import event_bus, Events
from app.core.database import get_db
from app.core.auth import get_current_user_id
from app.core.version_manager import version_manager
from app.models.agent import Agent, AgentStatus
from app.models.memory import Memory, MemoryTier
from app.core.memory_engine import memory_engine
from app.schemas.agents import (
    CreateAgentRequest, UpdateAgentRequest, AgentResponse,
    AgentListResponse, ExecuteResponse, CorrectRequest, CorrectResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# In-memory fallback (demo mode) — protected by lock for thread safety
# ---------------------------------------------------------------------------
_agents: dict[str, dict] = {}
_agents_lock = asyncio.Lock()


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
        created_at=agent.created_at.isoformat() if agent.created_at else datetime.now(timezone.utc).isoformat(),
        updated_at=agent.updated_at.isoformat() if agent.updated_at else datetime.now(timezone.utc).isoformat(),
    )


def _make_agent_dict(data: CreateAgentRequest, owner_id: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(uuid.uuid4()),
        "owner_id": owner_id,
        "name": data.name,
        "description": data.description,
        "personality": data.personality or "professional",
        "avatar_emoji": data.avatar_emoji or "◎",
        "status": "idle",
        "trigger_type": data.trigger_type or "manual",
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


# ---------------------------------------------------------------------------
# Helper: get agent scoped to the authenticated owner
# ---------------------------------------------------------------------------

async def _get_owned_agent(agent_id: str, user_id: str, db: AsyncSession) -> Agent:
    """Fetch an agent from DB, raising 404 if not found or not owned by user."""
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")
    result = await db.execute(
        select(Agent).where(Agent.id == agent_uuid, Agent.owner_id == uuid.UUID(user_id))
    )
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# ---------------------------------------------------------------------------
# Routes — all require authentication via get_current_user_id
# ---------------------------------------------------------------------------


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    data: CreateAgentRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if _use_db():
        agent = Agent(
            id=uuid.uuid4(),
            owner_id=uuid.UUID(user_id),
            name=data.name,
            description=data.description,
            personality=data.personality or "professional",
            avatar_emoji=data.avatar_emoji or "◎",
            trigger_type=data.trigger_type or "manual",
            trigger_config={},
            integrations=data.integrations or [],
            guardrails=data.guardrails or [],
            status=AgentStatus.idle,
        )
        db.add(agent)
        await db.flush()
        await event_bus.emit(Events.AGENT_CREATED, {"agent_id": str(agent.id), "name": agent.name})
        resp = _agent_to_response(agent)
        version_manager.save_version(str(agent.id), resp.model_dump(), change_summary="Agent created")
        return resp

    # Fallback (demo mode)
    agent = _make_agent_dict(data, owner_id=user_id)
    async with _agents_lock:
        _agents[agent["id"]] = agent
    await event_bus.emit(Events.AGENT_CREATED, {"agent_id": agent["id"], "name": agent["name"]})
    version_manager.save_version(agent["id"], agent, change_summary="Agent created")
    return AgentResponse(**agent)


@router.get("", response_model=AgentListResponse)
async def list_agents(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if _use_db():
        query = select(Agent).where(Agent.owner_id == uuid.UUID(user_id))
        if status:
            try:
                status_enum = AgentStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
            query = query.where(Agent.status == status_enum)
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
    async with _agents_lock:
        agents = [a for a in _agents.values() if a.get("owner_id") == user_id]
    if status:
        agents = [a for a in agents if a["status"] == status]
    total = len(agents)
    start = (page - 1) * per_page
    return AgentListResponse(
        agents=[AgentResponse(**a) for a in agents[start:start + per_page]],
        total=total, page=page, per_page=per_page,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if _use_db():
        agent = await _get_owned_agent(agent_id, user_id, db)
        return _agent_to_response(agent)

    async with _agents_lock:
        a = _agents.get(agent_id)
    if not a or a.get("owner_id") != user_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse(**a)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    data: UpdateAgentRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if _use_db():
        agent = await _get_owned_agent(agent_id, user_id, db)
        updates = data.model_dump(exclude_none=True)
        for key, value in updates.items():
            if key == "status":
                value = AgentStatus(value)
            setattr(agent, key, value)
        await db.flush()
        await event_bus.emit(Events.AGENT_UPDATED, {"agent_id": agent_id, **updates})
        resp = _agent_to_response(agent)
        version_manager.save_version(agent_id, resp.model_dump(), change_summary="Agent updated")
        return resp

    async with _agents_lock:
        a = _agents.get(agent_id)
        if not a or a.get("owner_id") != user_id:
            raise HTTPException(status_code=404, detail="Agent not found")
        updates = data.model_dump(exclude_none=True)
        a.update(updates)
        a["updated_at"] = datetime.now(timezone.utc).isoformat()
    await event_bus.emit(Events.AGENT_UPDATED, {"agent_id": agent_id, **updates})
    version_manager.save_version(agent_id, a, change_summary="Agent updated")
    return AgentResponse(**a)


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if _use_db():
        agent = await _get_owned_agent(agent_id, user_id, db)
        name = agent.name
        await db.delete(agent)
        await db.flush()
        await event_bus.emit(Events.AGENT_DELETED, {"agent_id": agent_id, "name": name})
        return {"status": "deleted", "id": agent_id}

    async with _agents_lock:
        a = _agents.get(agent_id)
        if not a or a.get("owner_id") != user_id:
            raise HTTPException(status_code=404, detail="Agent not found")
        name = a["name"]
        del _agents[agent_id]
    await event_bus.emit(Events.AGENT_DELETED, {"agent_id": agent_id, "name": name})
    return {"status": "deleted", "id": agent_id}


@router.post("/{agent_id}/execute", response_model=ExecuteResponse)
async def trigger_execution(
    agent_id: str,
    trigger_data: Optional[dict] = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if trigger_data is None:
        trigger_data = {}

    if _use_db():
        agent = await _get_owned_agent(agent_id, user_id, db)
        execution_id = str(uuid.uuid4())
        agent.status = AgentStatus.active
        agent.total_executions = (agent.total_executions or 0) + 1
        await event_bus.emit(Events.EXECUTION_STARTED, {"execution_id": execution_id, "agent_id": agent_id})
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
    async with _agents_lock:
        a = _agents.get(agent_id)
        if not a or a.get("owner_id") != user_id:
            raise HTTPException(status_code=404, detail="Agent not found")
        execution_id = str(uuid.uuid4())
        a["status"] = "active"
        a["total_executions"] += 1
    await event_bus.emit(Events.EXECUTION_STARTED, {"execution_id": execution_id, "agent_id": agent_id})
    async with _agents_lock:
        a = _agents.get(agent_id)
        if a:
            a["successful_executions"] += 1
            a["status"] = "idle"
            total = a["total_executions"]
            success = a["successful_executions"]
            a["accuracy"] = success / total if total > 0 else 0.0
            a["time_saved_minutes"] += 2.5
            a["updated_at"] = datetime.now(timezone.utc).isoformat()
    await event_bus.emit(Events.EXECUTION_COMPLETED, {"execution_id": execution_id, "agent_id": agent_id, "status": "completed"})
    return {"execution_id": execution_id, "agent_id": agent_id, "status": "completed"}


@router.post("/{agent_id}/correct", response_model=CorrectResponse)
async def correct_agent(
    agent_id: str,
    data: CorrectRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    original = ""
    correction = data.correction
    context: dict = {}
    if _use_db():
        agent = await _get_owned_agent(agent_id, user_id, db)
        agent.total_corrections = (agent.total_corrections or 0) + 1
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
        try:
            await memory_engine.store_correction(agent_id, original, correction, context)
        except Exception:
            logger.warning("Failed to store correction in vector engine for agent %s", agent_id, exc_info=True)
        await event_bus.emit(Events.CORRECTION_RECEIVED, {"agent_id": agent_id, "original": original, "correction": correction})
        return {"status": "correction_stored", "agent_id": agent_id}

    # Fallback
    async with _agents_lock:
        a = _agents.get(agent_id)
        if not a or a.get("owner_id") != user_id:
            raise HTTPException(status_code=404, detail="Agent not found")
        a["total_corrections"] += 1
        a["updated_at"] = datetime.now(timezone.utc).isoformat()
    await event_bus.emit(Events.CORRECTION_RECEIVED, {"agent_id": agent_id, "original": original, "correction": correction})
    return {"status": "correction_stored", "agent_id": agent_id}
