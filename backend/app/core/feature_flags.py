"""Feature flag system for controlled rollouts."""
import uuid, random, logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.flags")

@dataclass
class FeatureFlag:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    enabled: bool = False
    scope: str = "global"  # global, workspace, user
    target_ids: List[str] = field(default_factory=list)
    rollout_pct: float = 100.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class FeatureFlagEngine:
    def __init__(self):
        self._flags: Dict[str, FeatureFlag] = {}

    def create_flag(self, name: str, description: str = "", scope: str = "global", rollout_pct: float = 100.0) -> dict:
        flag = FeatureFlag(name=name, description=description, scope=scope, rollout_pct=rollout_pct, enabled=True)
        self._flags[flag.id] = flag
        return asdict(flag)

    def is_enabled(self, flag_name: str, user_id: str = None, workspace_id: str = None) -> bool:
        flag = next((f for f in self._flags.values() if f.name == flag_name), None)
        if not flag or not flag.enabled:
            return False
        if flag.scope == "user" and user_id and flag.target_ids and user_id not in flag.target_ids:
            return False
        if flag.scope == "workspace" and workspace_id and flag.target_ids and workspace_id not in flag.target_ids:
            return False
        if flag.rollout_pct < 100:
            return random.random() * 100 < flag.rollout_pct
        return True

    def update_flag(self, flag_id: str, **kwargs) -> dict:
        flag = self._flags.get(flag_id)
        if not flag:
            return {"error": "Flag not found"}
        for k, v in kwargs.items():
            if hasattr(flag, k):
                setattr(flag, k, v)
        return asdict(flag)

    def list_flags(self) -> List[dict]:
        return [asdict(f) for f in self._flags.values()]

feature_flag_engine = FeatureFlagEngine()
