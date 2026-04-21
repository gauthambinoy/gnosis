"""
Real-World Connectors API — endpoints for real-world data and triggers.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Any

from app.core.auth import get_current_user_id
from app.core.realworld_engine import realworld_engine
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/realworld", tags=["realworld"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateTriggerRequest(BaseModel):
    user_id: str = "default"
    source: str
    params: dict[str, str] = Field(default_factory=dict)
    field_path: str
    condition: str
    threshold: Any
    action_description: str = ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/sources")
async def list_sources(user_id: str = Depends(get_current_user_id)):
    """List available real-world data sources."""
    sources = realworld_engine.list_sources()
    return {"sources": sources, "count": len(sources)}


@router.get("/fetch/{source}")
async def fetch_source(
    source: str,
    params: str = Query("", description="Comma-separated key=value pairs"),
    user_id: str = Depends(get_current_user_id),
):
    """Fetch current data from a real-world source."""
    parsed: dict[str, str] = {}
    if params:
        for pair in params.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                parsed[k.strip()] = v.strip()
    result = await realworld_engine.fetch_source(source, parsed)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/triggers")
async def create_trigger(
    body: CreateTriggerRequest, user_id: str = Depends(get_current_user_id)
):
    """Create a real-world trigger."""
    try:
        trigger = await realworld_engine.create_trigger(
            user_id=user_id,
            source=body.source,
            field_path=body.field_path,
            condition=body.condition,
            threshold=body.threshold,
            action_description=body.action_description,
            params=body.params,
        )
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)
    return {"created": True, "trigger": realworld_engine._trigger_to_dict(trigger)}


@router.get("/triggers")
async def list_triggers(user_id: str = Depends(get_current_user_id)):
    """List all triggers for a user."""
    triggers = realworld_engine.list_triggers(user_id)
    return {"triggers": triggers, "count": len(triggers)}


@router.delete("/triggers/{trigger_id}")
async def delete_trigger(trigger_id: str, user_id: str = Depends(get_current_user_id)):
    """Delete a trigger."""
    deleted = await realworld_engine.delete_trigger(trigger_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return {"deleted": True, "trigger_id": trigger_id}


@router.post("/triggers/check")
async def check_triggers(user_id: str = Depends(get_current_user_id)):
    """Check all triggers now and return any that fired."""
    fired = await realworld_engine.check_triggers()
    return {"fired": fired, "count": len(fired)}


@router.get("/history")
async def event_history(limit: int = Query(50, ge=1, le=500), user_id: str = Depends(get_current_user_id)):
    """Event history of fired triggers."""
    history = realworld_engine.get_history(limit)
    return {"history": history, "count": len(history)}


@router.get("/stats")
async def realworld_stats(user_id: str = Depends(get_current_user_id)):
    """Real-world engine statistics."""
    return realworld_engine.get_stats()
