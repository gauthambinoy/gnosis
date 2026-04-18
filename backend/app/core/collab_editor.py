"""Collaborative Agent Editing — track who edited what in agent configs."""

from dataclasses import dataclass, field, asdict
from typing import Dict, List
from datetime import datetime, timezone
import uuid


@dataclass
class EditSession:
    id: str
    agent_id: str
    user_id: str
    changes: List[dict] = field(default_factory=list)
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: str = "active"  # active / closed


class CollabEditorEngine:
    def __init__(self):
        self._sessions: Dict[str, EditSession] = {}

    def start_session(self, agent_id: str, user_id: str) -> EditSession:
        session = EditSession(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            user_id=user_id,
        )
        self._sessions[session.id] = session
        return session

    def apply_change(
        self, session_id: str, field_name: str, old_value: str, new_value: str
    ) -> EditSession:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session {session_id} not found")
        if session.status != "active":
            raise ValueError("Session is closed")
        session.changes.append(
            {
                "field": field_name,
                "old": old_value,
                "new": new_value,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return session

    def close_session(self, session_id: str) -> EditSession:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session {session_id} not found")
        session.status = "closed"
        return session

    def list_sessions(self, agent_id: str) -> List[dict]:
        return [asdict(s) for s in self._sessions.values() if s.agent_id == agent_id]


collab_editor = CollabEditorEngine()
