"""Gnosis Time-Travel Debugger — Replay agent executions step-by-step."""
import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.time_travel")

@dataclass
class DebugFrame:
    index: int
    timestamp: str
    phase: str  # "input", "memory_retrieval", "cortex_layer_1", ..., "output"
    label: str
    data: dict = field(default_factory=dict)
    duration_ms: float = 0

@dataclass
class DebugSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = ""
    agent_id: str = ""
    frames: List[DebugFrame] = field(default_factory=list)
    total_duration_ms: float = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class TimeTravelDebugger:
    """Records and replays agent execution traces frame-by-frame."""
    
    def __init__(self):
        self._sessions: Dict[str, DebugSession] = {}
        self._active_recordings: Dict[str, DebugSession] = {}  # execution_id -> session

    def start_recording(self, execution_id: str, agent_id: str) -> str:
        session = DebugSession(execution_id=execution_id, agent_id=agent_id)
        self._active_recordings[execution_id] = session
        logger.info(f"Debug recording started: {session.id} for execution {execution_id}")
        return session.id

    def record_frame(self, execution_id: str, phase: str, label: str, data: dict = None, duration_ms: float = 0):
        session = self._active_recordings.get(execution_id)
        if not session:
            return
        frame = DebugFrame(
            index=len(session.frames),
            timestamp=datetime.now(timezone.utc).isoformat(),
            phase=phase,
            label=label,
            data=data or {},
            duration_ms=duration_ms,
        )
        session.frames.append(frame)

    def stop_recording(self, execution_id: str) -> Optional[DebugSession]:
        session = self._active_recordings.pop(execution_id, None)
        if session:
            session.total_duration_ms = sum(f.duration_ms for f in session.frames)
            self._sessions[session.id] = session
            logger.info(f"Debug recording complete: {session.id}, {len(session.frames)} frames")
        return session

    def get_session(self, session_id: str) -> Optional[dict]:
        session = self._sessions.get(session_id)
        return asdict(session) if session else None

    def get_frame(self, session_id: str, frame_index: int) -> Optional[dict]:
        session = self._sessions.get(session_id)
        if session and 0 <= frame_index < len(session.frames):
            return asdict(session.frames[frame_index])
        return None

    def get_frames_range(self, session_id: str, start: int = 0, end: int = -1) -> List[dict]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        frames = session.frames[start:end if end > 0 else len(session.frames)]
        return [asdict(f) for f in frames]

    def list_sessions(self, agent_id: str = None, limit: int = 20) -> List[dict]:
        sessions = list(self._sessions.values())
        if agent_id:
            sessions = [s for s in sessions if s.agent_id == agent_id]
        sessions.sort(key=lambda s: s.created_at, reverse=True)
        return [{"id": s.id, "execution_id": s.execution_id, "agent_id": s.agent_id, "frame_count": len(s.frames), "total_duration_ms": s.total_duration_ms, "created_at": s.created_at} for s in sessions[:limit]]

    def search_frames(self, session_id: str, phase: str = None, label_contains: str = None) -> List[dict]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        frames = session.frames
        if phase:
            frames = [f for f in frames if f.phase == phase]
        if label_contains:
            frames = [f for f in frames if label_contains.lower() in f.label.lower()]
        return [asdict(f) for f in frames]

time_travel_debugger = TimeTravelDebugger()
