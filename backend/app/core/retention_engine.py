"""Gnosis Data Retention — Per-workspace retention policies with auto-purge."""
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("gnosis.retention")

@dataclass
class RetentionPolicy:
    workspace_id: str
    execution_days: int = 90      # Keep executions for N days
    memory_days: int = 365        # Keep memories for N days
    audit_days: int = 730         # Keep audit logs for 2 years
    file_days: int = 180          # Keep uploaded files for N days
    activity_days: int = 90       # Keep activity feed for N days
    auto_purge: bool = False      # Enable automatic purging
    archive_before_purge: bool = True  # Archive data before deletion
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class PurgeResult:
    workspace_id: str
    executions_purged: int = 0
    memories_purged: int = 0
    files_purged: int = 0
    activities_purged: int = 0
    archived: bool = False
    purged_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class RetentionEngine:
    def __init__(self):
        self._policies: Dict[str, RetentionPolicy] = {}
        self._purge_history: List[PurgeResult] = []

    def set_policy(self, workspace_id: str, **kwargs) -> RetentionPolicy:
        if workspace_id in self._policies:
            policy = self._policies[workspace_id]
            for key, value in kwargs.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)
            policy.updated_at = datetime.now(timezone.utc).isoformat()
        else:
            policy = RetentionPolicy(workspace_id=workspace_id, **kwargs)
            self._policies[workspace_id] = policy
        logger.info(f"Retention policy set for workspace {workspace_id}")
        return policy

    def get_policy(self, workspace_id: str) -> RetentionPolicy:
        return self._policies.get(workspace_id, RetentionPolicy(workspace_id=workspace_id))

    def calculate_expiry(self, workspace_id: str) -> dict:
        policy = self.get_policy(workspace_id)
        now = datetime.now(timezone.utc)
        return {
            "executions_expire_before": (now - timedelta(days=policy.execution_days)).isoformat(),
            "memories_expire_before": (now - timedelta(days=policy.memory_days)).isoformat(),
            "audit_expire_before": (now - timedelta(days=policy.audit_days)).isoformat(),
            "files_expire_before": (now - timedelta(days=policy.file_days)).isoformat(),
            "activities_expire_before": (now - timedelta(days=policy.activity_days)).isoformat(),
        }

    def simulate_purge(self, workspace_id: str) -> dict:
        """Dry-run purge to show what would be deleted."""
        expiry = self.calculate_expiry(workspace_id)
        return {
            "workspace_id": workspace_id,
            "dry_run": True,
            "would_expire": expiry,
            "note": "Run POST /purge to execute",
        }

    def list_policies(self) -> List[dict]:
        return [asdict(p) for p in self._policies.values()]

    def get_purge_history(self, workspace_id: str = None) -> List[dict]:
        history = self._purge_history
        if workspace_id:
            history = [h for h in history if h.workspace_id == workspace_id]
        return [asdict(h) for h in history]

retention_engine = RetentionEngine()
