"""Inbound webhooks API."""

from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user_id
from app.core.inbound_webhooks import inbound_webhook_engine
from dataclasses import asdict

router = APIRouter()


@router.post("")
async def register_webhook(body: dict, user_id: str = Depends(get_current_user_id)):
    name = body.get("name")
    agent_id = body.get("agent_id")
    if not name or not agent_id:
        raise HTTPException(status_code=400, detail="name and agent_id are required")
    hook = inbound_webhook_engine.register_hook(name, agent_id)
    return asdict(hook)


@router.get("")
async def list_webhooks(
    agent_id: str = None, user_id: str = Depends(get_current_user_id)
):
    hooks = inbound_webhook_engine.list_hooks(agent_id)
    return {"webhooks": [asdict(h) for h in hooks]}


@router.post("/{hook_id}/trigger")
async def trigger_webhook(
    hook_id: str, body: dict = None, user_id: str = Depends(get_current_user_id)
):
    result = inbound_webhook_engine.trigger(hook_id, body or {})
    if not result:
        raise HTTPException(status_code=404, detail="Webhook not found or inactive")
    return result
