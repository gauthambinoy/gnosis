"""Unit tests for RateLimiter sync API."""

import time
import pytest
from app.core.rate_limiter import RateLimiter


@pytest.fixture
def rl():
    return RateLimiter()


def test_check_under_limit(rl):
    res = rl.check("k1", limit=3)
    assert res["allowed"] is True
    assert res["remaining"] == 2


def test_check_blocks_at_limit(rl):
    for _ in range(3):
        rl.check("k1", limit=3)
    res = rl.check("k1", limit=3)
    assert res["allowed"] is False
    assert res["remaining"] == 0
    assert res["limit"] == 3


def test_check_user_default_limit(rl):
    res = rl.check_user("user-x")
    assert res["allowed"] is True
    assert res["limit"] == rl.default_limit


def test_set_user_limit(rl):
    rl.set_user_limit("user-x", 2)
    rl.check_user("user-x")
    rl.check_user("user-x")
    res = rl.check_user("user-x")
    assert res["allowed"] is False


def test_check_ip_isolated_from_user(rl):
    res_u = rl.check_user("u1")
    res_i = rl.check_ip("1.2.3.4")
    assert res_u["allowed"] is True
    assert res_i["allowed"] is True


def test_get_stats(rl):
    rl.check("k1")
    rl.set_user_limit("u1", 10)
    s = rl.get_stats()
    assert s["tracked_keys"] >= 1
    assert s["custom_limits"] == 1


def test_window_cleanup(rl):
    # Insert old timestamps directly, then run a check; cleanup should remove old.
    rl.windows["k1"] = [time.time() - 120]  # > 60s old
    res = rl.check("k1", limit=2)
    assert res["allowed"] is True
    assert res["remaining"] == 1  # only the new entry remains


def test_default_limit_used(rl):
    res = rl.check("k1")
    assert res["limit"] == rl.default_limit
