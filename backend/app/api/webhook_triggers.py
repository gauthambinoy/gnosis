from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from app.core.webhook_triggers import webhook_trigger_manager
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


class CreateTriggerRequest(BaseModel):
    agent_id: str
    name: str = Field(min_length=1, max_length=200)
    allowed_sources: List[str] = Field(default_factory=list)


@router.post("/triggers")
async def create_trigger(req: CreateTriggerRequest):
    trigger = webhook_trigger_manager.create_trigger(
        agent_id=req.agent_id, name=req.name, allowed_sources=req.allowed_sources
    )
    return asdict(trigger)


@router.get("/triggers")
async def list_triggers(agent_id: Optional[str] = None):
    triggers = webhook_trigger_manager.list_triggers(agent_id=agent_id)
    return {"triggers": [asdict(t) for t in triggers], "total": len(triggers)}


@router.get("/triggers/{trigger_id}")
async def get_trigger(trigger_id: str):
    trigger = webhook_trigger_manager.get_trigger(trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return asdict(trigger)


@router.delete("/triggers/{trigger_id}")
async def delete_trigger(trigger_id: str):
    if not webhook_trigger_manager.delete_trigger(trigger_id):
        raise HTTPException(status_code=404, detail="Trigger not found")
    return {"deleted": True}


@router.post("/triggers/{trigger_id}/toggle")
async def toggle_trigger(trigger_id: str):
    result = webhook_trigger_manager.toggle_trigger(trigger_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return {"active": result}


@router.post("/trigger/{trigger_id}")
async def invoke_webhook(trigger_id: str, request: Request):
    """Public endpoint — external services POST here to trigger an agent."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    
    headers = dict(request.headers)
    source_ip = request.client.host if request.client else "unknown"
    
    # Optional signature verification
    signature = headers.get("x-webhook-signature", "")
    if signature and not webhook_trigger_manager.verify_signature(trigger_id, await request.body(), signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        invocation = await webhook_trigger_manager.invoke(trigger_id, payload, headers, source_ip)
        return asdict(invocation)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/triggers/{trigger_id}/invocations")
async def list_invocations(trigger_id: str, limit: int = 50):
    invocations = webhook_trigger_manager.get_invocations(trigger_id=trigger_id, limit=limit)
    return {"invocations": [asdict(i) for i in invocations], "total": len(invocations)}


@router.get("/stats")
async def webhook_stats():
    return webhook_trigger_manager.stats
