from fastapi import APIRouter, Body
from pydantic import BaseModel

from app.schemas.execute import ExecuteRequest, ExecutionResponse

router = APIRouter()


@router.post("/trigger", response_model=ExecutionResponse)
async def trigger_execution(data: ExecuteRequest):
    """Trigger an agent execution."""
    # Placeholder — orchestrator in Phase 2
    return {
        "execution_id": "exec-placeholder",
        "agent_id": data.agent_id,
        "status": "queued",
    }
