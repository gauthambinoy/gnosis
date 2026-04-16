"""Gnosis State Snapshots — capture and restore complete agent state."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
import json
import sys


@dataclass
class StateSnapshot:
    id: str
    agent_id: str
    state: dict
    memory_count: int
    config: dict
    created_at: str
    size_bytes: int = 0
    description: str = ""

    def __post_init__(self):
        if not self.size_bytes:
            self.size_bytes = sys.getsizeof(json.dumps(self.state, default=str))


class StateSnapshotEngine:
    """Capture and restore complete agent state snapshots."""

    def __init__(self):
        self._snapshots: dict[str, StateSnapshot] = {}

    def capture_snapshot(self, agent_id: str, state: dict | None = None,
                         config: dict | None = None, description: str = "") -> StateSnapshot:
        state = state or {"status": "active", "context": {}}
        config = config or {}
        snap = StateSnapshot(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            state=state,
            memory_count=len(state.get("memories", [])),
            config=config,
            created_at=datetime.now(timezone.utc).isoformat(),
            description=description,
        )
        self._snapshots[snap.id] = snap
        return snap

    def restore_snapshot(self, snapshot_id: str) -> dict | None:
        snap = self._snapshots.get(snapshot_id)
        if not snap:
            return None
        return {"agent_id": snap.agent_id, "state": snap.state, "config": snap.config, "restored_at": datetime.now(timezone.utc).isoformat()}

    def list_snapshots(self, agent_id: str) -> list[StateSnapshot]:
        return [s for s in self._snapshots.values() if s.agent_id == agent_id]

    def diff_snapshots(self, id_a: str, id_b: str) -> dict | None:
        a = self._snapshots.get(id_a)
        b = self._snapshots.get(id_b)
        if not a or not b:
            return None
        added = {k: b.state[k] for k in b.state if k not in a.state}
        removed = {k: a.state[k] for k in a.state if k not in b.state}
        changed = {k: {"old": a.state[k], "new": b.state[k]} for k in a.state if k in b.state and a.state[k] != b.state[k]}
        return {
            "snapshot_a": id_a, "snapshot_b": id_b,
            "added": added, "removed": removed, "changed": changed,
            "size_diff": b.size_bytes - a.size_bytes,
        }


state_snapshot_engine = StateSnapshotEngine()
