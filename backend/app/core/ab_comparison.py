"""A/B Response Comparison — compare two agent responses side-by-side with scoring."""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid


@dataclass
class ABComparison:
    id: str
    prompt: str
    response_a: str
    response_b: str
    agent_a: str
    agent_b: str
    winner: str = ""
    scores: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ABComparisonEngine:
    def __init__(self):
        self._comparisons: Dict[str, ABComparison] = {}

    def create_comparison(
        self, prompt: str, response_a: str, response_b: str, agent_a: str = "", agent_b: str = ""
    ) -> ABComparison:
        scores = {
            "length_a": len(response_a),
            "length_b": len(response_b),
            "word_count_a": len(response_a.split()),
            "word_count_b": len(response_b.split()),
        }
        comp = ABComparison(
            id=str(uuid.uuid4()),
            prompt=prompt,
            response_a=response_a,
            response_b=response_b,
            agent_a=agent_a,
            agent_b=agent_b,
            scores=scores,
        )
        self._comparisons[comp.id] = comp
        return comp

    def vote(self, comparison_id: str, winner: str) -> ABComparison:
        comp = self._comparisons.get(comparison_id)
        if not comp:
            raise KeyError(f"Comparison {comparison_id} not found")
        if winner not in ("a", "b", "tie"):
            raise ValueError("Winner must be 'a', 'b', or 'tie'")
        comp.winner = winner
        return comp

    def list_comparisons(self) -> List[dict]:
        return [asdict(c) for c in self._comparisons.values()]


ab_engine = ABComparisonEngine()
