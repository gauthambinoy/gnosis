"""Unit tests for DeadLetterQueue."""

import pytest
from app.core.dlq import DeadLetterQueue


@pytest.fixture
def dlq():
    return DeadLetterQueue()


def test_push_creates_entry(dlq):
    e = dlq.push("execution", "boom", payload={"x": 1})
    assert e.operation == "execution"
    assert e.status == "pending"
    assert dlq.get(e.id) is e


def test_get_missing(dlq):
    assert dlq.get("nope") is None


def test_list_filter_by_operation(dlq):
    dlq.push("execution", "e1")
    dlq.push("webhook", "e2")
    res = dlq.list_entries(operation="execution")
    assert len(res) == 1
    assert res[0]["operation"] == "execution"


def test_list_filter_by_status(dlq):
    e = dlq.push("execution", "e1")
    dlq.push("execution", "e2")
    dlq.mark_resolved(e.id)
    pending = dlq.list_entries(status="pending")
    resolved = dlq.list_entries(status="resolved")
    assert len(pending) == 1
    assert len(resolved) == 1


def test_mark_resolved_true_false(dlq):
    e = dlq.push("execution", "e")
    assert dlq.mark_resolved(e.id) is True
    assert dlq.mark_resolved("missing") is False


def test_retry_increments(dlq):
    e = dlq.push("execution", "e", max_retries=2)
    r = dlq.retry(e.id)
    assert r["status"] == "retrying"
    assert r["retry_count"] == 1


def test_retry_expires_after_max(dlq):
    e = dlq.push("execution", "e", max_retries=1)
    dlq.retry(e.id)  # 1
    out = dlq.retry(e.id)  # exceeded
    assert out["status"] == "expired"
    assert dlq.get(e.id).status == "expired"


def test_retry_missing_returns_none(dlq):
    assert dlq.retry("missing") is None


def test_purge_resolved(dlq):
    e1 = dlq.push("execution", "e1")
    dlq.push("execution", "e2")
    dlq.mark_resolved(e1.id)
    purged = dlq.purge_resolved()
    assert purged == 1
    assert len(dlq._entries) == 1


def test_max_entries_trim():
    dlq = DeadLetterQueue(max_entries=3)
    for i in range(5):
        dlq.push("op", f"err{i}")
    assert len(dlq._entries) == 3


def test_stats(dlq):
    dlq.push("execution", "e1")
    e = dlq.push("webhook", "e2")
    dlq.mark_resolved(e.id)
    s = dlq.stats
    assert s["total"] == 2
    assert s["by_status"]["pending"] == 1
    assert s["by_status"]["resolved"] == 1
    assert s["by_operation"]["execution"] == 1
