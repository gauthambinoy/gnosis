"""Gnosis Billing — Usage tracking, quotas, and billing management."""
import uuid, logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger("gnosis.billing")


class PlanTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


PLAN_LIMITS = {
    PlanTier.FREE: {"agents": 3, "executions_per_day": 50, "tokens_per_month": 100_000, "file_storage_mb": 100, "team_members": 1},
    PlanTier.STARTER: {"agents": 10, "executions_per_day": 500, "tokens_per_month": 1_000_000, "file_storage_mb": 1000, "team_members": 5},
    PlanTier.PRO: {"agents": 50, "executions_per_day": 5000, "tokens_per_month": 10_000_000, "file_storage_mb": 10000, "team_members": 25},
    PlanTier.ENTERPRISE: {"agents": -1, "executions_per_day": -1, "tokens_per_month": -1, "file_storage_mb": -1, "team_members": -1},  # -1 = unlimited
}

PLAN_PRICES = {
    PlanTier.FREE: 0,
    PlanTier.STARTER: 19,
    PlanTier.PRO: 79,
    PlanTier.ENTERPRISE: 299,
}


@dataclass
class UsageRecord:
    id: str
    user_id: str
    metric: str  # agents_created, executions, tokens_used, storage_used_mb
    value: float
    period: str  # YYYY-MM-DD or YYYY-MM
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Subscription:
    id: str
    user_id: str
    plan: PlanTier = PlanTier.FREE
    status: str = "active"  # active, cancelled, past_due
    current_period_start: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    current_period_end: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BillingEngine:
    def __init__(self):
        self._subscriptions: Dict[str, Subscription] = {}  # user_id -> sub
        self._usage: Dict[str, List[UsageRecord]] = {}  # user_id -> records
        self._daily_counters: Dict[str, Dict[str, float]] = {}  # user_id -> {metric: count}
        self._monthly_counters: Dict[str, Dict[str, float]] = {}

    def get_or_create_subscription(self, user_id: str) -> Subscription:
        if user_id not in self._subscriptions:
            self._subscriptions[user_id] = Subscription(id=str(uuid.uuid4()), user_id=user_id)
        return self._subscriptions[user_id]

    def upgrade_plan(self, user_id: str, plan: PlanTier) -> Subscription:
        sub = self.get_or_create_subscription(user_id)
        old_plan = sub.plan
        sub.plan = plan
        logger.info(f"User {user_id} upgraded from {old_plan} to {plan}")
        return sub

    def record_usage(self, user_id: str, metric: str, value: float = 1):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        month = datetime.now(timezone.utc).strftime("%Y-%m")

        record = UsageRecord(id=str(uuid.uuid4()), user_id=user_id, metric=metric, value=value, period=today)
        self._usage.setdefault(user_id, []).append(record)

        # Update counters
        self._daily_counters.setdefault(user_id, {})
        self._daily_counters[user_id][metric] = self._daily_counters[user_id].get(metric, 0) + value

        self._monthly_counters.setdefault(user_id, {})
        self._monthly_counters[user_id][metric] = self._monthly_counters[user_id].get(metric, 0) + value

    def check_quota(self, user_id: str, metric: str) -> dict:
        sub = self.get_or_create_subscription(user_id)
        limits = PLAN_LIMITS.get(sub.plan, PLAN_LIMITS[PlanTier.FREE])

        metric_map = {
            "executions": ("executions_per_day", self._daily_counters),
            "tokens_used": ("tokens_per_month", self._monthly_counters),
            "agents_created": ("agents", self._monthly_counters),
        }

        if metric not in metric_map:
            return {"allowed": True, "reason": "Unknown metric"}

        limit_key, counter_dict = metric_map[metric]
        limit = limits.get(limit_key, -1)
        current = counter_dict.get(user_id, {}).get(metric, 0)

        if limit == -1:  # Unlimited
            return {"allowed": True, "current": current, "limit": "unlimited"}

        return {
            "allowed": current < limit,
            "current": current,
            "limit": limit,
            "remaining": max(0, limit - current),
            "percentage_used": round((current / limit) * 100, 1) if limit > 0 else 0,
        }

    def get_usage_summary(self, user_id: str) -> dict:
        sub = self.get_or_create_subscription(user_id)
        limits = PLAN_LIMITS.get(sub.plan, PLAN_LIMITS[PlanTier.FREE])
        daily = self._daily_counters.get(user_id, {})
        monthly = self._monthly_counters.get(user_id, {})

        return {
            "plan": sub.plan,
            "price": PLAN_PRICES.get(sub.plan, 0),
            "daily_executions": {"used": daily.get("executions", 0), "limit": limits["executions_per_day"]},
            "monthly_tokens": {"used": monthly.get("tokens_used", 0), "limit": limits["tokens_per_month"]},
            "agents": {"used": monthly.get("agents_created", 0), "limit": limits["agents"]},
            "storage_mb": {"used": monthly.get("storage_used_mb", 0), "limit": limits["file_storage_mb"]},
        }

    def get_plans(self) -> list:
        return [
            {"tier": tier.value, "price": PLAN_PRICES[tier], "limits": PLAN_LIMITS[tier],
             "name": tier.value.title(), "popular": tier == PlanTier.PRO}
            for tier in PlanTier
        ]

    @property
    def stats(self) -> dict:
        plan_counts = {}
        for sub in self._subscriptions.values():
            plan_counts[sub.plan] = plan_counts.get(sub.plan, 0) + 1
        return {"total_subscribers": len(self._subscriptions), "by_plan": plan_counts}


billing_engine = BillingEngine()
