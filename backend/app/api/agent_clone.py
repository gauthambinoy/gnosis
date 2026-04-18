"""One-click agent cloning with deep copy of config, tools, and personality."""

from fastapi import APIRouter, HTTPException, Depends
from app.core.auth import get_current_user_id
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.clone")
router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.post("/{agent_id}/clone")
async def clone_agent(
    agent_id: str, new_name: str = "", user_id: str = Depends(get_current_user_id)
):
    """Deep-clone an agent with all configuration."""
    try:
        from app.core.marketplace import marketplace_engine
    except ImportError:
        raise HTTPException(status_code=500, detail="Marketplace engine not available")

    source = marketplace_engine.get_agent(agent_id)
    if not source:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Deep clone the agent data
    source_data = (
        source
        if isinstance(source, dict)
        else (source.__dict__.copy() if hasattr(source, "__dict__") else {})
    )

    clone_id = str(uuid.uuid4())
    name = new_name or f"{source_data.get('name', 'Agent')} (Clone)"

    clone_data = {
        **source_data,
        "id": clone_id,
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_executions": 0,
        "cloned_from": agent_id,
    }

    # Remove runtime state
    for key in ["last_execution", "current_task", "_runtime"]:
        clone_data.pop(key, None)

    marketplace_engine._agents[clone_id] = (
        type(source)(**clone_data) if not isinstance(source, dict) else clone_data
    )

    logger.info(f"Agent cloned: {agent_id} -> {clone_id} by {user_id}")
    return {"id": clone_id, "name": name, "cloned_from": agent_id, "status": "created"}
