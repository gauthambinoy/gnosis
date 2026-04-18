"""
Predictions API — Predictive Agent Spawning endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from app.core.predictive_engine import predictive_engine

router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class TrackActionRequest(BaseModel):
    user_id: str = "default"
    action: str
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("")
async def get_predictions(user_id: str = "default"):
    """Get current predictions for user."""
    suggestions = await predictive_engine.suggest_agents(user_id)
    return {
        "predictions": suggestions,
        "count": len(suggestions),
        "user_id": user_id,
    }


@router.post("/track")
async def track_action(body: TrackActionRequest):
    """Track a user action for pattern learning."""
    event = await predictive_engine.track_action(
        body.user_id, body.action, body.metadata
    )
    return {
        "tracked": True,
        "event_id": event.id,
        "action": event.action,
        "timestamp": event.timestamp,
    }


@router.get("/patterns")
async def get_patterns(user_id: str = "default"):
    """View detected patterns for user."""
    patterns = await predictive_engine.analyze_patterns(user_id)
    return {
        "patterns": patterns,
        "count": len(patterns),
        "user_id": user_id,
    }


@router.post("/dismiss/{prediction_id}")
async def dismiss_prediction(prediction_id: str):
    """Dismiss a prediction."""
    result = await predictive_engine.dismiss_prediction(prediction_id)
    if not result:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {"dismissed": True, "prediction": result}


@router.post("/accept/{prediction_id}")
async def accept_prediction(prediction_id: str):
    """Accept & deploy a predicted agent."""
    result = await predictive_engine.accept_prediction(prediction_id)
    if not result:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {
        "accepted": True,
        "prediction": result,
        "message": "Agent deployment initiated",
    }


@router.get("/stats")
async def prediction_stats(user_id: str = "default"):
    """Prediction engine statistics."""
    stats = await predictive_engine.get_stats(user_id)
    return stats
