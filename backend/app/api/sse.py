"""SSE endpoints for real-time updates."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.core.sse_broadcaster import sse_broadcaster
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/api/v1/sse", tags=["real-time"])

@router.get("/stream/{channel}")
async def sse_stream(channel: str, user_id: str = Depends(get_current_user_id)):
    """Subscribe to real-time SSE events for a channel."""
    return StreamingResponse(
        sse_broadcaster.event_stream(channel),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )

@router.get("/stats")
async def sse_stats(user_id: str = Depends(get_current_user_id)):
    return sse_broadcaster.stats

@router.post("/test/{channel}")
async def test_broadcast(channel: str, data: dict, user_id: str = Depends(get_current_user_id)):
    """Test: broadcast a message to a channel."""
    await sse_broadcaster.publish(channel, "test", data)
    return {"status": "sent", "channel": channel}
