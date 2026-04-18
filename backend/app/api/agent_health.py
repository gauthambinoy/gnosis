"""Agent health score computation."""
from fastapi import APIRouter, HTTPException, Depends
from app.core.auth import get_current_user_id
import logging
from app.core.safe_error import safe_http_error

logger = logging.getLogger("gnosis.agent_health")
router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

def compute_health_score(agent_data: dict) -> dict:
    """Compute composite health score (0-100) for an agent."""
    factors = {}

    # Success rate (40% weight)
    total_exec = agent_data.get("total_executions", 0)
    success_rate = agent_data.get("success_rate", 0)
    if total_exec > 0:
        sr_score = min(success_rate * 100, 100)
        factors["success_rate"] = {"score": round(sr_score, 1), "weight": 40, "value": f"{success_rate*100:.1f}%"}
    else:
        sr_score = 50  # No data
        factors["success_rate"] = {"score": 50, "weight": 40, "value": "No executions"}

    # Status (20% weight)
    status = agent_data.get("status", "idle")
    status_scores = {"active": 100, "idle": 70, "paused": 50, "learning": 80, "error": 10}
    st_score = status_scores.get(status, 50)
    factors["status"] = {"score": st_score, "weight": 20, "value": status}

    # Error rate (20% weight)
    error_count = agent_data.get("error_count", 0)
    err_score = max(0, 100 - error_count * 10)
    factors["error_rate"] = {"score": err_score, "weight": 20, "value": f"{error_count} errors"}

    # Trust level (20% weight)
    trust = agent_data.get("trust_level", 1)
    trust_score = min(trust * 33, 100)
    factors["trust_level"] = {"score": round(trust_score, 1), "weight": 20, "value": f"Level {trust}"}

    # Weighted average
    total_score = (sr_score * 0.4) + (st_score * 0.2) + (err_score * 0.2) + (trust_score * 0.2)

    grade = "A" if total_score >= 90 else "B" if total_score >= 75 else "C" if total_score >= 60 else "D" if total_score >= 40 else "F"

    return {
        "health_score": round(total_score, 1),
        "grade": grade,
        "factors": factors,
    }

@router.get("/{agent_id}/health")
async def get_agent_health(agent_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        from app.core.marketplace import marketplace_engine
        agent = marketplace_engine.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        data = agent if isinstance(agent, dict) else agent.__dict__
        return compute_health_score(data)
    except HTTPException:
        raise
    except Exception as e:
        safe_http_error(e, "Operation failed", 500)
