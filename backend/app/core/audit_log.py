"""Gnosis Audit Log — immutable audit trail of all agent actions."""

import json
import hashlib
from datetime import datetime, timezone

from app.core.event_bus import event_bus


class AuditLog:
    """Immutable audit trail of all agent actions.

    Each entry is chained via a hash of the previous entry to detect tampering.
    """

    def __init__(self):
        self.entries: list[dict] = []
        self._last_hash: str = "genesis"

    async def log(
        self, event_type: str, agent_id: str, details: dict, user_id: str | None = None
    ):
        """Log an audit event with timestamp, type, agent, details, and integrity hash."""
        entry = {
            "id": len(self.entries),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "agent_id": agent_id,
            "user_id": user_id,
            "details": details,
            "prev_hash": self._last_hash,
        }
        # Chain hash for tamper detection
        raw = json.dumps(entry, sort_keys=True, default=str)
        entry["hash"] = hashlib.sha256(raw.encode()).hexdigest()
        self._last_hash = entry["hash"]

        self.entries.append(entry)

    async def query(
        self,
        agent_id: str | None = None,
        event_type: str | None = None,
        since: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query audit entries with optional filters."""
        results = self.entries

        if agent_id:
            results = [e for e in results if e["agent_id"] == agent_id]
        if event_type:
            results = [e for e in results if e["event_type"] == event_type]
        if since:
            results = [e for e in results if e["timestamp"] >= since]

        return results[-limit:]

    async def get_agent_trail(self, agent_id: str) -> list[dict]:
        """Get full audit trail for a specific agent."""
        return [e for e in self.entries if e["agent_id"] == agent_id]

    async def export(self, format: str = "json") -> str:
        """Export audit log in the specified format."""
        if format == "json":
            return json.dumps(self.entries, indent=2, default=str)
        elif format == "csv":
            if not self.entries:
                return "id,timestamp,event_type,agent_id,user_id,details_summary\n"
            lines = ["id,timestamp,event_type,agent_id,user_id,details_summary"]
            for e in self.entries:
                details_summary = json.dumps(e.get("details", {}), default=str)[:200]
                details_summary = details_summary.replace('"', '""')
                lines.append(
                    f"{e['id']},{e['timestamp']},{e['event_type']},"
                    f"{e['agent_id']},{e.get('user_id', '')},"
                    f'"{details_summary}"'
                )
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def verify_integrity(self) -> dict:
        """Verify the hash chain hasn't been tampered with."""
        if not self.entries:
            return {"valid": True, "entries_checked": 0}

        prev_hash = "genesis"
        for i, entry in enumerate(self.entries):
            if entry["prev_hash"] != prev_hash:
                return {"valid": False, "broken_at": i, "entries_checked": i}
            # Recompute hash
            check_entry = {k: v for k, v in entry.items() if k != "hash"}
            raw = json.dumps(check_entry, sort_keys=True, default=str)
            expected = hashlib.sha256(raw.encode()).hexdigest()
            if entry["hash"] != expected:
                return {"valid": False, "broken_at": i, "entries_checked": i}
            prev_hash = entry["hash"]

        return {"valid": True, "entries_checked": len(self.entries)}


# Global singleton
audit_log = AuditLog()


# ------------------------------------------------------------------
# Event bus integration: subscribe to relevant events
# ------------------------------------------------------------------


async def _on_audit_event(event: dict):
    """Generic handler that logs any event bus event to the audit log."""
    event_type = event.get("type", "unknown")
    payload = event.get("payload", {})
    agent_id = payload.get("agent_id", "system")
    user_id = payload.get("user_id")
    await audit_log.log(event_type, agent_id, payload, user_id=user_id)


def wire_audit_log():
    """Subscribe audit log to all execution.*, correction.*, trust.* events."""
    from app.core.event_bus import Events

    audit_events = [
        Events.EXECUTION_STARTED,
        Events.EXECUTION_COMPLETED,
        Events.EXECUTION_FAILED,
        Events.CORRECTION_RECEIVED,
        Events.TRUST_CHANGED,
        Events.AGENT_CREATED,
        Events.AGENT_UPDATED,
        Events.AGENT_DELETED,
        Events.LEARNING_COMPLETED,
        Events.INSIGHT_GENERATED,
    ]
    for evt in audit_events:
        event_bus.on(evt, _on_audit_event)
