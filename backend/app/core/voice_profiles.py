"""Gnosis Voice & Tone Profiles — Manage agent voice and tone settings."""

import uuid
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

logger = logging.getLogger("gnosis.voice_profiles")


@dataclass
class VoiceProfile:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    tone: str = "friendly"  # formal/casual/technical/friendly
    vocabulary_level: str = "intermediate"  # simple/intermediate/advanced
    response_style: str = "balanced"  # concise/detailed/balanced
    example_phrases: List[str] = field(default_factory=list)
    agent_id: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class VoiceProfileEngine:
    VALID_TONES = {"formal", "casual", "technical", "friendly"}
    VALID_VOCAB = {"simple", "intermediate", "advanced"}
    VALID_STYLES = {"concise", "detailed", "balanced"}

    def __init__(self):
        self._profiles: Dict[str, VoiceProfile] = {}
        self._agent_map: Dict[str, str] = {}  # agent_id -> profile_id

    def create_profile(
        self,
        name: str,
        tone: str = "friendly",
        vocabulary_level: str = "intermediate",
        response_style: str = "balanced",
        example_phrases: List[str] = None,
    ) -> VoiceProfile:
        if tone not in self.VALID_TONES:
            raise ValueError(f"Invalid tone: {tone}. Must be one of {self.VALID_TONES}")
        if vocabulary_level not in self.VALID_VOCAB:
            raise ValueError(f"Invalid vocabulary_level: {vocabulary_level}")
        if response_style not in self.VALID_STYLES:
            raise ValueError(f"Invalid response_style: {response_style}")
        profile = VoiceProfile(
            name=name,
            tone=tone,
            vocabulary_level=vocabulary_level,
            response_style=response_style,
            example_phrases=example_phrases or [],
        )
        self._profiles[profile.id] = profile
        logger.info(f"Created voice profile: {profile.id} ({name})")
        return profile

    def get_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        return self._profiles.get(profile_id)

    def list_profiles(self) -> List[dict]:
        return [asdict(p) for p in self._profiles.values()]

    def update_profile(self, profile_id: str, **kwargs) -> Optional[VoiceProfile]:
        profile = self._profiles.get(profile_id)
        if not profile:
            return None
        for k, v in kwargs.items():
            if hasattr(profile, k) and k not in ("id", "created_at"):
                setattr(profile, k, v)
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        if profile_id in self._profiles:
            del self._profiles[profile_id]
            self._agent_map = {
                a: p for a, p in self._agent_map.items() if p != profile_id
            }
            return True
        return False

    def assign_to_agent(self, profile_id: str, agent_id: str) -> bool:
        if profile_id not in self._profiles:
            return False
        self._agent_map[agent_id] = profile_id
        self._profiles[profile_id].agent_id = agent_id
        logger.info(f"Assigned profile {profile_id} to agent {agent_id}")
        return True

    def get_profile_for_agent(self, agent_id: str) -> Optional[VoiceProfile]:
        pid = self._agent_map.get(agent_id)
        return self._profiles.get(pid) if pid else None


voice_profile_engine = VoiceProfileEngine()
