"""Gnosis Execution Recorder — Records execution steps for replay."""
import uuid, time, logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("gnosis.recorder")


@dataclass
class ExecutionStep:
    phase: str  # perceive, memory, context, reason, meta, act, post
    status: str  # started, completed, failed
    input_summary: str = ""
    output_summary: str = ""
    duration_ms: float = 0
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ExecutionRecording:
    id: str
    agent_id: str
    task: str
    steps: List[ExecutionStep] = field(default_factory=list)
    total_duration_ms: float = 0
    token_usage: dict = field(default_factory=dict)
    status: str = "running"  # running, completed, failed
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None


class ExecutionRecorder:
    def __init__(self, max_recordings: int = 1000):
        self._recordings: Dict[str, ExecutionRecording] = {}
        self._agent_recordings: Dict[str, List[str]] = {}  # agent_id -> recording_ids
        self._max = max_recordings

    def start_recording(self, agent_id: str, task: str) -> ExecutionRecording:
        recording = ExecutionRecording(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            task=task[:500],
        )
        self._recordings[recording.id] = recording
        self._agent_recordings.setdefault(agent_id, []).append(recording.id)

        # Prune if over limit
        if len(self._recordings) > self._max:
            oldest_key = next(iter(self._recordings))
            self._recordings.pop(oldest_key, None)

        return recording

    def add_step(self, recording_id: str, phase: str, status: str,
                 input_summary: str = "", output_summary: str = "",
                 duration_ms: float = 0, metadata: dict = None):
        recording = self._recordings.get(recording_id)
        if not recording:
            return
        recording.steps.append(ExecutionStep(
            phase=phase, status=status,
            input_summary=input_summary[:300],
            output_summary=output_summary[:300],
            duration_ms=duration_ms,
            metadata=metadata or {},
        ))

    def complete_recording(self, recording_id: str, status: str = "completed", token_usage: dict = None):
        recording = self._recordings.get(recording_id)
        if not recording:
            return
        recording.status = status
        recording.completed_at = datetime.now(timezone.utc).isoformat()
        recording.total_duration_ms = sum(s.duration_ms for s in recording.steps)
        if token_usage:
            recording.token_usage = token_usage

    def get_recording(self, recording_id: str) -> Optional[ExecutionRecording]:
        return self._recordings.get(recording_id)

    def list_recordings(self, agent_id: str = None, limit: int = 50) -> List[ExecutionRecording]:
        if agent_id:
            ids = self._agent_recordings.get(agent_id, [])
            recordings = [self._recordings[rid] for rid in reversed(ids) if rid in self._recordings]
        else:
            recordings = sorted(self._recordings.values(), key=lambda r: r.started_at, reverse=True)
        return recordings[:limit]

    @property
    def stats(self) -> dict:
        statuses = {}
        for r in self._recordings.values():
            statuses[r.status] = statuses.get(r.status, 0) + 1
        return {"total_recordings": len(self._recordings), "by_status": statuses}


execution_recorder = ExecutionRecorder()
