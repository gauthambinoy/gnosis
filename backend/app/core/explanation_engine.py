"""Agent Explanation Mode — break agent responses into reasoning steps."""
from dataclasses import dataclass, field, asdict
from typing import Dict, List
from datetime import datetime, timezone
import uuid


@dataclass
class Explanation:
    id: str
    execution_id: str
    steps: List[dict] = field(default_factory=list)  # [{step, reasoning, confidence}]
    summary: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExplanationEngine:
    def __init__(self):
        self._explanations: Dict[str, Explanation] = {}

    def generate_explanation(self, execution_id: str, response_text: str) -> Explanation:
        sentences = [s.strip() for s in response_text.split(".") if s.strip()]
        steps = []
        for i, sentence in enumerate(sentences):
            confidence = round(max(0.5, 1.0 - i * 0.05), 2)
            steps.append({
                "step": i + 1,
                "reasoning": sentence,
                "confidence": confidence,
            })
        summary = sentences[0] if sentences else "No reasoning available"
        explanation = Explanation(
            id=str(uuid.uuid4()),
            execution_id=execution_id,
            steps=steps,
            summary=summary,
        )
        self._explanations[explanation.id] = explanation
        return explanation

    def get_explanation(self, execution_id: str) -> List[dict]:
        return [
            asdict(e)
            for e in self._explanations.values()
            if e.execution_id == execution_id
        ]


explanation_engine = ExplanationEngine()
