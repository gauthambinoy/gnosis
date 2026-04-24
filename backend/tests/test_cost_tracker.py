"""Unit tests for CostTracker."""

import pytest
from app.core.cost_tracker import CostTracker


@pytest.fixture
def ct():
    return CostTracker()


def test_record_increments_today(ct):
    ct.record("a1", "cheap", "gpt-4o-mini", 100, 50, 0.001)
    today = ct.today_stats
    assert today["tokens"] == 150
    assert today["requests"] == 1
    assert today["cost"] == pytest.approx(0.001)


def test_total_stats_aggregates(ct):
    ct.record("a1", "cheap", "m", 10, 20, 0.01)
    ct.record("a2", "deep", "m2", 30, 40, 0.05)
    s = ct.total_stats
    assert s["total_tokens"] == 100
    assert s["total_requests"] == 2
    assert s["total_cost_usd"] == pytest.approx(0.06)


def test_cached_counted(ct):
    ct.record("a1", "cheap", "m", 1, 1, 0.0, cached=True)
    ct.record("a1", "cheap", "m", 1, 1, 0.0, cached=False)
    s = ct.total_stats
    assert s["cached_requests"] == 1
    assert s["cache_rate"] == 0.5


def test_agent_stats_filters(ct):
    ct.record("a1", "cheap", "m", 10, 10, 0.01)
    ct.record("a2", "deep", "m", 5, 5, 0.02)
    s = ct.agent_stats("a1")
    assert s["tokens"] == 20
    assert s["requests"] == 1
    assert "cheap" in s["by_tier"]


def test_agent_stats_empty(ct):
    s = ct.agent_stats("missing")
    assert s["tokens"] == 0
    assert s["requests"] == 0


def test_recent_records_limit(ct):
    for i in range(5):
        ct.record("a1", "cheap", "m", 1, 1, 0.001)
    recent = ct.recent_records(limit=3)
    assert len(recent) == 3
    assert recent[0]["agent_id"] == "a1"


def test_total_stats_empty(ct):
    s = ct.total_stats
    assert s["total_requests"] == 0
    assert s["cache_rate"] == 0


def test_today_stats_empty(ct):
    s = ct.today_stats
    assert s["tokens"] == 0
    assert s["cost"] == 0.0
