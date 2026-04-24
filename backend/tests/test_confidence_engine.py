"""Unit tests for ConfidenceEngine."""

import pytest
from app.core.confidence import ConfidenceEngine


@pytest.fixture
def ce():
    return ConfidenceEngine()


def test_default_score_low_confidence(ce):
    s = ce.score()
    assert 0 <= s.overall <= 100
    assert s.memory_match == 20.0  # baseline when no memory


def test_strong_memory_increases_score(ce):
    s = ce.score(memory_results=5, memory_max_score=0.9)
    assert s.memory_match >= 70
    assert "strong memory match" in s.explanation


def test_corrections_boost_memory(ce):
    base = ce.score(memory_results=3, memory_max_score=0.7)
    boosted = ce.score(memory_results=3, memory_max_score=0.7, has_corrections=True)
    assert boosted.memory_match >= base.memory_match


def test_deep_reasoning_explanation(ce):
    s = ce.score(reasoning_level=4)
    assert "deep reasoning applied" in s.explanation
    assert s.reasoning_depth == 95


def test_pattern_reasoning_explanation(ce):
    s = ce.score(reasoning_level=1)
    assert "pattern-matched response" in s.explanation


def test_context_coverage(ce):
    s = ce.score(context_tokens=800, max_context_tokens=800)
    assert s.context_coverage == 100.0
    assert "good context coverage" in s.explanation


def test_context_zero_max(ce):
    s = ce.score(context_tokens=100, max_context_tokens=0)
    assert s.context_coverage == 0


def test_overall_clamped_to_100(ce):
    s = ce.score(
        memory_results=10,
        memory_max_score=1.0,
        context_tokens=1000,
        max_context_tokens=800,
        reasoning_level=4,
        response_length=500,
        has_corrections=True,
        trust_level=4,
    )
    assert s.overall <= 100
    assert s.model_certainty <= 100


def test_unknown_reasoning_level_default(ce):
    s = ce.score(reasoning_level=99)
    assert s.reasoning_depth == 50
