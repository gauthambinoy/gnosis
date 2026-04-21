"""Concurrent-safety tests for the in-memory rate limiter."""

import asyncio
import pytest

from app.core.rate_limiter import RateLimiter


@pytest.mark.anyio
async def test_concurrent_acheck_respects_limit():
    rl = RateLimiter()
    limit = 50
    total = 200

    async def hit():
        return await rl.acheck("concur-key", limit=limit)

    results = await asyncio.gather(*(hit() for _ in range(total)))
    allowed = sum(1 for r in results if r["allowed"])
    denied = sum(1 for r in results if not r["allowed"])
    assert allowed == limit
    assert denied == total - limit


@pytest.mark.anyio
async def test_acheck_independent_keys():
    rl = RateLimiter()

    async def hit(key: str):
        return await rl.acheck(key, limit=3)

    results = await asyncio.gather(
        *(hit("k-a") for _ in range(3)),
        *(hit("k-b") for _ in range(3)),
    )
    assert all(r["allowed"] for r in results)
    blocked_a = await rl.acheck("k-a", limit=3)
    assert blocked_a["allowed"] is False
    blocked_b = await rl.acheck("k-b", limit=3)
    assert blocked_b["allowed"] is False


@pytest.mark.anyio
async def test_acheck_user_and_ip_helpers():
    rl = RateLimiter()
    rl.set_user_limit("u1", 2)
    r1 = await rl.acheck_user("u1")
    r2 = await rl.acheck_user("u1")
    r3 = await rl.acheck_user("u1")
    assert r1["allowed"] and r2["allowed"]
    assert r3["allowed"] is False

    ip_result = await rl.acheck_ip("1.2.3.4")
    assert ip_result["allowed"] is True
