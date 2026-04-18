"""Feature flag system for controlled rollouts."""
import asyncio
import logging
import random
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List

from app.core.engine_state_store import load_states, upsert_state

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
        self._loaded = False
        self._load_lock = asyncio.Lock()

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        async with self._load_lock:
            if self._loaded:
                return
            for row in await load_states("feature_flags"):
                data = row.state_json or {}
                flag = FeatureFlag(**data)
                self._flags[row.entity_id] = flag
            self._loaded = True

    async def create_flag(self, name: str, description: str = "", scope: str = "global", rollout_pct: float = 100.0) -> dict:
        await self._ensure_loaded()
        flag = FeatureFlag(name=name, description=description, scope=scope, rollout_pct=rollout_pct, enabled=True)
        self._flags[flag.id] = flag
        await upsert_state("feature_flags", flag.id, asdict(flag), group_id=flag.name, state_type=flag.scope, is_active=flag.enabled)
        return asdict(flag)

    async def is_enabled(self, flag_name: str, user_id: str = None, workspace_id: str = None) -> bool:
        await self._ensure_loaded()
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

    async def update_flag(self, flag_id: str, **kwargs) -> dict:
        await self._ensure_loaded()
        flag = self._flags.get(flag_id)
        if not flag:
            return {"error": "Flag not found"}
        for k, v in kwargs.items():
            if hasattr(flag, k):
                setattr(flag, k, v)
        await upsert_state("feature_flags", flag_id, asdict(flag), group_id=flag.name, state_type=flag.scope, is_active=flag.enabled)
        return asdict(flag)

    async def list_flags(self) -> List[dict]:
        await self._ensure_loaded()
        return [asdict(f) for f in self._flags.values()]

feature_flag_engine = FeatureFlagEngine()
