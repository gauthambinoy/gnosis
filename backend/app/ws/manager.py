"""Centralized WebSocket connection manager for Gnosis."""

import asyncio
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
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def connect_dashboard(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        async with self._get_lock():
            self._dashboard.add(websocket)
            self._metadata[websocket] = {
                "user_id": user_id,
                "type": "dashboard",
                "connected_at": datetime.now(timezone.utc).isoformat(),
            }

    async def connect_agent_watcher(
        self, websocket: WebSocket, agent_id: str, user_id: str = ""
    ):
        await websocket.accept()
        async with self._get_lock():
            if agent_id not in self._agent_watchers:
                self._agent_watchers[agent_id] = set()
            self._agent_watchers[agent_id].add(websocket)
            self._metadata[websocket] = {
                "user_id": user_id,
                "agent_id": agent_id,
                "type": "watcher",
                "connected_at": datetime.now(timezone.utc).isoformat(),
            }

    async def disconnect(self, websocket: WebSocket):
        """Remove a websocket from all tracking structures atomically."""
        async with self._get_lock():
            self._disconnect_locked(websocket)

    def _disconnect_locked(self, websocket: WebSocket):
        self._dashboard.discard(websocket)
        meta = self._metadata.pop(websocket, {})
        agent_id = meta.get("agent_id")
        if agent_id:
            watchers = self._agent_watchers.get(agent_id)
            if watchers is not None:
                watchers.discard(websocket)
                if not watchers:
                    self._agent_watchers.pop(agent_id, None)

    async def broadcast_dashboard(self, event_type: str, payload: dict):
        """Send event to all dashboard connections."""
        async with self._get_lock():
            targets = list(self._dashboard)
        await self._send_to_targets(targets, event_type, payload)

    async def broadcast_agent(self, agent_id: str, event_type: str, payload: dict):
        """Send event to all watchers of a specific agent."""
        async with self._get_lock():
            targets = list(self._agent_watchers.get(agent_id, set()))
        await self._send_to_targets(targets, event_type, payload)

    async def stream_consciousness(
        self, agent_id: str, phase: str, content: str, metadata: dict | None = None
    ):
        """Stream a consciousness event (Mind's Eye)."""
        await self.broadcast_agent(
            agent_id,
            "consciousness",
            {
                "agent_id": agent_id,
                "phase": phase,
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def _send_to_targets(
        self, connections: list[WebSocket], event_type: str, payload: dict
    ):
        message = json.dumps(
            {
                "type": event_type,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        disconnected: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        if disconnected:
            async with self._get_lock():
                for ws in disconnected:
                    self._disconnect_locked(ws)

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
