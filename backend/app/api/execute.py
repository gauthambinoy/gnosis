import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.execute import ExecuteRequest, ExecutionResponse
from app.core.guardrails import guardrail_engine
from app.core.auth import get_current_user_id
from app.core.database import get_db, db_available
from app.core.error_handling import ForbiddenError, NotFoundError
from app.models.agent import Agent

# In-memory fallback agent store from agents.py for ownership lookups when DB unavailable.
from app.api.agents import _agents as _agents_memory

logger = logging.getLogger(__name__)

router = APIRouter()


async def _verify_agent_ownership(
    agent_id: str, user_id: str, db: AsyncSession
) -> None:
    """Raise ForbiddenError unless `user_id` owns `agent_id`. Raises NotFoundError if missing."""
    if db_available:
        try:
            agent_uuid = uuid.UUID(agent_id)
            user_uuid = uuid.UUID(user_id)
        except (ValueError, AttributeError):
            raise NotFoundError("Agent not found")
        result = await db.execute(select(Agent).where(Agent.id == agent_uuid))
        agent = result.scalars().first()
        if agent is None:
            raise NotFoundError("Agent not found")
        if agent.owner_id != user_uuid:
            raise ForbiddenError("You do not own this agent")
        return

    # Fallback in-memory check
    agent = _agents_memory.get(agent_id)
    if agent is None:
        raise NotFoundError("Agent not found")
    if agent.get("owner_id") != user_id:
        raise ForbiddenError("You do not own this agent")


@router.post("/trigger", response_model=ExecutionResponse)
async def trigger_execution(
    data: ExecuteRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an agent execution."""
    await _verify_agent_ownership(data.agent_id, user_id, db)

    # Guardrail pre-execution check
    guardrail_result = await guardrail_engine.check(
        agent_id=data.agent_id,
        action={"type": "execute", "data": data.model_dump()},
        context={},
    )
    if not guardrail_result.get("passed", True):
        violations = guardrail_result.get("violations", [])
        blocking = [v for v in violations if v.get("severity") == "block"]
        if blocking:
            raise HTTPException(
                status_code=403,
                detail=f"Guardrail violation: {blocking[0].get('description', 'Blocked by safety check')}",
            )
    for w in guardrail_result.get("warnings", []):
        logger.warning(
            "Guardrail warning for agent %s: %s", data.agent_id, w.get("description")
        )

    # Placeholder — orchestrator in Phase 2
    return {
        "execution_id": "exec-placeholder",
        "agent_id": data.agent_id,
        "status": "queued",
    }
