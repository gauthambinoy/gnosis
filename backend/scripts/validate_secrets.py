#!/usr/bin/env python3
"""
Gnosis Secrets Validation Script

Verifies all required production secrets are configured before startup.
Fails fast with clear error messages if any secrets are missing.

Usage:
    python3 scripts/validate_secrets.py [--environment prod|staging|dev]

Programmatic use (called from app startup):
    from scripts.validate_secrets import enforce_no_default_secrets
    enforce_no_default_secrets(settings)        # raises RuntimeError on default
"""

import sys
import os
import logging
from typing import Iterable, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ANSI colors for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class SecretValidator:
    """Validates required secrets for Gnosis deployment."""

    # Secrets required in all environments
    REQUIRED_SECRETS = {
        "SECRET_KEY": "JWT signing key (generate: openssl rand -hex 32)",
        "DATABASE_URL": "PostgreSQL connection string",
    }

    # Secrets required in production
    PRODUCTION_SECRETS = {
        "OPENROUTER_API_KEY": "Primary LLM provider (OpenRouter)",
        "AWS_REGION": "AWS region for infrastructure",
        "AWS_ACCESS_KEY_ID": "AWS access key ID",
        "AWS_SECRET_ACCESS_KEY": "AWS secret access key",
        "GOOGLE_CLIENT_ID": "Google OAuth client ID",
        "GOOGLE_CLIENT_SECRET": "Google OAuth client secret",
        "GITHUB_CLIENT_ID": "GitHub OAuth app client ID",
        "GITHUB_CLIENT_SECRET": "GitHub OAuth app client secret",
    }

    # Optional secrets with fallback behavior
    OPTIONAL_SECRETS = {
        "REDIS_URL": "Redis cache URL (optional in dev)",
        "ANTHROPIC_API_KEY": "Anthropic Claude API key (fallback provider)",
        "OPENAI_API_KEY": "OpenAI API key (fallback provider)",
        "SENTRY_DSN": "Sentry error tracking (optional)",
    }

    def __init__(self, environment: str = "dev"):
        """Initialize validator for given environment."""
        self.environment = environment
        self.missing_secrets = []
        self.optional_missing = []
        self.warnings = []

    def validate(self) -> bool:
        """Validate all required secrets. Returns True if all present."""
        print(f"\n{BLUE}🔍 Validating Gnosis secrets for '{self.environment}' environment{RESET}\n")

        # Check required secrets
        self._check_secrets(self.REQUIRED_SECRETS, required=True)

        # Check production-specific secrets
        if self.environment == "prod":
            self._check_secrets(self.PRODUCTION_SECRETS, required=True)
            self._validate_production_settings()

        # Check optional secrets
        self._check_secrets(self.OPTIONAL_SECRETS, required=False)

        # Report results
        return self._print_report()

    def _check_secrets(self, secrets_dict: dict, required: bool = True):
        """Check if secrets exist in environment."""
        for secret_name, description in secrets_dict.items():
            value = os.getenv(secret_name)

            if value:
                status = f"{GREEN}✓{RESET}"
                print(f"  {status} {secret_name:<30} {YELLOW}(configured){RESET}")
            else:
                status = f"{RED}✗{RESET}"
                print(f"  {status} {secret_name:<30} {RED}(MISSING){RESET}")

                if required:
                    self.missing_secrets.append((secret_name, description))
                else:
                    self.optional_missing.append((secret_name, description))

    def _validate_production_settings(self):
        """Additional validation for production environment."""
        # Check DEBUG is False in production
        debug = os.getenv("DEBUG", "false").lower()
        if debug == "true":
            self.warnings.append("DEBUG=true in production (should be 'false')")

        # Check database URL uses async driver
        db_url = os.getenv("DATABASE_URL", "")
        if db_url and "asyncpg" not in db_url:
            self.warnings.append("DATABASE_URL should use 'asyncpg' driver")

    def _print_report(self) -> bool:
        """Print validation report and return success status."""
        print("\n" + "=" * 70)

        if self.missing_secrets:
            print(f"\n{RED}❌ VALIDATION FAILED - Missing required secrets:{RESET}\n")

            for secret_name, description in self.missing_secrets:
                print(f"  • {secret_name}")
                print(f"    └─ {description}\n")

            return False

        if self.warnings:
            print(f"\n{YELLOW}⚠️  CONFIGURATION WARNINGS:{RESET}\n")
            for warning in self.warnings:
                print(f"  • {warning}\n")

        print("=" * 70)

        if not self.missing_secrets:
            print(f"\n{GREEN}✅ All required secrets validated successfully{RESET}\n")
            return True

        return False


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate Gnosis secrets before deployment")
    parser.add_argument(
        "--environment",
        choices=["dev", "staging", "prod"],
        default="dev",
        help="Deployment environment (default: dev)",
    )

    args = parser.parse_args()

    validator = SecretValidator(environment=args.environment)
    success = validator.validate()

    sys.exit(0 if success else 1)


