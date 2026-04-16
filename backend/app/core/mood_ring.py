"""Gnosis Mood Ring — Track agent mood based on recent success/failure rates."""
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional

logger = logging.getLogger("gnosis.mood_ring")


@dataclass
class AgentMood:
    agent_id: str = ""
    mood: str = "idle"  # energized/focused/struggling/recovering/idle
    energy: float = 0.5  # 0-1
    recent_successes: int = 0
    recent_failures: int = 0
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MoodRingEngine:
    MOODS = {"energized", "focused", "struggling", "recovering", "idle"}

    def __init__(self):
        self._moods: Dict[str, AgentMood] = {}

    def _calculate_mood(self, successes: int, failures: int) -> tuple:
        total = successes + failures
        if total == 0:
            return "idle", 0.5
        ratio = successes / total
        if ratio >= 0.9:
            return "energized", min(1.0, 0.7 + ratio * 0.3)
        elif ratio >= 0.7:
            return "focused", 0.5 + ratio * 0.3
        elif ratio >= 0.4:
            return "recovering", 0.3 + ratio * 0.2
        else:
            return "struggling", max(0.0, ratio * 0.5)

    def update_mood(self, agent_id: str, success: bool) -> AgentMood:
        if agent_id not in self._moods:
            self._moods[agent_id] = AgentMood(agent_id=agent_id)
        mood_data = self._moods[agent_id]
        if success:
            mood_data.recent_successes += 1
        else:
            mood_data.recent_failures += 1
        mood_data.mood, mood_data.energy = self._calculate_mood(
            mood_data.recent_successes, mood_data.recent_failures)
        mood_data.energy = round(mood_data.energy, 2)
        mood_data.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Agent {agent_id} mood: {mood_data.mood} (energy={mood_data.energy})")
        return mood_data

    def get_mood(self, agent_id: str) -> AgentMood:
        if agent_id not in self._moods:
            self._moods[agent_id] = AgentMood(agent_id=agent_id)
        return self._moods[agent_id]

    def reset_mood(self, agent_id: str) -> AgentMood:
        self._moods[agent_id] = AgentMood(agent_id=agent_id)
        return self._moods[agent_id]


mood_ring_engine = MoodRingEngine()
