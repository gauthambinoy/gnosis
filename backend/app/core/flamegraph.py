"""Gnosis Flamegraph — Visual execution profiling for agent runs."""

import uuid
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

logger = logging.getLogger("gnosis.flamegraph")


@dataclass
class FlameSpan:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    parent_id: Optional[str] = None
    start_ms: float = 0
    end_ms: float = 0
    duration_ms: float = 0
    metadata: dict = field(default_factory=dict)
    children: List["FlameSpan"] = field(default_factory=list)


@dataclass
class FlameProfile:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = ""
    agent_id: str = ""
    root_spans: List[FlameSpan] = field(default_factory=list)
    total_duration_ms: float = 0
    created_at: str = ""


class FlameProfiler:
    """Profiles agent execution into flamegraph-compatible spans."""

    def __init__(self):
        self._profiles: Dict[str, FlameProfile] = {}
        self._active: Dict[
            str, dict
        ] = {}  # execution_id -> {"profile": ..., "stack": [...], "start": ...}

    def start_profile(self, execution_id: str, agent_id: str = "") -> str:
        profile = FlameProfile(execution_id=execution_id, agent_id=agent_id)
        self._active[execution_id] = {
            "profile": profile,
            "stack": [],
            "start": time.time() * 1000,
            "all_spans": {},
        }
        return profile.id

    def push_span(
        self, execution_id: str, name: str, metadata: dict = None
    ) -> Optional[str]:
        ctx = self._active.get(execution_id)
        if not ctx:
            return None

        span = FlameSpan(
            name=name,
            start_ms=time.time() * 1000 - ctx["start"],
            metadata=metadata or {},
        )

        if ctx["stack"]:
            span.parent_id = ctx["stack"][-1].id

        ctx["stack"].append(span)
        ctx["all_spans"][span.id] = span
        return span.id

    def pop_span(self, execution_id: str) -> Optional[dict]:
        ctx = self._active.get(execution_id)
        if not ctx or not ctx["stack"]:
            return None

        span = ctx["stack"].pop()
        span.end_ms = time.time() * 1000 - ctx["start"]
        span.duration_ms = span.end_ms - span.start_ms

        if ctx["stack"]:
            ctx["stack"][-1].children.append(span)
        else:
            ctx["profile"].root_spans.append(span)

        return asdict(span)

    def end_profile(self, execution_id: str) -> Optional[dict]:
        ctx = self._active.pop(execution_id, None)
        if not ctx:
            return None

        # Close any remaining spans
        while ctx["stack"]:
            self._active[execution_id] = ctx
            self.pop_span(execution_id)
        self._active.pop(execution_id, None)

        profile = ctx["profile"]
        profile.total_duration_ms = time.time() * 1000 - ctx["start"]
        from datetime import datetime, timezone

        profile.created_at = datetime.now(timezone.utc).isoformat()
        self._profiles[profile.id] = profile
        return self._profile_to_dict(profile)

    def get_profile(self, profile_id: str) -> Optional[dict]:
        profile = self._profiles.get(profile_id)
        return self._profile_to_dict(profile) if profile else None

    def list_profiles(self, agent_id: str = None, limit: int = 20) -> List[dict]:
        profiles = list(self._profiles.values())
        if agent_id:
            profiles = [p for p in profiles if p.agent_id == agent_id]
        profiles.sort(key=lambda p: p.created_at, reverse=True)
        return [
            {
                "id": p.id,
                "execution_id": p.execution_id,
                "agent_id": p.agent_id,
                "total_duration_ms": p.total_duration_ms,
                "span_count": self._count_spans(p),
                "created_at": p.created_at,
            }
            for p in profiles[:limit]
        ]

    def _count_spans(self, profile: FlameProfile) -> int:
        count = 0

        def _count(spans):
            nonlocal count
            for s in spans:
                count += 1
                _count(s.children)

        _count(profile.root_spans)
        return count

    def _profile_to_dict(self, profile: FlameProfile) -> dict:
        def _span_dict(span):
            return {
                "id": span.id,
                "name": span.name,
                "parent_id": span.parent_id,
                "start_ms": round(span.start_ms, 2),
                "end_ms": round(span.end_ms, 2),
                "duration_ms": round(span.duration_ms, 2),
                "metadata": span.metadata,
                "children": [_span_dict(c) for c in span.children],
            }

        return {
            "id": profile.id,
            "execution_id": profile.execution_id,
            "agent_id": profile.agent_id,
            "total_duration_ms": round(profile.total_duration_ms, 2),
            "created_at": profile.created_at,
            "spans": [_span_dict(s) for s in profile.root_spans],
        }


flame_profiler = FlameProfiler()
