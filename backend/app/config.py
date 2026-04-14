from pydantic_settings import BaseSettings
from functools import lru_cache


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
    secret_key: str = "gnosis-secret-key-change-in-production-minimum-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

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
