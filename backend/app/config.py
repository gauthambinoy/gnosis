import logging
import warnings

from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache

logger = logging.getLogger(__name__)

_INSECURE_DEFAULT_KEY = "gnosis-secret-key-change-in-production-minimum-32-chars"


class Settings(BaseSettings):
    # App
    app_name: str = "Gnosis"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://gnosis:gnosis_secret@localhost:5432/gnosis"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = _INSECURE_DEFAULT_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    @model_validator(mode="after")
    def _validate_secret_key(self) -> "Settings":
        if self.secret_key == _INSECURE_DEFAULT_KEY:
            if not self.debug:
                raise ValueError(
                    "FATAL: SECRET_KEY is set to the insecure default. "
                    "Set a strong SECRET_KEY in your .env file (generate with: openssl rand -hex 32). "
                    "Set DEBUG=true to bypass this check in development."
                )
            warnings.warn(
                "SECRET_KEY is the insecure default — acceptable only in DEBUG mode. "
                "Never deploy to production without a real secret key.",
                stacklevel=2,
            )
        elif len(self.secret_key) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long for security."
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

    # Performance
    cache_ttl_seconds: int = 300
    max_cache_size: int = 1000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
