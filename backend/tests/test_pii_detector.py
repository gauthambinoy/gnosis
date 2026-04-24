"""Unit tests for PIIDetector."""

import pytest
from app.core.pii_detector import PIIDetector


@pytest.fixture
def det():
    return PIIDetector()


def test_detect_email(det):
    res = det.scan("Contact me at jane.doe@example.com please")
    assert res.pii_found
    types = {d.pii_type for d in res.detections}
    assert "email" in types
    assert "[EMAIL_REDACTED]" in res.redacted_text


def test_detect_phone(det):
    res = det.scan("Call (415) 555-1234 today")
    assert any(d.pii_type == "phone_us" for d in res.detections)
    assert "[PHONE_REDACTED]" in res.redacted_text


def test_detect_ssn(det):
    res = det.scan("SSN: 123-45-6789")
    assert any(d.pii_type == "ssn" for d in res.detections)
    assert "[SSN_REDACTED]" in res.redacted_text


def test_detect_credit_card(det):
    res = det.scan("My card 4111 1111 1111 1111")
    assert any(d.pii_type == "credit_card" for d in res.detections)
    assert "[CC_REDACTED]" in res.redacted_text


def test_clean_text_no_pii(det):
    res = det.scan("Hello world, just a friendly message.")
    assert res.pii_found is False
    assert res.redacted_text == res.text


def test_redact_shortcut(det):
    out = det.redact("send to test@x.io")
    assert "test@x.io" not in out
    assert "[EMAIL_REDACTED]" in out


def test_multiple_detections_redacted(det):
    res = det.scan("a@b.com and c@d.com and 111-22-3333")
    assert len(res.detections) >= 3
    assert "a@b.com" not in res.redacted_text
    assert "c@d.com" not in res.redacted_text
    assert "111-22-3333" not in res.redacted_text


def test_stats_increment(det):
    det.scan("foo@bar.com")
    det.scan("nothing here")
    stats = det.stats
    assert stats["total_scans"] == 2
    assert stats["total_detections"] >= 1


def test_enabled_types_filter():
    det = PIIDetector(enabled_types={"email"})
    res = det.scan("email a@b.com phone (415) 555-1234")
    types = {d.pii_type for d in res.detections}
    assert "email" in types
    assert "phone_us" not in types


def test_scan_time_recorded(det):
    res = det.scan("hello@world.com")
    assert res.scan_time_ms >= 0
