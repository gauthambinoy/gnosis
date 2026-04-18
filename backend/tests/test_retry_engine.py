"""Tests for retry engine."""

import pytest
from app.core.retry_engine import RetryEngine


class TestRetryEngine:
    def setup_method(self):
        self.engine = RetryEngine(max_attempts=3, base_delay=0.01, max_delay=0.1)

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        call_count = 0

        async def success_fn():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await self.engine.execute_with_retry("exec-1", success_fn)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_then_success(self):
        attempts = 0

        async def flaky_fn():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ValueError("temporary failure")
            return "recovered"

        result = await self.engine.execute_with_retry("exec-2", flaky_fn)
        assert result == "recovered"
        assert attempts == 3

    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        async def always_fail():
            raise RuntimeError("permanent failure")

        with pytest.raises(RuntimeError, match="permanent failure"):
            await self.engine.execute_with_retry("exec-3", always_fail)

        record = self.engine.get_record("exec-3")
        assert record["status"] == "exhausted"
        assert len(record["errors"]) == 3

    @pytest.mark.asyncio
    async def test_record_tracks_success(self):
        async def ok():
            return 42

        await self.engine.execute_with_retry("exec-4", ok)
        record = self.engine.get_record("exec-4")
        assert record["status"] == "succeeded"
        assert record["completed_at"] is not None

    def test_stats(self):
        stats = self.engine.stats
        assert "total_tracked" in stats
        assert "total_retries" in stats
        assert stats["total_tracked"] == 0

    def test_get_nonexistent_record(self):
        assert self.engine.get_record("no-such-id") is None
