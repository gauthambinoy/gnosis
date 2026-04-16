"""Gnosis Environment Promotion — Promote agent configs between environments."""
import uuid, logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

logger = logging.getLogger("gnosis.env_promotion")


@dataclass
class PromotionRecord:
    id: str
    agent_id: str
    from_env: str
    to_env: str
    config_snapshot: dict
    promoted_by: str
    status: str = "pending"  # pending/approved/deployed/rolled_back
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EnvPromotionEngine:
    def __init__(self):
        self._promotions: Dict[str, PromotionRecord] = {}

    def promote(self, agent_id: str, from_env: str, to_env: str, config_snapshot: dict, promoted_by: str) -> PromotionRecord:
        valid_envs = ["dev", "staging", "production"]
        if from_env not in valid_envs or to_env not in valid_envs:
            raise ValueError(f"Invalid environment. Must be one of {valid_envs}")
        if valid_envs.index(to_env) <= valid_envs.index(from_env):
            raise ValueError("Can only promote to a higher environment")
        record = PromotionRecord(
            id=uuid.uuid4().hex[:12],
            agent_id=agent_id,
            from_env=from_env,
            to_env=to_env,
            config_snapshot=config_snapshot,
            promoted_by=promoted_by,
        )
        self._promotions[record.id] = record
        logger.info(f"Promotion {record.id}: {agent_id} {from_env} -> {to_env}")
        return record

    def approve_promotion(self, promotion_id: str) -> PromotionRecord:
        record = self._promotions.get(promotion_id)
        if not record:
            raise KeyError("Promotion not found")
        if record.status != "pending":
            raise ValueError(f"Cannot approve promotion in status: {record.status}")
        record.status = "approved"
        logger.info(f"Promotion {promotion_id} approved")
        return record

    def deploy_promotion(self, promotion_id: str) -> PromotionRecord:
        record = self._promotions.get(promotion_id)
        if not record:
            raise KeyError("Promotion not found")
        if record.status != "approved":
            raise ValueError(f"Cannot deploy promotion in status: {record.status}")
        record.status = "deployed"
        logger.info(f"Promotion {promotion_id} deployed")
        return record

    def rollback(self, promotion_id: str) -> PromotionRecord:
        record = self._promotions.get(promotion_id)
        if not record:
            raise KeyError("Promotion not found")
        if record.status not in ("approved", "deployed"):
            raise ValueError(f"Cannot rollback promotion in status: {record.status}")
        record.status = "rolled_back"
        logger.info(f"Promotion {promotion_id} rolled back")
        return record

    def list_promotions(self, agent_id: Optional[str] = None) -> List[PromotionRecord]:
        records = list(self._promotions.values())
        if agent_id:
            records = [r for r in records if r.agent_id == agent_id]
        return sorted(records, key=lambda r: r.created_at, reverse=True)


env_promotion_engine = EnvPromotionEngine()
