"""Gnosis Swarm Intelligence API — Agent teams that self-organize."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.core.swarm_engine import swarm_engine

router = APIRouter(prefix="/api/v1/swarm", tags=["swarm"])


# ─── Request Models ───

class RegisterAgentRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=100)
    name: str = Field(default="", max_length=200)
    skills: list[str] = Field(default_factory=list)
    specialization: str = Field(default="general", max_length=100)
    trust_score: float = Field(default=0.5, ge=0, le=1)


class CreateSwarmTaskRequest(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    requester_id: str = Field(default="", max_length=100)
    required_skills: list[str] = Field(default_factory=list)


class SubmitResultRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=100)
    result: dict = Field(default_factory=dict)


# ─── Agent Registry ───

@router.post("/register")
async def register_agent(req: RegisterAgentRequest):
    """Register an agent's capabilities in the swarm."""
    cap = swarm_engine.register_agent(req.agent_id, req.model_dump())
    return {"status": "registered", "agent": cap}


@router.delete("/register/{agent_id}")
async def unregister_agent(agent_id: str):
    """Remove an agent from the swarm registry."""
    removed = swarm_engine.unregister_agent(agent_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Agent not found in registry")
    return {"status": "unregistered", "agent_id": agent_id}


@router.get("/discover")
async def discover_agents(
    skills: Optional[str] = Query(None, description="Comma-separated skills"),
    specialization: Optional[str] = Query(None, description="Specialization filter"),
):
    """Discover agents by skills or specialization."""
    skill_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else None
    agents = swarm_engine.discover_agents(skills=skill_list, specialization=specialization or "")
    return {"agents": agents, "count": len(agents)}


@router.get("/registry")
async def get_registry():
    """Get full agent registry."""
    registry = swarm_engine.get_registry()
    return {"agents": registry, "count": len(registry)}


# ─── Swarm Tasks ───

@router.post("/tasks")
async def create_swarm_task(req: CreateSwarmTaskRequest):
    """Create a swarm task — agents are auto-recruited."""
    task = await swarm_engine.create_swarm_task(req.model_dump())
    return {"status": "created", "task": task}


@router.get("/tasks")
async def list_tasks(status: Optional[str] = Query(None)):
    """List swarm tasks, optionally filtered by status."""
    tasks = swarm_engine.list_tasks(status=status or "")
    return {"tasks": tasks, "count": len(tasks)}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific swarm task."""
    task = swarm_engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks/{task_id}/result")
async def submit_result(task_id: str, req: SubmitResultRequest):
    """Submit a result for a swarm task."""
    result = await swarm_engine.submit_result(task_id, req.agent_id, req.result)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── Messaging ───

@router.get("/inbox/{agent_id}")
async def get_inbox(agent_id: str, limit: int = Query(20, ge=1, le=100)):
    """Get an agent's message inbox."""
    messages = swarm_engine.get_inbox(agent_id, limit=limit)
    return {"messages": messages, "count": len(messages)}


# ─── Stats ───

@router.get("/stats")
async def get_stats():
    """Get swarm intelligence statistics."""
    return swarm_engine.get_stats()
