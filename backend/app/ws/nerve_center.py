from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from app.ws.manager import ws_manager

router = APIRouter()


@router.websocket("/ws/nerve-center")
async def nerve_center_ws(websocket: WebSocket):
    """WebSocket for live dashboard updates."""
    await ws_manager.connect_dashboard(websocket, user_id="anonymous")
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "connections": ws_manager.total_connections}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
