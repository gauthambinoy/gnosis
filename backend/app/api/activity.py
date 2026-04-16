from fastapi import APIRouter, HTTPException, Depends, Query
from app.core.activity_feed import activity_feed
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/activity", tags=["activity"])

@router.get("/{workspace_id}")
async def get_feed(workspace_id: str, limit: int = 50, event_type: Optional[str] = None, after: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    return {"events": activity_feed.get_feed(workspace_id, limit=limit, event_type=event_type, after=after)}

@router.get("/{workspace_id}/mentions")
async def get_mentions(workspace_id: str, unread_only: bool = True, user_id: str = Depends(get_current_user_id)):
    return {"mentions": activity_feed.get_mentions(workspace_id, user_id, unread_only=unread_only)}

@router.post("/events/{event_id}/read")
async def mark_read(event_id: str, user_id: str = Depends(get_current_user_id)):
    if not activity_feed.mark_read(event_id, user_id):
        raise HTTPException(status_code=404, detail="Event not found")
    return {"status": "read"}

@router.get("/{workspace_id}/stats")
async def feed_stats(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    return activity_feed.stats(workspace_id)
