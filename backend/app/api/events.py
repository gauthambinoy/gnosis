from fastapi import APIRouter
from app.core.event_bus import event_bus
from app.ws.manager import ws_manager

router = APIRouter()


@router.get("/recent")
async def get_recent_events(limit: int = 20):
    return {"events": event_bus.recent_events(limit)}


@router.get("/connections")
async def get_connections():
    return {
        "total": ws_manager.total_connections,
        "dashboard": ws_manager.dashboard_count,
    }
