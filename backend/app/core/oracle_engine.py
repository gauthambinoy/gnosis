"""Gnosis Oracle — proactive cross-agent pattern detection and insights."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent


class OracleEngine:
    """Generates cross-agent insights by analyzing patterns across all agents."""

    FAILURE_THRESHOLD = 0.20  # >20% failure rate triggers alert
    LOW_ACCURACY_THRESHOLD = 0.70
    HIGH_COST_MULTIPLIER = 3.0  # 3x average cost is high
    UNDERUSED_MEMORY_THRESHOLD = 5  # agents with < N memories may need tuning

    # --- Public API ---

    async def analyze_patterns(self, db: AsyncSession) -> list[dict]:
        """Find patterns: repeated failures, similar tasks, optimization opportunities."""
        agents = await self._load_agents(db)
        if not agents:
            return []

        patterns: list[dict] = []
        patterns.extend(self._detect_high_failure_agents(agents))
        patterns.extend(self._detect_low_accuracy_agents(agents))
        patterns.extend(self._detect_duplicate_work(agents))
        patterns.extend(self._detect_cost_outliers(agents))
        patterns.extend(self._detect_underused_memory(agents))
        return patterns

    async def generate_insights(self, db: AsyncSession) -> list[dict]:
        """Generate actionable insights with severity (critical/warning/info/success)."""
        agents = await self._load_agents(db)
        if not agents:
            return [
                self._make_insight(
                    "info",
                    "suggestion",
                    "No agents found",
                    "Create your first agent to start receiving insights.",
                    suggested_action="Navigate to Awaken to create an agent.",
                )
            ]

        insights: list[dict] = []

        # Analyze patterns
        patterns = await self.analyze_patterns(db)
        for pattern in patterns:
            insights.append(pattern)

        # Success insights
        for agent in agents:
            if agent.total_executions >= 10 and agent.accuracy >= 0.95:
                insights.append(
                    self._make_insight(
                        "success",
                        "trend",
                        f"{agent.name} performing excellently",
                        f"{agent.name} has {agent.accuracy * 100:.0f}% accuracy across {agent.total_executions} executions.",
                        agent_id=str(agent.id),
                        suggested_action="Consider promoting trust level."
                        if agent.trust_level < 3
                        else None,
                    )
                )

        # Platform-wide insight
        total_exec = sum(a.total_executions or 0 for a in agents)
        total_saved = sum(a.time_saved_minutes or 0 for a in agents)
        if total_exec > 0:
            insights.append(
                self._make_insight(
                    "info",
                    "trend",
                    f"Platform activity: {total_exec} executions",
                    f"Your agents have executed {total_exec} tasks and saved {total_saved:.0f} minutes total.",
                )
            )

        return insights

    async def get_health_score(self, db: AsyncSession) -> dict:
        """Overall platform health: agent reliability, memory utilization, cost efficiency."""
        agents = await self._load_agents(db)

        if not agents:
            return {
                "overall": 0.0,
                "agent_reliability": 0.0,
                "memory_utilization": 0.0,
                "cost_efficiency": 0.0,
                "active_agents": 0,
                "total_agents": 0,
                "details": {},
            }

        total = len(agents)
        active = sum(1 for a in agents if a.status.value in ("active", "idle"))
        with_executions = [a for a in agents if (a.total_executions or 0) > 0]

        # Agent reliability: weighted average accuracy
        if with_executions:
            total_exec = sum(a.total_executions for a in with_executions)
            reliability = sum(
                (a.accuracy or 0) * (a.total_executions or 0) for a in with_executions
            ) / max(total_exec, 1)
        else:
            reliability = 1.0

        # Memory utilization: fraction of agents with meaningful memory
        mem_scores = []
        for a in agents:
            count = a.memory_count or 0
            if count == 0:
                mem_scores.append(0.0)
            elif count < self.UNDERUSED_MEMORY_THRESHOLD:
                mem_scores.append(0.5)
            else:
                mem_scores.append(1.0)
        memory_util = sum(mem_scores) / max(len(mem_scores), 1)

        # Cost efficiency: inverse of cost variance (lower variance = better)
        costs = [(a.total_cost_usd or 0) for a in with_executions]
        if len(costs) > 1:
            avg_cost = sum(costs) / len(costs)
            if avg_cost > 0:
                variance = sum((c - avg_cost) ** 2 for c in costs) / len(costs)
                std_ratio = (variance**0.5) / avg_cost
                cost_eff = max(0, 1.0 - min(std_ratio, 1.0))
            else:
                cost_eff = 1.0
        else:
            cost_eff = 1.0

        overall = reliability * 0.5 + memory_util * 0.25 + cost_eff * 0.25

        return {
            "overall": round(overall, 3),
            "agent_reliability": round(reliability, 3),
            "memory_utilization": round(memory_util, 3),
            "cost_efficiency": round(cost_eff, 3),
            "active_agents": active,
            "total_agents": total,
            "details": {
                "total_executions": sum(a.total_executions or 0 for a in agents),
                "total_cost_usd": round(sum(a.total_cost_usd or 0 for a in agents), 4),
                "total_tokens": sum(a.total_tokens_used or 0 for a in agents),
                "total_time_saved_minutes": round(
                    sum(a.time_saved_minutes or 0 for a in agents), 1
                ),
                "total_corrections": sum(a.total_corrections or 0 for a in agents),
            },
        }

    async def get_recommendations(self, db: AsyncSession) -> list[dict]:
        """Generate actionable recommendations."""
        agents = await self._load_agents(db)
        recs: list[dict] = []

        for agent in agents:
            execs = agent.total_executions or 0
            if execs == 0:
                continue

            failure_rate = (agent.failed_executions or 0) / execs
            accuracy = agent.accuracy or 0

            # Trust level adjustments
            if execs >= 20 and accuracy >= 0.95 and agent.trust_level < 3:
                recs.append(
                    {
                        "type": "promote",
                        "agent_id": str(agent.id),
                        "agent_name": agent.name,
                        "title": f"Promote {agent.name} to {['Apprentice', 'Associate', 'Autonomous'][min(agent.trust_level, 2)]}",
                        "reason": f"Accuracy of {accuracy * 100:.0f}% across {execs} executions warrants higher trust.",
                        "priority": "high",
                    }
                )
            elif failure_rate > 0.5 and agent.trust_level > 0:
                recs.append(
                    {
                        "type": "demote",
                        "agent_id": str(agent.id),
                        "agent_name": agent.name,
                        "title": f"Demote {agent.name} — high failure rate",
                        "reason": f"Failure rate of {failure_rate * 100:.0f}% suggests the agent needs more oversight.",
                        "priority": "critical",
                    }
                )

            # Memory suggestions
            if execs >= 10 and (agent.memory_count or 0) < 3:
                recs.append(
                    {
                        "type": "optimize",
                        "agent_id": str(agent.id),
                        "agent_name": agent.name,
                        "title": f"Add memories for {agent.name}",
                        "reason": f"Agent has {execs} executions but only {agent.memory_count or 0} memories. Adding corrections or procedures could improve accuracy.",
                        "priority": "medium",
                    }
                )

        # Detect potential merge candidates (agents with same trigger type)
        trigger_groups: dict[str, list] = {}
        for agent in agents:
            tt = agent.trigger_type or "manual"
            trigger_groups.setdefault(tt, []).append(agent)

        for trigger_type, group in trigger_groups.items():
            if len(group) >= 3:
                names = ", ".join(a.name for a in group[:3])
                recs.append(
                    {
                        "type": "merge",
                        "title": f"Consider consolidating {trigger_type} agents",
                        "reason": f"{len(group)} agents share the '{trigger_type}' trigger ({names}{'...' if len(group) > 3 else ''}). Merging similar agents could reduce costs.",
                        "priority": "low",
                    }
                )

        return recs

    # --- Backward-compatible stubs ---

    async def detect_anomalies(self, agent_id: str | None = None) -> list:
        return []

    async def detect_trends(self, agent_id: str | None = None) -> list:
        return []

    # --- Private helpers ---

    async def _load_agents(self, db: AsyncSession) -> list[Agent]:
        result = await db.execute(select(Agent).where(Agent.is_active.is_(True)))
        return list(result.scalars().all())

    def _detect_high_failure_agents(self, agents: list[Agent]) -> list[dict]:
        insights = []
        for agent in agents:
            execs = agent.total_executions or 0
            if execs < 5:
                continue
            failure_rate = (agent.failed_executions or 0) / execs
            if failure_rate > self.FAILURE_THRESHOLD:
                insights.append(
                    self._make_insight(
                        "critical" if failure_rate > 0.5 else "warning",
                        "anomaly",
                        f"{agent.name} has high failure rate ({failure_rate * 100:.0f}%)",
                        f"{agent.failed_executions} of {execs} executions failed. Review recent errors and add corrections.",
                        agent_id=str(agent.id),
                        suggested_action="Review failed executions and add correction memories.",
                        data={
                            "failure_rate": round(failure_rate, 3),
                            "failed": agent.failed_executions,
                            "total": execs,
                        },
                    )
                )
        return insights

    def _detect_low_accuracy_agents(self, agents: list[Agent]) -> list[dict]:
        insights = []
        for agent in agents:
            if (agent.total_executions or 0) < 10:
                continue
            if (agent.accuracy or 0) < self.LOW_ACCURACY_THRESHOLD:
                insights.append(
                    self._make_insight(
                        "warning",
                        "anomaly",
                        f"{agent.name} accuracy below threshold ({agent.accuracy * 100:.0f}%)",
                        f"Accuracy has dropped below {self.LOW_ACCURACY_THRESHOLD * 100:.0f}%. Consider adding correction memories or adjusting configuration.",
                        agent_id=str(agent.id),
                        suggested_action="Add correction memories from recent failures.",
                        data={"accuracy": round(agent.accuracy or 0, 3)},
                    )
                )
        return insights

    def _detect_duplicate_work(self, agents: list[Agent]) -> list[dict]:
        """Find agents with identical descriptions that may be doing duplicate work."""
        desc_groups: dict[str, list[str]] = {}
        for agent in agents:
            key = (agent.description or "").strip().lower()[:100]
            if key:
                desc_groups.setdefault(key, []).append(agent.name)

        insights = []
        for desc, names in desc_groups.items():
            if len(names) >= 2:
                insights.append(
                    self._make_insight(
                        "info",
                        "optimization",
                        f"Potential duplicate agents: {', '.join(names[:3])}",
                        f"{len(names)} agents have very similar descriptions. Consider merging to reduce costs.",
                        suggested_action="Review and merge duplicate agents.",
                        data={"agents": names},
                    )
                )
        return insights

    def _detect_cost_outliers(self, agents: list[Agent]) -> list[dict]:
        costs = [
            (a, a.total_cost_usd or 0) for a in agents if (a.total_executions or 0) > 0
        ]
        if len(costs) < 2:
            return []

        avg_cost = sum(c for _, c in costs) / len(costs)
        if avg_cost <= 0:
            return []

        insights = []
        for agent, cost in costs:
            if cost > avg_cost * self.HIGH_COST_MULTIPLIER:
                insights.append(
                    self._make_insight(
                        "warning",
                        "optimization",
                        f"{agent.name} cost is {cost / avg_cost:.1f}x above average",
                        f"Total cost ${cost:.4f} vs platform average ${avg_cost:.4f}. Consider optimizing reasoning tier or reducing token usage.",
                        agent_id=str(agent.id),
                        suggested_action="Review reasoning tier settings and consider using a cheaper model.",
                        data={"cost": round(cost, 4), "avg_cost": round(avg_cost, 4)},
                    )
                )
        return insights

    def _detect_underused_memory(self, agents: list[Agent]) -> list[dict]:
        insights = []
        for agent in agents:
            if (agent.total_executions or 0) >= 10 and (
                agent.memory_count or 0
            ) < self.UNDERUSED_MEMORY_THRESHOLD:
                insights.append(
                    self._make_insight(
                        "info",
                        "suggestion",
                        f"{agent.name} has few memories ({agent.memory_count or 0})",
                        f"Agent has executed {agent.total_executions} times but only has {agent.memory_count or 0} memories. Building memory improves performance.",
                        agent_id=str(agent.id),
                        suggested_action="Enable automatic memory creation or add manual memories.",
                    )
                )
        return insights

    @staticmethod
    def _make_insight(
        severity: str,
        insight_type: str,
        title: str,
        description: str,
        agent_id: str | None = None,
        suggested_action: str | None = None,
        data: dict | None = None,
    ) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "severity": severity,
            "type": insight_type,
            "title": title,
            "description": description,
            "agent_id": agent_id,
            "suggested_action": suggested_action,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
