"""User feedback collection endpoint."""

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.audit_log import audit_log

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])

_feedback_store: list[dict] = []


class FeedbackIn(BaseModel):
    category: Literal["bug", "feature_request", "general", "praise"] = "general"
    message: str = Field(min_length=3, max_length=4000)
    rating: int | None = Field(default=None, ge=1, le=5)
    page: str | None = None
    email: str | None = None


class FeedbackOut(BaseModel):
    id: str
    received_at: str
    status: str = "received"


def _current_user_id() -> str | None:
    """Best-effort user id resolver. Replaced by real auth dependency in main.py."""
    return None


@router.post("", response_model=FeedbackOut, status_code=201)
async def submit_feedback(
    payload: FeedbackIn,
    user_id: str | None = Depends(_current_user_id),
) -> FeedbackOut:
    entry = {
        "id": str(uuid4()),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        **payload.model_dump(),
    }
    _feedback_store.append(entry)
    try:
        await audit_log.log(
            "feedback.submitted",
            agent_id="system",
            details={"category": entry["category"], "rating": entry.get("rating")},
            user_id=user_id,
        )
    except Exception:
        # Audit failure must not block feedback submission
        pass
    return FeedbackOut(id=entry["id"], received_at=entry["received_at"])


@router.get("", response_model=list[dict])
async def list_feedback(limit: int = 100) -> list[dict]:
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
    return _feedback_store[-limit:]
