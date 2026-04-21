from fastapi import APIRouter, Depends
from app.core.event_bus import event_bus
from app.core.auth import get_current_user_id
from app.ws.manager import ws_manager

router = APIRouter()


@router.get("/recent")
async def get_recent_events(limit: int = 20, user_id: str = Depends(get_current_user_id)):
    return {"events": event_bus.recent_events(limit)}


@router.get("/connections")
async def get_connections(user_id: str = Depends(get_current_user_id)):
    return {
        "total": ws_manager.total_connections,
        "dashboard": ws_manager.dashboard_count,
    }
