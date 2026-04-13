from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

router = APIRouter()

# Connected dashboard clients
_dashboard_clients: set[WebSocket] = set()


@router.websocket("/ws/nerve-center")
async def nerve_center_ws(websocket: WebSocket):
    """WebSocket for live dashboard updates."""
    await websocket.accept()
    _dashboard_clients.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        _dashboard_clients.discard(websocket)


async def broadcast_to_dashboard(event_type: str, payload: dict):
    """Broadcast an event to all connected dashboard clients."""
    message = json.dumps({"type": event_type, "payload": payload})
    disconnected = set()
    for ws in _dashboard_clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    _dashboard_clients -= disconnected
