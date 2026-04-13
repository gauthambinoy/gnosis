from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from app.ws.manager import ws_manager

router = APIRouter()


@router.websocket("/ws/minds-eye/{agent_id}")
async def minds_eye_ws(websocket: WebSocket, agent_id: str):
    """WebSocket for live agent consciousness stream."""
    await ws_manager.connect_agent_watcher(websocket, agent_id)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "watchers": ws_manager.agent_watcher_count(agent_id),
                }))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
