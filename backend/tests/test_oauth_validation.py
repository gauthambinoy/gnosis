"""Tests for OAuth credential validation (H18)."""

from __future__ import annotations

import pytest

from app.integrations.oauth import (
    OAuthConfigurationError,
    _build_provider_configs,
    validate_oauth_credentials,
)


def _clear_oauth(monkeypatch):
    for var in (
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "SLACK_CLIENT_ID",
        "SLACK_CLIENT_SECRET",
    ):
        monkeypatch.delenv(var, raising=False)


def test_all_providers_missing_returns_missing_list(monkeypatch):
    _clear_oauth(monkeypatch)
    result = validate_oauth_credentials()
    assert set(result["missing"]) == {"google", "slack"}
    assert result["configured"] == []


def test_partial_credentials_marked_missing(monkeypatch):
    """Only client_id without client_secret still counts as missing."""
    _clear_oauth(monkeypatch)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id-only")
    result = validate_oauth_credentials()
    assert "google" in result["missing"]


def test_fully_configured_provider_appears_in_configured(monkeypatch):
    _clear_oauth(monkeypatch)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    result = validate_oauth_credentials()
    assert "google" in result["configured"]
    assert "google" not in result["missing"]


def test_strict_mode_raises_when_missing(monkeypatch):
    _clear_oauth(monkeypatch)
    with pytest.raises(OAuthConfigurationError) as ei:
        validate_oauth_credentials(strict=True)
    msg = str(ei.value)
    assert "google" in msg and "slack" in msg


def test_strict_mode_does_not_raise_when_all_present(monkeypatch):
    _clear_oauth(monkeypatch)
    for v in (
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "SLACK_CLIENT_ID",
        "SLACK_CLIENT_SECRET",
    ):
        monkeypatch.setenv(v, "x")
    # No exception
    validate_oauth_credentials(strict=True)


def test_required_providers_filter(monkeypatch):
    _clear_oauth(monkeypatch)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "s")
    # Only check google — slack missing should be OK
    result = validate_oauth_credentials(required_providers=["google"], strict=True)
    assert result["configured"] == ["google"]
    assert result["missing"] == []


def test_build_provider_configs_reflects_env_changes(monkeypatch):
    _clear_oauth(monkeypatch)
    cfgs = _build_provider_configs()
    assert cfgs["google"]["client_id"] == ""
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "x")
    cfgs2 = _build_provider_configs()
    assert cfgs2["google"]["client_id"] == "x"
