"""Gnosis Confidence Scoring — Estimate response confidence."""

import logging
from dataclasses import dataclass

logger = logging.getLogger("gnosis.confidence")


@dataclass
class ConfidenceScore:
    overall: float  # 0-100
    memory_match: float  # How well memory matched the query (0-100)
    model_certainty: float  # Based on response characteristics (0-100)
    context_coverage: float  # How much context was available (0-100)
    reasoning_depth: float  # Which reasoning level was used (0-100)
    explanation: str = ""


class ConfidenceEngine:
    """Estimates confidence for agent responses."""

    def score(
        self,
        memory_results: int = 0,
        memory_max_score: float = 0.0,
        context_tokens: int = 0,
        max_context_tokens: int = 800,
        reasoning_level: int = 0,  # 0=cache, 1=pattern, 2=classify, 3=standard, 4=deep
        response_length: int = 0,
        has_corrections: bool = False,
        trust_level: int = 0,
    ) -> ConfidenceScore:
        # Memory match score
        if memory_results > 0:
            memory_score = min(
                100, memory_max_score * 100 * (1 + min(memory_results, 5) / 10)
            )
            if has_corrections:
                memory_score = min(100, memory_score * 1.3)
        else:
            memory_score = 20.0  # Low confidence without memory

        # Model certainty (inferred from response characteristics)
        length_factor = min(
            1.0, response_length / 200
        )  # Longer = more detailed = more certain
        model_score = 50 + length_factor * 30 + (trust_level * 5)

        # Context coverage
        context_ratio = (
            min(1.0, context_tokens / max_context_tokens)
            if max_context_tokens > 0
            else 0
        )
        context_score = context_ratio * 100

        # Reasoning depth
        reasoning_scores = {0: 30, 1: 50, 2: 65, 3: 80, 4: 95}
        reasoning_score = reasoning_scores.get(reasoning_level, 50)

        # Weighted overall
        overall = (
            memory_score * 0.3
            + model_score * 0.25
            + context_score * 0.2
            + reasoning_score * 0.25
        )

        # Explanation
        parts = []
        if memory_score >= 70:
            parts.append("strong memory match")
        elif memory_score < 40:
            parts.append("limited memory context")
        if reasoning_level >= 3:
            parts.append("deep reasoning applied")
        elif reasoning_level <= 1:
            parts.append("pattern-matched response")
        if context_score >= 60:
            parts.append("good context coverage")

        explanation = ", ".join(parts) if parts else "standard confidence"

        return ConfidenceScore(
            overall=round(min(100, max(0, overall)), 1),
            memory_match=round(min(100, max(0, memory_score)), 1),
            model_certainty=round(min(100, max(0, model_score)), 1),
            context_coverage=round(min(100, max(0, context_score)), 1),
            reasoning_depth=round(min(100, max(0, reasoning_score)), 1),
            explanation=explanation,
        )


confidence_engine = ConfidenceEngine()
