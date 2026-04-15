from fastapi import APIRouter, HTTPException, Depends
from app.core.webhook_dispatcher import webhook_dispatcher, ALL_EVENTS
from app.core.auth import get_current_user_id
from dataclasses import asdict
from typing import List, Optional

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

@router.get("/events")
async def list_available_events(user_id: str = Depends(get_current_user_id)):
    return {"events": ALL_EVENTS}

@router.post("")
async def register_webhook(data: dict, user_id: str = Depends(get_current_user_id)):
    endpoint = webhook_dispatcher.register(
        url=data["url"], events=data.get("events", ["*"]),
        secret=data.get("secret", ""), workspace_id=data.get("workspace_id", ""), created_by=user_id,
    )
    return asdict(endpoint)

@router.get("")
async def list_webhooks(workspace_id: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    return {"endpoints": webhook_dispatcher.list_endpoints(workspace_id=workspace_id)}

@router.delete("/{endpoint_id}")
async def delete_webhook(endpoint_id: str, user_id: str = Depends(get_current_user_id)):
    if not webhook_dispatcher.unregister(endpoint_id):
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"deleted": True}

@router.get("/{endpoint_id}/deliveries")
async def get_deliveries(endpoint_id: str, limit: int = 50, user_id: str = Depends(get_current_user_id)):
    return {"deliveries": webhook_dispatcher.get_deliveries(endpoint_id=endpoint_id, limit=limit)}

@router.get("/stats")
async def webhook_stats(user_id: str = Depends(get_current_user_id)):
    return webhook_dispatcher.stats
