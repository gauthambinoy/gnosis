"""Startup environment validation — fail fast with clear messages."""
import os
import sys
import logging

logger = logging.getLogger("gnosis.env")

REQUIRED_VARS = {
    "DATABASE_URL": "PostgreSQL connection string (e.g., postgresql+asyncpg://user:pass@host/db)",
    "JWT_SECRET_KEY": "Secret key for JWT token signing (generate with: openssl rand -hex 32)",
}

RECOMMENDED_VARS = {
    "REDIS_URL": "Redis connection string (default: redis://localhost:6379/0)",
    "OPENROUTER_API_KEY": "OpenRouter API key for LLM access",
    "ENCRYPTION_KEY": "Key for encrypting stored secrets (generate with: openssl rand -hex 32)",
}

OPTIONAL_VARS = {
    "ANTHROPIC_API_KEY": "Anthropic Claude API key",
    "OPENAI_API_KEY": "OpenAI API key",
    "GOOGLE_API_KEY": "Google AI API key",
    "AWS_ACCESS_KEY_ID": "AWS access key for S3 file storage",
    "AWS_SECRET_ACCESS_KEY": "AWS secret key for S3",
    "GNOSIS_UPLOAD_DIR": "File upload directory (default: ./uploads)",
    "CORS_ORIGINS": "Comma-separated allowed CORS origins",
    "LOG_LEVEL": "Logging level (default: INFO)",
}


def validate_environment(strict: bool = False) -> dict:
    """Validate environment variables. Returns status report.
    
    If strict=True, exits the process on missing required vars.
    """
    report = {"required": {}, "recommended": {}, "optional": {}, "errors": [], "warnings": []}

    # Check required
    for var, desc in REQUIRED_VARS.items():
        val = os.getenv(var, "")
        if not val:
            report["required"][var] = {"status": "MISSING", "description": desc}
            report["errors"].append(f"Missing required: {var} — {desc}")
        else:
            report["required"][var] = {"status": "OK", "value_preview": f"{val[:8]}..."}

    # Check recommended
    for var, desc in RECOMMENDED_VARS.items():
        val = os.getenv(var, "")
        if not val:
            report["recommended"][var] = {"status": "MISSING", "description": desc}
            report["warnings"].append(f"Missing recommended: {var} — {desc}")
        else:
            report["recommended"][var] = {"status": "OK"}

    # Check optional
    for var, desc in OPTIONAL_VARS.items():
        val = os.getenv(var, "")
        report["optional"][var] = {"status": "SET" if val else "UNSET", "description": desc}

    # Log results
    if report["errors"]:
        for err in report["errors"]:
            logger.error(f"ENV VALIDATION: {err}")
        if strict:
            logger.critical("Exiting due to missing required environment variables.")
            sys.exit(1)
    
    if report["warnings"]:
        for warn in report["warnings"]:
            logger.warning(f"ENV VALIDATION: {warn}")

    configured = sum(1 for v in {**REQUIRED_VARS, **RECOMMENDED_VARS, **OPTIONAL_VARS} if os.getenv(v))
    total = len(REQUIRED_VARS) + len(RECOMMENDED_VARS) + len(OPTIONAL_VARS)
    logger.info(f"Environment: {configured}/{total} vars configured, {len(report['errors'])} errors, {len(report['warnings'])} warnings")

    return report
