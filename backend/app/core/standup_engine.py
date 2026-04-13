"""Gnosis Standup Engine — generates daily briefings summarizing all agent activity."""

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.audit_log import audit_log
from app.core.cost_tracker import cost_tracker
from app.core.trust_engine import trust_engine


class StandupEngine:
    """Generates daily briefings summarizing all agent activity."""

    async def generate(self) -> dict:
        """Generate standup report covering the last 24 hours.

        Includes:
        - Total executions with success/fail counts
        - Top and worst performing agents
        - Cost summary (tokens used, USD spent)
        - Notable events (trust changes, corrections, failures)
        - Recommendations
        """
        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=24)).isoformat()

        # Gather audit entries from the last 24h
        recent_entries = await audit_log.query(since=since, limit=5000)

        # Execution stats
        exec_started = [e for e in recent_entries if e["event_type"] == "execution.started"]
        exec_completed = [e for e in recent_entries if e["event_type"] == "execution.completed"]
        exec_failed = [e for e in recent_entries if e["event_type"] == "execution.failed"]

        total_executions = len(exec_started)
        success_count = len(exec_completed)
        fail_count = len(exec_failed)

        # Per-agent breakdown
        agent_stats: dict[str, dict] = {}
        for entry in exec_started:
            aid = entry.get("agent_id", "unknown")
            if aid not in agent_stats:
                agent_stats[aid] = {"executions": 0, "successes": 0, "failures": 0, "total_cost_usd": 0.0, "total_latency_ms": 0.0}
            agent_stats[aid]["executions"] += 1

        for entry in exec_completed:
            aid = entry.get("agent_id", "unknown")
            if aid in agent_stats:
                agent_stats[aid]["successes"] += 1
                details = entry.get("details", {})
                agent_stats[aid]["total_cost_usd"] += details.get("total_cost_usd", 0.0)
                agent_stats[aid]["total_latency_ms"] += details.get("total_latency_ms", 0.0)

        for entry in exec_failed:
            aid = entry.get("agent_id", "unknown")
            if aid in agent_stats:
                agent_stats[aid]["failures"] += 1

        # Top / worst performing agent
        top_agent = None
        worst_agent = None
        if agent_stats:
            scored = []
            for aid, stats in agent_stats.items():
                rate = stats["successes"] / stats["executions"] if stats["executions"] > 0 else 0
                scored.append({"agent_id": aid, "success_rate": rate, **stats})
            scored.sort(key=lambda x: (-x["success_rate"], -x["executions"]))
            top_agent = scored[0] if scored else None
            worst_agent = scored[-1] if len(scored) > 1 else None

        # Cost summary
        today_costs = cost_tracker.today_stats

        # Notable events
        notable: list[dict] = []
        trust_changes = [e for e in recent_entries if e["event_type"] == "trust.changed"]
        for tc in trust_changes:
            notable.append({"type": "trust_change", "agent_id": tc["agent_id"], "details": tc.get("details", {}), "timestamp": tc["timestamp"]})

        corrections = [e for e in recent_entries if e["event_type"] == "correction.received"]
        for c in corrections:
            notable.append({"type": "correction", "agent_id": c["agent_id"], "details": c.get("details", {}), "timestamp": c["timestamp"]})

        if exec_failed:
            for f in exec_failed[:5]:
                notable.append({"type": "failure", "agent_id": f["agent_id"], "details": f.get("details", {}), "timestamp": f["timestamp"]})

        return {
            "generated_at": now.isoformat(),
            "period": {"from": since, "to": now.isoformat()},
            "summary": {
                "total_executions": total_executions,
                "successes": success_count,
                "failures": fail_count,
                "success_rate": round(success_count / total_executions, 4) if total_executions > 0 else 0.0,
            },
            "top_agent": top_agent,
            "worst_agent": worst_agent,
            "cost_summary": {
                "tokens_used": today_costs.get("tokens", 0),
                "usd_spent": round(today_costs.get("cost", 0.0), 6),
                "requests": today_costs.get("requests", 0),
            },
            "notable_events": notable[:20],
            "agent_count": len(agent_stats),
            "agents": agent_stats,
        }

    async def get_agent_summary(self, agent_id: str) -> dict:
        """Individual agent 24h summary."""
        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=24)).isoformat()

        entries = await audit_log.query(agent_id=agent_id, since=since, limit=5000)

        exec_started = [e for e in entries if e["event_type"] == "execution.started"]
        exec_completed = [e for e in entries if e["event_type"] == "execution.completed"]
        exec_failed = [e for e in entries if e["event_type"] == "execution.failed"]
        corrections = [e for e in entries if e["event_type"] == "correction.received"]
        trust_changes = [e for e in entries if e["event_type"] == "trust.changed"]

        total = len(exec_started)
        successes = len(exec_completed)
        failures = len(exec_failed)

        total_cost = sum(e.get("details", {}).get("total_cost_usd", 0.0) for e in exec_completed)
        total_latency = sum(e.get("details", {}).get("total_latency_ms", 0.0) for e in exec_completed)

        trust_level = trust_engine.get_trust_level(agent_id)
        trust_info = trust_engine.LEVELS.get(trust_level, {})

        return {
            "agent_id": agent_id,
            "generated_at": now.isoformat(),
            "period": {"from": since, "to": now.isoformat()},
            "trust_level": trust_level,
            "trust_name": trust_info.get("name", "Unknown"),
            "executions": {
                "total": total,
                "successes": successes,
                "failures": failures,
                "success_rate": round(successes / total, 4) if total > 0 else 0.0,
            },
            "cost": {
                "total_usd": round(total_cost, 6),
                "avg_per_execution": round(total_cost / total, 6) if total > 0 else 0.0,
            },
            "avg_latency_ms": round(total_latency / successes, 1) if successes > 0 else 0.0,
            "corrections_received": len(corrections),
            "trust_changes": [{"details": tc.get("details", {}), "timestamp": tc["timestamp"]} for tc in trust_changes],
            "recent_events": entries[-10:],
        }


# Global singleton
standup_engine = StandupEngine()
