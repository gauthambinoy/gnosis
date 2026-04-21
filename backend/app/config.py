import logging
import warnings

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_INSECURE_DEFAULT_KEY = "gnosis-secret-key-change-in-production-minimum-32-chars"

# Centralised registry of every literal default-secret string ever shipped with
# Gnosis. New defaults must be added here so the startup validator can refuse
# to boot a production instance that still has them in place.
INSECURE_DEFAULT_SECRETS: frozenset[str] = frozenset(
    {
        _INSECURE_DEFAULT_KEY,
        "change-in-production",
        "changeme",
        "secret",
        "default",
    }
)

# Environments treated as non-production. Anything else (prod, production,
# staging, stage, prd, live, ...) is considered production-like and forces a
# hard failure when an insecure default secret is detected.
NON_PRODUCTION_ENVIRONMENTS: frozenset[str] = frozenset(
    {"dev", "development", "local", "test", "testing", "ci"}
)


def is_insecure_default_secret(value: str | None) -> bool:
    """Return True if ``value`` is one of the known shipped defaults."""
    if not value:
        return True
    return value in INSECURE_DEFAULT_SECRETS


class Settings(BaseSettings):
    # App
    app_name: str = "Gnosis"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = (
        "postgresql+asyncpg://gnosis:gnosis_secret@localhost:5432/gnosis"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = _INSECURE_DEFAULT_KEY
    jwt_secret_key: str | None = None
    encryption_key: str | None = None
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    @property
    def is_production_environment(self) -> bool:
        env = (self.environment or "").strip().lower()
        return bool(env) and env not in NON_PRODUCTION_ENVIRONMENTS

    @model_validator(mode="after")
    def _validate_secret_key(self) -> "Settings":
        env_is_prod = self.is_production_environment
        # Treat DEBUG=true as an additional dev-mode signal so legacy callers
        # that flip DEBUG without touching ENVIRONMENT still get warn-only.
        in_dev = (not env_is_prod) or self.debug

        for field_name, field_value in (
            ("SECRET_KEY", self.secret_key),
            ("JWT_SECRET_KEY", self.jwt_secret_key),
            ("ENCRYPTION_KEY", self.encryption_key),
        ):
            # Only SECRET_KEY is mandatory; the rest are checked when set.
            if field_value is None:
                continue

            if field_value in INSECURE_DEFAULT_SECRETS:
                if not in_dev:
                    raise ValueError(
                        f"FATAL: {field_name} is set to a known insecure default "
                        f"while ENVIRONMENT={self.environment!r}. "
                        "Set a strong value (generate with: openssl rand -hex 32) "
                        "or set ENVIRONMENT=development for local use."
                    )
                warnings.warn(
                    f"{field_name} is the insecure default — acceptable only in "
                    "development/test. Never deploy to production without rotating it.",
                    stacklevel=2,
                )
            elif len(field_value) < 32:
                raise ValueError(
                    f"{field_name} must be at least 32 characters long for security."
                )
        return self

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # LLM (defaults, user can override)
    default_llm_provider: str = "openrouter"
    default_provider: str = "openrouter"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Rate limiting
    rate_limit_per_minute: int = 100

    # SSO
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""

    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""  # Empty = use IAM role (recommended on ECS)
    aws_secret_access_key: str = ""
    s3_upload_bucket: str = ""
    s3_export_bucket: str = ""
    sqs_execution_queue_url: str = ""
    sqs_webhook_queue_url: str = ""
    ses_sender_email: str = ""
    dynamodb_execution_table: str = ""
    dynamodb_sessions_table: str = ""
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""

    # Sentry
    sentry_dsn: str = ""

    # Auto-API security: comma-separated allowlist of hostnames permitted for
    # outbound /api/v1/auto-api/.../call requests. Empty in production blocks all.
    # Honors env var GNOSIS_AUTO_API_ALLOWED_HOSTS.
    auto_api_allowed_hosts: str = ""

    # Performance
    cache_ttl_seconds: int = 300
    max_cache_size: int = 1000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
