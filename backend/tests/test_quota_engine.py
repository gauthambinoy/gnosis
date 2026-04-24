"""Unit tests for QuotaEngine."""

import pytest

from app.core.quota_engine import QuotaEngine, TIER_LIMITS, QuotaLimits


@pytest.fixture
def qe():
    return QuotaEngine()


def test_default_tier_is_free(qe):
    limits = qe.get_limits("ws-1")
    assert limits.max_agents == TIER_LIMITS["free"].max_agents


def test_set_tier_pro(qe):
    qe.set_tier("ws-1", "pro")
    assert qe.get_limits("ws-1").max_agents == TIER_LIMITS["pro"].max_agents


def test_set_tier_invalid_raises(qe):
    with pytest.raises(ValueError):
        qe.set_tier("ws-1", "ultra")


def test_check_quota_unknown_resource_allows(qe):
    res = qe.check_quota("ws-1", "unknown_resource")
    assert res["allowed"] is True
    assert res["resource"] == "unknown_resource"


def test_check_quota_under_limit(qe):
    res = qe.check_quota("ws-1", "agents", amount=1)
    assert res["allowed"] is True
    # remaining = limit - current_usage (before this call)
    assert res["remaining"] == TIER_LIMITS["free"].max_agents


def test_record_and_exceed_quota(qe):
    qe.set_tier("ws-1", "free")
    for _ in range(TIER_LIMITS["free"].max_agents):
        qe.record_usage("ws-1", "agents")
    res = qe.check_quota("ws-1", "agents", amount=1)
    assert res["allowed"] is False
    assert res["remaining"] == 0


def test_record_usage_increments(qe):
    qe.record_usage("ws-1", "executions", amount=5)
    qe.record_usage("ws-1", "tokens", amount=100)
    usage = qe.get_usage("ws-1")
    assert usage.executions_today == 5
    assert usage.tokens_today == 100


def test_reset_daily_counters(qe):
    qe.record_usage("ws-1", "executions", amount=10)
    qe.record_usage("ws-1", "tokens", amount=100)
    qe.reset_daily_counters()
    usage = qe.get_usage("ws-1")
    assert usage.executions_today == 0
    assert usage.tokens_today == 0


def test_custom_limits_override_tier(qe):
    qe.set_tier("ws-1", "free")
    qe._custom_limits["ws-1"] = QuotaLimits(max_agents=999)
    assert qe.get_limits("ws-1").max_agents == 999


def test_dashboard_shape(qe):
    qe.set_tier("ws-1", "pro")
    qe.record_usage("ws-1", "agents", amount=5)
    dash = qe.get_dashboard("ws-1")
    assert dash["tier"] == "pro"
    assert "limits" in dash and "usage" in dash and "percentages" in dash
    assert dash["percentages"]["agents"] > 0


def test_tier_transition_keeps_usage(qe):
    qe.record_usage("ws-1", "agents", amount=2)
    qe.set_tier("ws-1", "enterprise")
    assert qe.get_usage("ws-1").agents == 2
    assert qe.get_limits("ws-1").max_agents == TIER_LIMITS["enterprise"].max_agents
