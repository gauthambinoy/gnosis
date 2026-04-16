"""Safe error response helper — never leak internal details to clients."""
from fastapi import HTTPException
from app.core.logger import get_logger

logger = get_logger("gnosis.errors")


def safe_http_error(
    e: Exception,
    message: str = "An error occurred",
    status_code: int = 400,
) -> None:
    """Log the real error, raise a sanitized HTTPException."""
    logger.error("API error: %s — %s", message, e, exc_info=True)
    raise HTTPException(status_code=status_code, detail=message)
