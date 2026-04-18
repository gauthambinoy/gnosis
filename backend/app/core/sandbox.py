"""Sandbox demo environment for safe experimentation."""

import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("gnosis.sandbox")


@dataclass
class SandboxSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    expires_at: str = ""
    state: dict = field(default_factory=dict)
    actions_count: int = 0
    max_actions: int = 100


class SandboxEngine:
    def __init__(self):
        self._sessions: Dict[str, SandboxSession] = {}

    def create_session(self, user_id: str, ttl_minutes: int = 30) -> dict:
        session = SandboxSession(
            user_id=user_id,
            expires_at=(
                datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
            ).isoformat(),
        )
        self._sessions[session.id] = session
        return asdict(session)

    def execute_in_sandbox(self, session_id: str, action: dict) -> dict:
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        if session.actions_count >= session.max_actions:
            return {"error": "Action limit reached"}
        session.actions_count += 1
        return {
            "action": action,
            "result": "simulated",
            "actions_remaining": session.max_actions - session.actions_count,
        }

    def get_session(self, session_id: str) -> dict:
        s = self._sessions.get(session_id)
        return asdict(s) if s else {"error": "Not found"}

    def destroy_session(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None


sandbox_engine = SandboxEngine()
