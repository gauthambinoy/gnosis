"""Gnosis Trust Engine — auto-evolving trust levels based on agent performance."""

from datetime import datetime, timedelta, timezone

from app.core.event_bus import event_bus, Events


class TrustEngine:
    """Auto-evolving trust levels based on agent performance."""

    LEVELS = {
        0: {"name": "Observer", "permissions": ["read"], "auto_approve": False},
        1: {
            "name": "Apprentice",
            "permissions": ["read", "draft"],
            "auto_approve": False,
        },
        2: {
            "name": "Operator",
            "permissions": ["read", "draft", "execute_safe"],
            "auto_approve": True,
            "limit": 10,
        },
        3: {
            "name": "Trusted",
            "permissions": ["read", "draft", "execute_safe", "execute_risky"],
            "auto_approve": True,
            "limit": 50,
        },
        4: {
            "name": "Autonomous",
            "permissions": ["all"],
            "auto_approve": True,
            "limit": None,
        },
    }

    PROMOTE_MIN_EXECUTIONS = 20
    PROMOTE_MIN_ACCURACY = 0.95
    PROMOTE_CRITICAL_FREE_DAYS = 7
    DEMOTE_ACCURACY_THRESHOLD = 0.80
    DEMOTE_WINDOW = 10

    def __init__(self):
        self._agent_trust: dict[str, int] = {}  # agent_id -> current level
        self._agent_history: dict[str, list[dict]] = {}  # agent_id -> execution records
        self._change_log: list[dict] = []

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    async def evaluate(self, agent_id: str, metrics: dict) -> dict:
        """Evaluate agent and recommend trust level change.

        Promote: >95% accuracy over 20+ executions, 0 critical failures in 7 days.
        Demote: <80% accuracy over last 10 executions, or any critical failure.
        """
        current = self._agent_trust.get(agent_id, 0)
        history = self._agent_history.get(agent_id, [])

        total = metrics.get("total_executions", len(history))
        accuracy = metrics.get("accuracy", self._calc_accuracy(history))
        critical_failures = metrics.get(
            "critical_failures_7d", self._recent_critical_failures(agent_id, days=7)
        )

        recommendation = "hold"
        reason = "Insufficient data or stable performance."

        # Check demotion first (safety takes priority)
        recent = history[-self.DEMOTE_WINDOW :] if history else []
        recent_accuracy = self._calc_accuracy(recent) if recent else accuracy

        if critical_failures > 0:
            recommendation = "demote"
            reason = f"Critical failure detected in last 7 days ({critical_failures} failure(s))."
        elif (
            len(recent) >= self.DEMOTE_WINDOW
            and recent_accuracy < self.DEMOTE_ACCURACY_THRESHOLD
        ):
            recommendation = "demote"
            reason = f"Recent accuracy {recent_accuracy:.1%} below {self.DEMOTE_ACCURACY_THRESHOLD:.0%} threshold over last {self.DEMOTE_WINDOW} executions."
        elif (
            total >= self.PROMOTE_MIN_EXECUTIONS
            and accuracy >= self.PROMOTE_MIN_ACCURACY
            and critical_failures == 0
            and current < 4
        ):
            recommendation = "promote"
            reason = f"Accuracy {accuracy:.1%} over {total} executions with 0 critical failures."

        return {
            "agent_id": agent_id,
            "current_level": current,
            "current_name": self.LEVELS[current]["name"],
            "recommendation": recommendation,
            "reason": reason,
            "metrics": {
                "total_executions": total,
                "accuracy": round(accuracy, 4),
                "recent_accuracy": round(recent_accuracy, 4),
                "critical_failures_7d": critical_failures,
            },
        }

    async def check_permission(
        self, agent_id: str, action: str, trust_level: int | None = None
    ) -> dict:
        """Check if agent can perform action at current trust level."""
        level = (
            trust_level
            if trust_level is not None
            else self._agent_trust.get(agent_id, 0)
        )
        level_info = self.LEVELS.get(level, self.LEVELS[0])

        permissions = level_info["permissions"]
        allowed = "all" in permissions or action in permissions
        auto_approve = level_info.get("auto_approve", False)
        requires_approval = not auto_approve and allowed

        if not allowed:
            reason = f"Action '{action}' not permitted at trust level {level} ({level_info['name']})."
        elif requires_approval:
            reason = f"Action '{action}' allowed but requires human approval at level {level} ({level_info['name']})."
        else:
            reason = f"Action '{action}' auto-approved at level {level} ({level_info['name']})."

        limit = level_info.get("limit")

        return {
            "allowed": allowed,
            "reason": reason,
            "requires_approval": requires_approval,
            "trust_level": level,
            "trust_name": level_info["name"],
            "execution_limit": limit,
        }

    async def promote(self, agent_id: str) -> dict:
        """Promote agent to next trust level."""
        current = self._agent_trust.get(agent_id, 0)
        if current >= 4:
            return {
                "agent_id": agent_id,
                "level": current,
                "name": self.LEVELS[current]["name"],
                "changed": False,
                "reason": "Already at maximum trust level.",
            }

        new_level = current + 1
        self._agent_trust[agent_id] = new_level

        change = {
            "agent_id": agent_id,
            "from_level": current,
            "to_level": new_level,
            "from_name": self.LEVELS[current]["name"],
            "to_name": self.LEVELS[new_level]["name"],
            "action": "promote",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._change_log.append(change)

        await event_bus.emit(Events.TRUST_CHANGED, change)

        return {
            "agent_id": agent_id,
            "level": new_level,
            "name": self.LEVELS[new_level]["name"],
            "changed": True,
            "reason": f"Promoted from {self.LEVELS[current]['name']} to {self.LEVELS[new_level]['name']}.",
        }

    async def demote(
        self, agent_id: str, reason: str = "Performance degradation"
    ) -> dict:
        """Demote agent to previous trust level."""
        current = self._agent_trust.get(agent_id, 0)
        if current <= 0:
            return {
                "agent_id": agent_id,
                "level": current,
                "name": self.LEVELS[current]["name"],
                "changed": False,
                "reason": "Already at minimum trust level.",
            }

        new_level = current - 1
        self._agent_trust[agent_id] = new_level

        change = {
            "agent_id": agent_id,
            "from_level": current,
            "to_level": new_level,
            "from_name": self.LEVELS[current]["name"],
            "to_name": self.LEVELS[new_level]["name"],
            "action": "demote",
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._change_log.append(change)

        await event_bus.emit(Events.TRUST_CHANGED, change)

        return {
            "agent_id": agent_id,
            "level": new_level,
            "name": self.LEVELS[new_level]["name"],
            "changed": True,
            "reason": f"Demoted from {self.LEVELS[current]['name']} to {self.LEVELS[new_level]['name']}: {reason}",
        }

    async def get_trust_report(self, agent_id: str) -> dict:
        """Full trust report for an agent."""
        level = self._agent_trust.get(agent_id, 0)
        level_info = self.LEVELS[level]
        history = self._agent_history.get(agent_id, [])
        changes = [c for c in self._change_log if c["agent_id"] == agent_id]

        return {
            "agent_id": agent_id,
            "current_level": level,
            "current_name": level_info["name"],
            "permissions": level_info["permissions"],
            "auto_approve": level_info.get("auto_approve", False),
            "execution_limit": level_info.get("limit"),
            "total_executions": len(history),
            "accuracy": round(self._calc_accuracy(history), 4),
            "recent_accuracy": round(
                self._calc_accuracy(history[-self.DEMOTE_WINDOW :]), 4
            )
            if history
            else 0.0,
            "critical_failures_7d": self._recent_critical_failures(agent_id, days=7),
            "change_history": changes[-20:],
        }

    # ------------------------------------------------------------------
    # Record-keeping
    # ------------------------------------------------------------------

    def record_execution(self, agent_id: str, success: bool, critical: bool = False):
        """Record an execution result for trust evaluation."""
        if agent_id not in self._agent_history:
            self._agent_history[agent_id] = []
        self._agent_history[agent_id].append(
            {
                "success": success,
                "critical_failure": critical and not success,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def set_trust_level(self, agent_id: str, level: int):
        """Directly set trust level (for initialization)."""
        self._agent_trust[agent_id] = max(0, min(4, level))

    def get_trust_level(self, agent_id: str) -> int:
        return self._agent_trust.get(agent_id, 0)

    # ------------------------------------------------------------------
    # Backward-compatible API
    # ------------------------------------------------------------------

    async def evaluate_trust(self, agent_id: str) -> int:
        return self.get_trust_level(agent_id)

    async def should_require_approval(
        self, agent_id: str, action_type: str, confidence: float
    ) -> bool:
        result = await self.check_permission(agent_id, action_type)
        if not result["allowed"]:
            return True
        return result["requires_approval"]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_accuracy(records: list[dict]) -> float:
        if not records:
            return 0.0
        successes = sum(1 for r in records if r.get("success", False))
        return successes / len(records)

    def _recent_critical_failures(self, agent_id: str, days: int = 7) -> int:
        history = self._agent_history.get(agent_id, [])
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        return sum(
            1
            for r in history
            if r.get("critical_failure", False) and r.get("timestamp", "") >= cutoff
        )


# Global singleton
trust_engine = TrustEngine()
