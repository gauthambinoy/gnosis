"""Gnosis Cost Tracker — tracks token usage and costs per user/agent."""

from datetime import datetime, date, timezone
from dataclasses import dataclass


@dataclass
class UsageRecord:
    timestamp: str
    agent_id: str
    tier: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cached: bool = False


class CostTracker:
    """Tracks LLM token usage and costs."""

    def __init__(self):
        self._records: list[UsageRecord] = []
        self._daily_totals: dict[str, dict] = {}  # date_str -> {tokens, cost, requests}

    def record(
        self,
        agent_id: str,
        tier: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        cached: bool = False,
    ):
        record = UsageRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_id=agent_id,
            tier=tier,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            cached=cached,
        )
        self._records.append(record)

        # Update daily totals
        today = date.today().isoformat()
        if today not in self._daily_totals:
            self._daily_totals[today] = {
                "tokens": 0,
                "cost": 0.0,
                "requests": 0,
                "cached": 0,
            }
        self._daily_totals[today]["tokens"] += input_tokens + output_tokens
        self._daily_totals[today]["cost"] += cost_usd
        self._daily_totals[today]["requests"] += 1
        if cached:
            self._daily_totals[today]["cached"] += 1

    @property
    def today_stats(self) -> dict:
        today = date.today().isoformat()
        return self._daily_totals.get(
            today, {"tokens": 0, "cost": 0.0, "requests": 0, "cached": 0}
        )

    @property
    def total_stats(self) -> dict:
        total_tokens = sum(r.input_tokens + r.output_tokens for r in self._records)
        total_cost = sum(r.cost_usd for r in self._records)
        cached_count = sum(1 for r in self._records if r.cached)
        return {
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "total_requests": len(self._records),
            "cached_requests": cached_count,
            "cache_rate": cached_count / len(self._records) if self._records else 0,
        }

    def agent_stats(self, agent_id: str) -> dict:
        agent_records = [r for r in self._records if r.agent_id == agent_id]
        return {
            "tokens": sum(r.input_tokens + r.output_tokens for r in agent_records),
            "cost_usd": round(sum(r.cost_usd for r in agent_records), 6),
            "requests": len(agent_records),
            "by_tier": self._group_by_tier(agent_records),
        }

    def _group_by_tier(self, records: list[UsageRecord]) -> dict:
        tiers: dict[str, dict] = {}
        for r in records:
            if r.tier not in tiers:
                tiers[r.tier] = {"tokens": 0, "cost": 0.0, "requests": 0}
            tiers[r.tier]["tokens"] += r.input_tokens + r.output_tokens
            tiers[r.tier]["cost"] += r.cost_usd
            tiers[r.tier]["requests"] += 1
        return tiers

    def recent_records(self, limit: int = 50) -> list[dict]:
        return [
            {
                "timestamp": r.timestamp,
                "agent_id": r.agent_id,
                "tier": r.tier,
                "model": r.model,
                "tokens": r.input_tokens + r.output_tokens,
                "cost_usd": r.cost_usd,
                "cached": r.cached,
            }
            for r in self._records[-limit:]
        ]


# Global singleton
cost_tracker = CostTracker()
