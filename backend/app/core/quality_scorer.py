"""Gnosis Quality Scorer — Score LLM responses on relevance, coherence, completeness."""
import uuid
import logging
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List
from collections import defaultdict

logger = logging.getLogger("gnosis.quality_scorer")


@dataclass
class QualityScore:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = ""
    relevance: float = 0.0  # 0-1
    coherence: float = 0.0  # 0-1
    completeness: float = 0.0  # 0-1
    overall: float = 0.0  # 0-1
    feedback: str = ""
    scored_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class QualityScorerEngine:
    def __init__(self):
        self._scores: Dict[str, List[QualityScore]] = defaultdict(list)

    def _score_relevance(self, prompt: str, response: str) -> float:
        prompt_words = set(re.findall(r'\b\w{3,}\b', prompt.lower()))
        response_words = set(re.findall(r'\b\w{3,}\b', response.lower()))
        if not prompt_words:
            return 0.5
        overlap = len(prompt_words & response_words)
        return min(1.0, round(overlap / max(1, len(prompt_words)) * 1.5, 2))

    def _score_coherence(self, response: str) -> float:
        sentences = re.split(r'[.!?]+', response)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) <= 1:
            return 0.7
        score = 0.6
        if len(sentences) >= 2:
            score += 0.1
        if any(w in response.lower() for w in ["first", "second", "then", "next", "finally", "therefore", "however"]):
            score += 0.15
        if not re.search(r'(.{10,})\1', response):
            score += 0.1
        return min(1.0, round(score, 2))

    def _score_completeness(self, prompt: str, response: str) -> float:
        if not response.strip():
            return 0.0
        length_ratio = len(response) / max(1, len(prompt))
        if length_ratio < 0.5:
            base = 0.3
        elif length_ratio < 1.0:
            base = 0.5
        elif length_ratio < 3.0:
            base = 0.7
        else:
            base = 0.8
        question_marks = prompt.count('?')
        if question_marks > 0:
            answer_indicators = sum(1 for w in ["because", "is", "are", "the answer", "result"]
                                    if w in response.lower())
            base += min(0.2, answer_indicators * 0.05)
        return min(1.0, round(base, 2))

    def score_response(self, prompt: str, response: str, execution_id: str = "",
                       agent_id: str = "") -> QualityScore:
        relevance = self._score_relevance(prompt, response)
        coherence = self._score_coherence(response)
        completeness = self._score_completeness(prompt, response)
        overall = round((relevance * 0.4 + coherence * 0.3 + completeness * 0.3), 2)

        feedback_parts = []
        if relevance < 0.5:
            feedback_parts.append("Low relevance: response may not address the prompt")
        if coherence < 0.5:
            feedback_parts.append("Low coherence: response structure could be improved")
        if completeness < 0.5:
            feedback_parts.append("Low completeness: response may be too brief")
        if overall >= 0.7:
            feedback_parts.append("Good overall quality")
        feedback = "; ".join(feedback_parts) if feedback_parts else "Acceptable quality"

        score = QualityScore(
            execution_id=execution_id, relevance=relevance, coherence=coherence,
            completeness=completeness, overall=overall, feedback=feedback,
        )
        if agent_id:
            self._scores[agent_id].append(score)
        logger.info(f"Quality score: overall={overall} (rel={relevance}, coh={coherence}, comp={completeness})")
        return score

    def get_history(self, agent_id: str, limit: int = 50) -> List[dict]:
        scores = self._scores.get(agent_id, [])
        return [asdict(s) for s in scores[-limit:]]


quality_scorer_engine = QualityScorerEngine()
