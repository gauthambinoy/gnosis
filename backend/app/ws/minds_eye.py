from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

router = APIRouter()

# Per-agent execution watchers
_agent_watchers: dict[str, set[WebSocket]] = {}


@router.websocket("/ws/minds-eye/{agent_id}")
async def minds_eye_ws(websocket: WebSocket, agent_id: str):
    """WebSocket for live agent consciousness stream."""
    await websocket.accept()
    if agent_id not in _agent_watchers:
        _agent_watchers[agent_id] = set()
    _agent_watchers[agent_id].add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        _agent_watchers.get(agent_id, set()).discard(websocket)


async def stream_consciousness(agent_id: str, phase: str, content: str, metadata: dict | None = None):
    """Stream a consciousness event to all watchers of an agent."""
    message = json.dumps({
        "type": "consciousness",
        "payload": {
            "agent_id": agent_id,
            "phase": phase,
            "content": content,
            "metadata": metadata or {},
        },
    })
    watchers = _agent_watchers.get(agent_id, set())
    disconnected = set()
    for ws in watchers:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    watchers -= disconnected
