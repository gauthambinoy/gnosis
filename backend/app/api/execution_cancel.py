"""Graceful execution cancellation."""

from fastapi import APIRouter, Depends
from app.core.auth import get_current_user_id
import logging

logger = logging.getLogger("gnosis.cancel")
router = APIRouter(prefix="/api/v1/executions", tags=["executions"])

# Global cancellation registry
_cancelled: set = set()


def is_cancelled(execution_id: str) -> bool:
    return execution_id in _cancelled


def clear_cancelled(execution_id: str):
    _cancelled.discard(execution_id)


@router.post("/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str, reason: str = "", user_id: str = Depends(get_current_user_id)
):
    """Request cancellation of a running execution."""
    _cancelled.add(execution_id)
    logger.info(
        f"Execution cancel requested: {execution_id} by {user_id}, reason: {reason}"
    )
    return {
        "execution_id": execution_id,
        "status": "cancel_requested",
        "reason": reason,
    }


@router.get("/{execution_id}/cancel-status")
async def cancel_status(execution_id: str, user_id: str = Depends(get_current_user_id)):
    return {
        "execution_id": execution_id,
        "cancel_requested": execution_id in _cancelled,
    }
