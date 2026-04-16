"""Startup banner with configuration summary."""
import sys
from app.config import get_settings
from app.core.logger import get_logger

logger = get_logger("startup")


def print_banner():
    settings = get_settings()
    db_status = (
        "connected"
        if settings.database_url and "postgresql" in settings.database_url
        else "in-memory"
    )
    redis_status = "connected" if settings.redis_url else "disabled"
    cors_display = str(settings.cors_origins)[:30]
    mode = "DEBUG" if settings.debug else "PRODUCTION"
    banner = f"""
\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
\u2551           GNOSIS AI AGENT PLATFORM           \u2551
\u2551              v1.0.0 \u2022 {mode:>10}        \u2551
\u2560\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2563
\u2551  API Prefix:  {settings.api_prefix:<30} \u2551
\u2551  Database:    {db_status:<30} \u2551
\u2551  Redis:       {redis_status:<30} \u2551
\u2551  CORS:        {cors_display:<30} \u2551
\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d"""
    print(banner, file=sys.stderr)
    logger.info(
        f"gnosis_started version=1.0.0 debug={settings.debug} "
        f"api_prefix={settings.api_prefix}"
    )
