"""Unit tests for cors_config."""

import os
import warnings
import pytest
from app.core import cors_config


@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)
    return monkeypatch


def test_origins_from_env(clean_env):
    clean_env.setenv("CORS_ORIGINS", "https://a.com,https://b.com")
    origins = cors_config.get_cors_origins()
    assert origins == ["https://a.com", "https://b.com"]


def test_origins_strip_whitespace(clean_env):
    clean_env.setenv("CORS_ORIGINS", " https://a.com , https://b.com ")
    origins = cors_config.get_cors_origins()
    assert origins == ["https://a.com", "https://b.com"]


def test_default_in_debug_mode_no_warning(clean_env):
    clean_env.setenv("DEBUG", "true")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        origins = cors_config.get_cors_origins()
    assert "http://localhost:3000" in origins
    assert not any("CORS_ORIGINS not set" in str(x.message) for x in w)


def test_default_in_prod_warns(clean_env):
    # No CORS_ORIGINS, no DEBUG -> warning expected
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        origins = cors_config.get_cors_origins()
    assert "http://localhost:3000" in origins
    assert any("CORS_ORIGINS not set" in str(x.message) for x in w)


def test_get_cors_config_shape(clean_env):
    clean_env.setenv("CORS_ORIGINS", "https://a.com")
    cfg = cors_config.get_cors_config()
    assert cfg["allow_origins"] == ["https://a.com"]
    assert cfg["allow_credentials"] is True
    assert "GET" in cfg["allow_methods"]
    assert "Authorization" in cfg["allow_headers"]
    assert "X-Request-ID" in cfg["expose_headers"]
    assert cfg["max_age"] == 3600


def test_empty_env_returns_defaults(clean_env):
    clean_env.setenv("CORS_ORIGINS", "")
    clean_env.setenv("DEBUG", "true")
    origins = cors_config.get_cors_origins()
    assert "http://localhost:3000" in origins


def test_filter_empty_segments(clean_env):
    clean_env.setenv("CORS_ORIGINS", "https://a.com,,https://b.com,")
    origins = cors_config.get_cors_origins()
    assert origins == ["https://a.com", "https://b.com"]
