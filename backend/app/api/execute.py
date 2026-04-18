import logging

from fastapi import APIRouter, HTTPException

from app.schemas.execute import ExecuteRequest, ExecutionResponse
from app.core.guardrails import guardrail_engine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/trigger", response_model=ExecutionResponse)
async def trigger_execution(data: ExecuteRequest):
    """Trigger an agent execution."""
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
        logger.warning("Guardrail warning for agent %s: %s", data.agent_id, w.get("description"))

    # Placeholder — orchestrator in Phase 2
    return {
        "execution_id": "exec-placeholder",
        "agent_id": data.agent_id,
        "status": "queued",
    }
