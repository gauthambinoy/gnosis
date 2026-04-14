"""Manages WebSocket connections for live execution streaming."""

from fastapi import WebSocket
from typing import Dict, Set
import json
from datetime import datetime, timezone


class ExecutionStreamManager:
    """Manages WebSocket connections for live execution streaming."""

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}  # agent_id -> connections
        self._global_connections: Set[WebSocket] = set()  # dashboard-wide listeners

    async def connect(self, websocket: WebSocket, agent_id: str = None):
        await websocket.accept()
        if agent_id:
            self._connections.setdefault(agent_id, set()).add(websocket)
        else:
            self._global_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket, agent_id: str = None):
        if agent_id:
            self._connections.get(agent_id, set()).discard(websocket)
        self._global_connections.discard(websocket)

    async def broadcast_phase(self, agent_id: str, phase: str, data: dict):
        """Broadcast execution phase to all listeners."""
        message = json.dumps({
            "type": "execution_phase",
            "agent_id": agent_id,
            "phase": phase,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Agent-specific listeners
        for ws in list(self._connections.get(agent_id, set())):
            try:
                await ws.send_text(message)
            except Exception:
                self._connections[agent_id].discard(ws)
        # Global dashboard listeners
        for ws in list(self._global_connections):
            try:
                await ws.send_text(message)
            except Exception:
                self._global_connections.discard(ws)

    async def broadcast_metric(self, metric_type: str, data: dict):
        """Broadcast real-time metrics to dashboard."""
        message = json.dumps({
            "type": "metric",
            "metric_type": metric_type,
            "data": data,
        })
        for ws in list(self._global_connections):
            try:
                await ws.send_text(message)
            except Exception:
                self._global_connections.discard(ws)

    @property
    def stats(self):
        return {
            "agent_streams": {k: len(v) for k, v in self._connections.items()},
            "global_listeners": len(self._global_connections),
        }


execution_stream = ExecutionStreamManager()
