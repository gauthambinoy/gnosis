"""User feedback collection endpoint."""

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.core.audit_log import audit_log
from app.core.auth import decode_token

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])

_feedback_store: list[dict] = []
_optional_security = HTTPBearer(auto_error=False)


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


async def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_security),
) -> Optional[str]:
    """Best-effort user resolver. Returns the JWT subject when a valid token is
    presented, otherwise None so anonymous feedback continues to work."""
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        return None
    if payload.get("type") != "access":
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None


@router.post("", response_model=FeedbackOut, status_code=201)
async def submit_feedback(
    payload: FeedbackIn,
    user_id: Optional[str] = Depends(get_optional_user_id),
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
