"""Gnosis Activity Feed — Workspace-level activity stream with @mentions."""

import uuid
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List
from collections import defaultdict

logger = logging.getLogger("gnosis.activity")


@dataclass
class ActivityEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str = ""
    actor_id: str = ""  # User or agent ID
    actor_type: str = "user"  # "user" or "agent"
    event_type: str = (
        ""  # "agent.created", "execution.completed", "pipeline.failed", etc.
    )
    title: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)
    mentions: List[str] = field(default_factory=list)  # @mentioned user IDs
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    read_by: List[str] = field(default_factory=list)


class ActivityFeed:
    def __init__(self, max_per_workspace: int = 1000):
        self._events: Dict[str, List[ActivityEvent]] = defaultdict(list)
        self._max = max_per_workspace

    def publish(
        self,
        workspace_id: str,
        event_type: str,
        title: str,
        actor_id: str = "",
        actor_type: str = "user",
        description: str = "",
        metadata: dict = None,
        mentions: list = None,
    ) -> ActivityEvent:
        event = ActivityEvent(
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=actor_type,
            event_type=event_type,
            title=title,
            description=description,
            metadata=metadata or {},
            mentions=mentions or [],
        )
        self._events[workspace_id].append(event)
        # Trim to max
        if len(self._events[workspace_id]) > self._max:
            self._events[workspace_id] = self._events[workspace_id][-self._max :]
        logger.info(f"Activity: [{workspace_id}] {event_type}: {title}")
        return event

    def get_feed(
        self,
        workspace_id: str,
        limit: int = 50,
        event_type: str = None,
        after: str = None,
    ) -> List[dict]:
        events = self._events.get(workspace_id, [])
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if after:
            events = [e for e in events if e.timestamp > after]
        return [
            asdict(e)
            for e in sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]
        ]

    def get_mentions(
        self, workspace_id: str, user_id: str, unread_only: bool = True
    ) -> List[dict]:
        events = self._events.get(workspace_id, [])
        mentioned = [e for e in events if user_id in e.mentions]
        if unread_only:
            mentioned = [e for e in mentioned if user_id not in e.read_by]
        return [
            asdict(e)
            for e in sorted(mentioned, key=lambda e: e.timestamp, reverse=True)
        ]

    def mark_read(self, event_id: str, user_id: str) -> bool:
        for events in self._events.values():
            for event in events:
                if event.id == event_id:
                    if user_id not in event.read_by:
                        event.read_by.append(user_id)
                    return True
        return False

    def stats(self, workspace_id: str) -> dict:
        events = self._events.get(workspace_id, [])
        types = {}
        for e in events:
            types[e.event_type] = types.get(e.event_type, 0) + 1
        return {"total_events": len(events), "by_type": types}


activity_feed = ActivityFeed()
