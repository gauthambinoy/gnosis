"""WebSocket route handlers for live execution streaming."""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.ws.execution_stream import execution_stream

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_WS_MESSAGE_SIZE = 64 * 1024  # 64KB


@router.websocket("/ws/dashboard")
async def dashboard_stream(websocket: WebSocket):
    await execution_stream.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if len(data) > MAX_WS_MESSAGE_SIZE:
                await websocket.close(code=1009, reason="Message too large")
                return
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning("Dashboard WebSocket error, cleaning up")
    finally:
        await execution_stream.disconnect(websocket)


@router.websocket("/ws/agent/{agent_id}")
async def agent_stream(websocket: WebSocket, agent_id: str):
    await execution_stream.connect(websocket, agent_id)
    try:
        while True:
            data = await websocket.receive_text()
            if len(data) > MAX_WS_MESSAGE_SIZE:
                await websocket.close(code=1009, reason="Message too large")
                return
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning("Agent %s WebSocket error, cleaning up", agent_id)
    finally:
        await execution_stream.disconnect(websocket, agent_id)