# ─── Startup hook (programmatic) ───────────────────────────────────────────
#
# The CLI ``SecretValidator`` above is meant for human-driven pre-deploy
# checks. The ``enforce_no_default_secrets`` helper below is the in-process
# guard wired into ``app.main`` so the FastAPI app refuses to serve a single
# request when a known shipped default secret is still in place in a
# production-like environment.

_KNOWN_DEFAULT_SECRETS: frozenset[str] = frozenset(
    {
        "gnosis-secret-key-change-in-production-minimum-32-chars",
        "change-in-production",
        "changeme",
        "secret",
        "default",
    }
)

_NON_PRODUCTION_ENVIRONMENTS: frozenset[str] = frozenset(
    {"dev", "development", "local", "test", "testing", "ci"}
)

# Settings attribute names (and their canonical env var names) that must never
# hold a known default secret in production.
_PROTECTED_SECRET_FIELDS: tuple[tuple[str, str], ...] = (
    ("secret_key", "SECRET_KEY"),
    ("jwt_secret_key", "JWT_SECRET_KEY"),
    ("encryption_key", "ENCRYPTION_KEY"),
)


def _resolve_environment(settings, override: Optional[str]) -> str:
    if override is not None:
        return override
    env = getattr(settings, "environment", None)
    if not env:
        env = os.getenv("ENVIRONMENT") or os.getenv("ENV") or "development"
    return str(env)


def _is_production(environment: str) -> bool:
    return environment.strip().lower() not in _NON_PRODUCTION_ENVIRONMENTS


def _iter_default_secret_fields(settings) -> Iterable[tuple[str, str]]:
    for attr, env_name in _PROTECTED_SECRET_FIELDS:
        value = getattr(settings, attr, None)
        if value is None:
            continue
        if value in _KNOWN_DEFAULT_SECRETS:
            yield env_name, value


def enforce_no_default_secrets(settings, environment: Optional[str] = None) -> None:
    """Fail-fast guard for app startup.

    Raises ``RuntimeError`` when any protected secret on ``settings`` matches a
    known shipped default and the resolved environment is production-like.
    In development/test environments the check only emits a warning so local
    boots are not disrupted.
    """
    env = _resolve_environment(settings, environment)
    offenders = list(_iter_default_secret_fields(settings))

    if not offenders:
        return

    names = ", ".join(name for name, _ in offenders)

    if _is_production(env):
        raise RuntimeError(
            f"FATAL: refusing to start Gnosis in environment={env!r} because the "
            f"following secret(s) still hold a known insecure default value: "
            f"{names}. Rotate them before launching (generate with: "
            f"openssl rand -hex 32)."
        )

    logger.warning(
        "Insecure default secret(s) detected in environment=%s: %s. "
        "Acceptable only in dev/test — production startup will be refused.",
        env,
        names,
    )


if __name__ == "__main__":
    main()
