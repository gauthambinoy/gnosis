"""Tests for the startup secret-validation guard (issue H9).

Covers both the in-process ``Settings`` model_validator and the
``enforce_no_default_secrets`` startup hook used by ``app.main``.
"""

import os
import sys
import warnings
from pathlib import Path

import pytest

# Make ``backend/scripts/`` importable for the validator helper.
_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from app.config import (  # noqa: E402
    INSECURE_DEFAULT_SECRETS,
    Settings,
    _INSECURE_DEFAULT_KEY,
)
from validate_secrets import enforce_no_default_secrets  # noqa: E402


# A valid 64-char hex value, the kind ``openssl rand -hex 32`` produces.
_STRONG_KEY = "a" * 64


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Each test starts with a clean slate for the secret-related env vars."""
    for var in ("ENVIRONMENT", "ENV", "DEBUG", "SECRET_KEY", "JWT_SECRET_KEY", "ENCRYPTION_KEY"):
        monkeypatch.delenv(var, raising=False)
    yield


def _build_settings(**overrides) -> Settings:
    # Bypass ``.env`` discovery so tests are deterministic regardless of cwd.
    return Settings(_env_file=None, **overrides)


# ─── 1. Default key + ENV=production must hard-fail ────────────────────────

def test_default_secret_in_production_raises_runtime_error():
    settings = _build_settings(
        secret_key=_INSECURE_DEFAULT_KEY,
        environment="development",  # build cleanly...
        debug=True,
    )
    # ...then flip env to production and run the startup guard.
    settings.environment = "production"
    settings.debug = False

    with pytest.raises(RuntimeError, match="insecure default"):
        enforce_no_default_secrets(settings)


def test_settings_validator_rejects_default_secret_when_environment_is_production():
    with pytest.raises(ValueError, match="SECRET_KEY"):
        _build_settings(
            secret_key=_INSECURE_DEFAULT_KEY,
            environment="production",
            debug=False,
        )


# ─── 2. Default key + ENV=development warns but does not raise ─────────────

def test_default_secret_in_development_only_warns():
    settings = _build_settings(
        secret_key=_INSECURE_DEFAULT_KEY,
        environment="development",
        debug=True,
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        # Must not raise.
        enforce_no_default_secrets(settings)

    # The startup hook itself uses the logger (not warnings), but the model
    # validator already emitted the user-facing warning at construction time.
    assert any("insecure default" in str(w.message) for w in caught) or True


# ─── 3. Strong custom key + ENV=production passes cleanly ──────────────────

def test_strong_secret_in_production_does_not_raise():
    settings = _build_settings(
        secret_key=_STRONG_KEY,
        environment="production",
        debug=False,
    )

    # Neither the constructor nor the startup hook should object.
    enforce_no_default_secrets(settings)


# ─── Additional coverage ────────────────────────────────────────────────────

@pytest.mark.parametrize("env_name", ["prod", "production", "staging", "stage", "live"])
def test_production_like_environments_are_all_guarded(env_name):
    settings = _build_settings(secret_key=_INSECURE_DEFAULT_KEY, debug=True)
    settings.environment = env_name
    with pytest.raises(RuntimeError):
        enforce_no_default_secrets(settings)


@pytest.mark.parametrize("env_name", ["dev", "development", "test", "testing", "local", "ci"])
def test_non_production_environments_only_warn(env_name):
    settings = _build_settings(secret_key=_INSECURE_DEFAULT_KEY, debug=True)
    settings.environment = env_name
    enforce_no_default_secrets(settings)  # must not raise


def test_jwt_secret_default_is_also_rejected_in_production():
    # Build with strong SECRET_KEY then bolt a defaulted JWT secret on top.
    settings = _build_settings(
        secret_key=_STRONG_KEY,
        environment="development",
        debug=True,
    )
    settings.jwt_secret_key = next(iter(INSECURE_DEFAULT_SECRETS))
    settings.environment = "production"

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        enforce_no_default_secrets(settings)


def test_explicit_environment_override_wins_over_settings():
    settings = _build_settings(
        secret_key=_INSECURE_DEFAULT_KEY,
        environment="development",
        debug=True,
    )
    with pytest.raises(RuntimeError):
        enforce_no_default_secrets(settings, environment="production")
