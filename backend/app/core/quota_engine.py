"""Gnosis Quota Engine — Per-workspace resource limits enforcement."""
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.quotas")

@dataclass
class QuotaLimits:
    max_agents: int = 10
    max_executions_per_day: int = 100
    max_storage_mb: int = 500
    max_tokens_per_day: int = 1_000_000
    max_pipelines: int = 5
    max_file_uploads: int = 100

@dataclass
class QuotaUsage:
    agents: int = 0
    executions_today: int = 0
    storage_mb: float = 0.0
    tokens_today: int = 0
    pipelines: int = 0
    file_uploads: int = 0
    last_reset: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

TIER_LIMITS = {
    "free": QuotaLimits(max_agents=3, max_executions_per_day=20, max_storage_mb=100, max_tokens_per_day=100_000, max_pipelines=2, max_file_uploads=20),
    "pro": QuotaLimits(max_agents=25, max_executions_per_day=500, max_storage_mb=2000, max_tokens_per_day=5_000_000, max_pipelines=20, max_file_uploads=500),
    "enterprise": QuotaLimits(max_agents=999, max_executions_per_day=10000, max_storage_mb=50000, max_tokens_per_day=100_000_000, max_pipelines=999, max_file_uploads=10000),
}

class QuotaEngine:
    def __init__(self):
        self._workspace_tiers: Dict[str, str] = {}  # workspace_id -> tier
        self._usage: Dict[str, QuotaUsage] = {}  # workspace_id -> usage
        self._custom_limits: Dict[str, QuotaLimits] = {}  # workspace_id -> custom overrides

    def set_tier(self, workspace_id: str, tier: str):
        if tier not in TIER_LIMITS:
            raise ValueError(f"Invalid tier: {tier}. Must be one of: {list(TIER_LIMITS.keys())}")
        self._workspace_tiers[workspace_id] = tier
        logger.info(f"Workspace {workspace_id} set to tier: {tier}")

    def get_limits(self, workspace_id: str) -> QuotaLimits:
        if workspace_id in self._custom_limits:
            return self._custom_limits[workspace_id]
        tier = self._workspace_tiers.get(workspace_id, "free")
        return TIER_LIMITS[tier]

    def get_usage(self, workspace_id: str) -> QuotaUsage:
        if workspace_id not in self._usage:
            self._usage[workspace_id] = QuotaUsage()
        return self._usage[workspace_id]

    def check_quota(self, workspace_id: str, resource: str, amount: int = 1) -> dict:
        """Check if a resource action would exceed quota. Returns {"allowed": bool, "remaining": int, ...}."""
        limits = self.get_limits(workspace_id)
        usage = self.get_usage(workspace_id)
        
        checks = {
            "agents": (usage.agents + amount, limits.max_agents),
            "executions": (usage.executions_today + amount, limits.max_executions_per_day),
            "storage_mb": (usage.storage_mb + amount, limits.max_storage_mb),
            "tokens": (usage.tokens_today + amount, limits.max_tokens_per_day),
            "pipelines": (usage.pipelines + amount, limits.max_pipelines),
            "file_uploads": (usage.file_uploads + amount, limits.max_file_uploads),
        }
        
        if resource not in checks:
            return {"allowed": True, "remaining": 999, "resource": resource}
        
        new_val, limit = checks[resource]
        allowed = new_val <= limit
        remaining = max(0, limit - (new_val - amount))
        
        if not allowed:
            logger.warning(f"Quota exceeded: workspace={workspace_id}, resource={resource}, usage={new_val-amount}, limit={limit}")
        
        return {
            "allowed": allowed,
            "resource": resource,
            "current": new_val - amount,
            "limit": limit,
            "remaining": remaining,
        }

    def record_usage(self, workspace_id: str, resource: str, amount: int = 1):
        usage = self.get_usage(workspace_id)
        if resource == "agents":
            usage.agents += amount
        elif resource == "executions":
            usage.executions_today += amount
        elif resource == "storage_mb":
            usage.storage_mb += amount
        elif resource == "tokens":
            usage.tokens_today += amount
        elif resource == "pipelines":
            usage.pipelines += amount
        elif resource == "file_uploads":
            usage.file_uploads += amount

    def reset_daily_counters(self):
        now = datetime.now(timezone.utc).isoformat()
        for ws_id, usage in self._usage.items():
            usage.executions_today = 0
            usage.tokens_today = 0
            usage.last_reset = now
        logger.info(f"Daily quota counters reset for {len(self._usage)} workspaces")

    def get_dashboard(self, workspace_id: str) -> dict:
        limits = self.get_limits(workspace_id)
        usage = self.get_usage(workspace_id)
        tier = self._workspace_tiers.get(workspace_id, "free")
        return {
            "workspace_id": workspace_id,
            "tier": tier,
            "limits": limits.__dict__,
            "usage": usage.__dict__,
            "percentages": {
                "agents": round(usage.agents / max(limits.max_agents, 1) * 100, 1),
                "executions": round(usage.executions_today / max(limits.max_executions_per_day, 1) * 100, 1),
                "storage": round(usage.storage_mb / max(limits.max_storage_mb, 1) * 100, 1),
                "tokens": round(usage.tokens_today / max(limits.max_tokens_per_day, 1) * 100, 1),
            },
        }

quota_engine = QuotaEngine()
