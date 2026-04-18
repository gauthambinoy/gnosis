"""Centralized WebSocket connection manager for Gnosis."""
import json
from fastapi import WebSocket
from datetime import datetime, timezone


class ConnectionManager:
    """Manages all WebSocket connections across the platform."""

    def __init__(self):
        # Dashboard connections
        self._dashboard: set[WebSocket] = set()
        # Per-agent consciousness watchers: agent_id -> set of websockets
        self._agent_watchers: dict[str, set[WebSocket]] = {}
        # Connection metadata
        self._metadata: dict[WebSocket, dict] = {}

    async def connect_dashboard(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self._dashboard.add(websocket)
        self._metadata[websocket] = {"user_id": user_id, "type": "dashboard", "connected_at": datetime.now(timezone.utc).isoformat()}

    async def connect_agent_watcher(self, websocket: WebSocket, agent_id: str, user_id: str = ""):
        await websocket.accept()
        if agent_id not in self._agent_watchers:
            self._agent_watchers[agent_id] = set()
        self._agent_watchers[agent_id].add(websocket)
        self._metadata[websocket] = {"user_id": user_id, "agent_id": agent_id, "type": "watcher", "connected_at": datetime.now(timezone.utc).isoformat()}

    def disconnect(self, websocket: WebSocket):
        self._dashboard.discard(websocket)
        meta = self._metadata.pop(websocket, {})
        if agent_id := meta.get("agent_id"):
            self._agent_watchers.get(agent_id, set()).discard(websocket)

    async def broadcast_dashboard(self, event_type: str, payload: dict):
        """Send event to all dashboard connections."""
        await self._send_to_set(self._dashboard, event_type, payload)

    async def broadcast_agent(self, agent_id: str, event_type: str, payload: dict):
        """Send event to all watchers of a specific agent."""
        watchers = self._agent_watchers.get(agent_id, set())
        await self._send_to_set(watchers, event_type, payload)

    async def stream_consciousness(self, agent_id: str, phase: str, content: str, metadata: dict | None = None):
        """Stream a consciousness event (Mind's Eye)."""
        await self.broadcast_agent(agent_id, "consciousness", {
            "agent_id": agent_id,
            "phase": phase,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def _send_to_set(self, connections: set[WebSocket], event_type: str, payload: dict):
        message = json.dumps({"type": event_type, "payload": payload, "timestamp": datetime.now(timezone.utc).isoformat()})
        disconnected = set()
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.add(ws)
        for ws in disconnected:
            self.disconnect(ws)

    @property
    def dashboard_count(self) -> int:
        return len(self._dashboard)

    def agent_watcher_count(self, agent_id: str) -> int:
        return len(self._agent_watchers.get(agent_id, set()))

    @property
    def total_connections(self) -> int:
        return len(self._metadata)


# Global singleton
ws_manager = ConnectionManager()
