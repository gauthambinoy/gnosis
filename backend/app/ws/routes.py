"""WebSocket route handlers for live execution streaming."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.ws.execution_stream import execution_stream

router = APIRouter()


@router.websocket("/ws/dashboard")
async def dashboard_stream(websocket: WebSocket):
    await execution_stream.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong keepalive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await execution_stream.disconnect(websocket)


@router.websocket("/ws/agent/{agent_id}")
async def agent_stream(websocket: WebSocket, agent_id: str):
    await execution_stream.connect(websocket, agent_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await execution_stream.disconnect(websocket, agent_id)
