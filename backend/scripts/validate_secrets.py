#!/usr/bin/env python3
"""
Gnosis Secrets Validation Script

Verifies all required production secrets are configured before startup.
Fails fast with clear error messages if any secrets are missing.

Usage:
    python3 scripts/validate_secrets.py [--environment prod|staging|dev]
"""

import sys
import os
from typing import Optional
from pathlib import Path

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


if __name__ == "__main__":
    main()
