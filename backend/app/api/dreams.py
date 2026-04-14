from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.dream_engine import dream_engine

router = APIRouter(prefix="/api/v1/dreams", tags=["dreams"])


class StartDreamRequest(BaseModel):
    max_scenarios: int = 5
    agent_data: Optional[dict] = None


class EvolutionAction(BaseModel):
    evolution_id: str


class PerformanceData(BaseModel):
    input: str = ""
    output: str = ""
    error: str = ""
    duration_ms: float = 0
    tokens_used: int = 0
    user_rating: float = 0


@router.post("/{agent_id}/start")
async def start_dream(agent_id: str, body: StartDreamRequest = StartDreamRequest()):
    """Put an agent to sleep — it will dream and learn."""
    result = await dream_engine.start_dream(
        agent_id=agent_id,
        agent_data=body.agent_data,
        max_scenarios=body.max_scenarios,
    )
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.get("/{agent_id}/sessions")
async def list_dream_sessions(agent_id: str):
    """List all dream sessions for an agent."""
    sessions = dream_engine.get_agent_dreams(agent_id)
    return {"agent_id": agent_id, "sessions": sessions, "total": len(sessions)}


@router.get("/session/{session_id}")
async def get_dream_session(session_id: str):
    """Get details of a specific dream session."""
    session = dream_engine.get_dream_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Dream session not found")
    return session


@router.get("/{agent_id}/evolutions")
async def list_evolutions(agent_id: str):
    """List all prompt evolutions for an agent."""
    evolutions = dream_engine.get_agent_evolutions(agent_id)
    return {"agent_id": agent_id, "evolutions": evolutions, "total": len(evolutions)}


@router.post("/{agent_id}/evolve/accept")
async def accept_evolution(agent_id: str, body: EvolutionAction):
    """Accept a proposed prompt evolution."""
    result = dream_engine.accept_evolution(agent_id, body.evolution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Evolution not found")
    return result


@router.post("/{agent_id}/evolve/reject")
async def reject_evolution(agent_id: str, body: EvolutionAction):
    """Reject a proposed prompt evolution."""
    success = dream_engine.reject_evolution(agent_id, body.evolution_id)
    if not success:
        raise HTTPException(status_code=404, detail="Evolution not found")
    return {"rejected": True}


@router.post("/{agent_id}/performance")
async def record_performance(agent_id: str, body: PerformanceData):
    """Record execution performance data for dream learning."""
    dream_engine.record_performance(agent_id, body.model_dump())
    return {"recorded": True}


@router.get("/{agent_id}/status")
async def dream_status(agent_id: str):
    """Check if an agent is currently dreaming."""
    return {
        "agent_id": agent_id,
        "is_dreaming": dream_engine.is_dreaming(agent_id),
    }


@router.get("/stats/overview")
async def dream_stats():
    """Get overall dream engine statistics."""
    return dream_engine.get_stats()
