"""Gnosis Emotion Engine — Detect and track emotional signals in conversations."""
import uuid
import logging
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger("gnosis.emotion")

EMOTION_KEYWORDS = {
    "frustrated": ["frustrated", "annoying", "angry", "terrible", "horrible", "hate", "worst", "broken", "useless", "awful"],
    "confused": ["confused", "unclear", "don't understand", "what do you mean", "lost", "how does", "doesn't make sense", "help me"],
    "satisfied": ["thanks", "great", "perfect", "excellent", "awesome", "love it", "works", "solved", "helpful", "amazing"],
    "curious": ["how", "why", "what if", "wonder", "curious", "interesting", "tell me more", "explain", "possible"],
}


@dataclass
class EmotionSignal:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    detected_emotion: str = "neutral"  # neutral/frustrated/confused/satisfied/curious
    confidence: float = 0.0
    context: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EmotionEngine:
    def __init__(self):
        self._history: Dict[str, List[EmotionSignal]] = defaultdict(list)

    def analyze_text(self, text: str, agent_id: str = "") -> EmotionSignal:
        text_lower = text.lower()
        scores: Dict[str, int] = {}
        for emotion, keywords in EMOTION_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > 0:
                scores[emotion] = count
        if not scores:
            signal = EmotionSignal(agent_id=agent_id, detected_emotion="neutral", confidence=0.5,
                                   context=text[:200])
        else:
            best = max(scores, key=scores.get)
            confidence = min(0.95, 0.4 + scores[best] * 0.15)
            signal = EmotionSignal(agent_id=agent_id, detected_emotion=best, confidence=round(confidence, 2),
                                   context=text[:200])
        if agent_id:
            self._history[agent_id].append(signal)
        logger.info(f"Emotion detected: {signal.detected_emotion} (conf={signal.confidence}) for agent {agent_id}")
        return signal

    def get_emotion_history(self, agent_id: str, limit: int = 50) -> List[dict]:
        signals = self._history.get(agent_id, [])
        return [asdict(s) for s in signals[-limit:]]

    def clear_history(self, agent_id: str) -> bool:
        if agent_id in self._history:
            self._history[agent_id].clear()
            return True
        return False


emotion_engine = EmotionEngine()
