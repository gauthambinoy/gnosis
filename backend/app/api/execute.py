from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ExecuteRequest(BaseModel):
    agent_id: str
    trigger_type: str = "manual"
    trigger_data: dict = {}


@router.post("/trigger")
async def trigger_execution(data: ExecuteRequest):
    """Trigger an agent execution."""
    # Placeholder — orchestrator in Phase 2
    return {
        "execution_id": "exec-placeholder",
        "agent_id": data.agent_id,
        "status": "queued",
    }
