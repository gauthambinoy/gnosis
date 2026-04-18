"""Voice Input Transcription — handle transcribed voice commands with intent detection."""

from dataclasses import dataclass, field, asdict
from typing import Dict, List
from datetime import datetime, timezone
import uuid


INTENT_KEYWORDS = {
    "execute": ["run", "execute", "start", "launch", "trigger"],
    "search": ["search", "find", "look", "query", "locate"],
    "navigate": ["go", "open", "navigate", "show", "view"],
    "create": ["create", "new", "add", "make", "build"],
}


@dataclass
class VoiceCommand:
    id: str
    user_id: str
    transcript: str
    confidence: float
    intent: str  # execute / search / navigate / create
    parsed_action: dict = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class VoiceInputEngine:
    def __init__(self):
        self._commands: Dict[str, VoiceCommand] = {}

    def parse_intent(
        self, transcript: str, user_id: str, confidence: float = 1.0
    ) -> VoiceCommand:
        words = transcript.lower().split()
        detected_intent = "execute"  # default
        for intent, keywords in INTENT_KEYWORDS.items():
            if any(kw in words for kw in keywords):
                detected_intent = intent
                break
        parsed_action = {
            "raw": transcript,
            "intent": detected_intent,
            "tokens": words,
        }
        cmd = VoiceCommand(
            id=str(uuid.uuid4()),
            user_id=user_id,
            transcript=transcript,
            confidence=confidence,
            intent=detected_intent,
            parsed_action=parsed_action,
        )
        self._commands[cmd.id] = cmd
        return cmd

    def history(self, user_id: str) -> List[dict]:
        return [asdict(c) for c in self._commands.values() if c.user_id == user_id]


voice_engine = VoiceInputEngine()
