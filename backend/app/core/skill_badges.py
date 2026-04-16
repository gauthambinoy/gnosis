"""Gnosis Skill Badges — Award and track agent skill achievements."""
import uuid
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger("gnosis.badges")


@dataclass
class SkillBadge:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    icon: str = "🏅"
    description: str = ""
    criteria: dict = field(default_factory=dict)
    level: str = "bronze"  # bronze/silver/gold/platinum


PRESET_BADGES = [
    SkillBadge(id="badge-speed-demon", name="Speed Demon", icon="⚡", description="Completes tasks in under 2 seconds",
               criteria={"avg_response_time_ms": 2000}, level="gold"),
    SkillBadge(id="badge-reliable", name="Reliable Responder", icon="🎯", description="99%+ success rate over 100 executions",
               criteria={"success_rate": 0.99, "min_executions": 100}, level="platinum"),
    SkillBadge(id="badge-polyglot", name="Polyglot", icon="🌍", description="Handles 5+ languages",
               criteria={"languages_supported": 5}, level="silver"),
    SkillBadge(id="badge-first-run", name="First Steps", icon="👣", description="Completed first execution",
               criteria={"total_executions": 1}, level="bronze"),
    SkillBadge(id="badge-marathon", name="Marathon Runner", icon="🏃", description="1000+ executions completed",
               criteria={"total_executions": 1000}, level="gold"),
]


class SkillBadgeEngine:
    VALID_LEVELS = {"bronze", "silver", "gold", "platinum"}

    def __init__(self):
        self._badges: Dict[str, SkillBadge] = {b.id: b for b in PRESET_BADGES}
        self._agent_badges: Dict[str, List[str]] = defaultdict(list)  # agent_id -> [badge_id]
        self._awarded_at: Dict[str, str] = {}  # "agent_id:badge_id" -> timestamp

    def create_badge(self, name: str, icon: str = "🏅", description: str = "",
                     criteria: dict = None, level: str = "bronze") -> SkillBadge:
        if level not in self.VALID_LEVELS:
            raise ValueError(f"Invalid level: {level}. Must be one of {self.VALID_LEVELS}")
        badge = SkillBadge(name=name, icon=icon, description=description,
                           criteria=criteria or {}, level=level)
        self._badges[badge.id] = badge
        logger.info(f"Created badge: {badge.id} ({name})")
        return badge

    def get_badge(self, badge_id: str) -> Optional[SkillBadge]:
        return self._badges.get(badge_id)

    def list_badges(self) -> List[dict]:
        return [asdict(b) for b in self._badges.values()]

    def award_badge(self, agent_id: str, badge_id: str) -> bool:
        if badge_id not in self._badges:
            return False
        key = f"{agent_id}:{badge_id}"
        if key in self._awarded_at:
            return False  # already awarded
        self._agent_badges[agent_id].append(badge_id)
        self._awarded_at[key] = datetime.now(timezone.utc).isoformat()
        logger.info(f"Awarded badge {badge_id} to agent {agent_id}")
        return True

    def check_eligibility(self, agent_id: str, badge_id: str, agent_stats: dict = None) -> bool:
        badge = self._badges.get(badge_id)
        if not badge:
            return False
        stats = agent_stats or {}
        for criterion, threshold in badge.criteria.items():
            if stats.get(criterion, 0) < threshold:
                return False
        return True

    def list_agent_badges(self, agent_id: str) -> List[dict]:
        badge_ids = self._agent_badges.get(agent_id, [])
        result = []
        for bid in badge_ids:
            badge = self._badges.get(bid)
            if badge:
                d = asdict(badge)
                d["awarded_at"] = self._awarded_at.get(f"{agent_id}:{bid}", "")
                result.append(d)
        return result


skill_badge_engine = SkillBadgeEngine()
