"""Unit tests for CompressionEngine."""

import base64
import zlib
import pytest
from app.core.compression import CompressionEngine


@pytest.fixture
def ce():
    return CompressionEngine()


def test_hash_deterministic(ce):
    h1 = ce.compute_hash({"a": 1, "b": 2})
    h2 = ce.compute_hash({"b": 2, "a": 1})
    assert h1 == h2


def test_hash_changes_with_data(ce):
    assert ce.compute_hash({"a": 1}) != ce.compute_hash({"a": 2})


def test_compress_full_payload(ce):
    data = {"items": list(range(100))}
    out = ce.compress_response(data)
    assert out["type"] == "full"
    assert "data" in out
    decoded = zlib.decompress(base64.b64decode(out["data"])).decode()
    assert "0" in decoded


def test_compress_no_change(ce):
    data = {"v": 1}
    h = ce.compute_hash(data)
    out = ce.compress_response(data, previous_hash=h)
    assert out["type"] == "no_change"
    assert out["size_bytes"] == 0


def test_stats_track_requests(ce):
    ce.compress_response({"a": 1})
    ce.compress_response({"a": 2})
    s = ce.get_stats()
    assert s["total_requests"] == 2
    assert s["full_responses"] == 2


def test_stats_track_delta_hits(ce):
    h = ce.compute_hash({"a": 1})
    ce.compress_response({"a": 1}, previous_hash=h)
    s = ce.get_stats()
    assert s["delta_hits"] == 1


def test_get_stats_has_timestamp(ce):
    s = ce.get_stats()
    assert "timestamp" in s


def test_compress_list(ce):
    out = ce.compress_response([1, 2, 3])
    assert out["type"] == "full"
    assert out["original_size"] > 0
