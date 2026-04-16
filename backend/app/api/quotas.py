from fastapi import APIRouter, HTTPException, Depends
from app.core.quota_engine import quota_engine
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/api/v1/quotas", tags=["quotas"])

@router.get("/dashboard/{workspace_id}")
async def get_quota_dashboard(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    return quota_engine.get_dashboard(workspace_id)

@router.post("/{workspace_id}/check")
async def check_quota(workspace_id: str, resource: str, amount: int = 1, user_id: str = Depends(get_current_user_id)):
    result = quota_engine.check_quota(workspace_id, resource, amount)
    if not result["allowed"]:
        raise HTTPException(status_code=429, detail=result)
    return result

@router.post("/{workspace_id}/tier")
async def set_tier(workspace_id: str, tier: str, user_id: str = Depends(get_current_user_id)):
    try:
        quota_engine.set_tier(workspace_id, tier)
        return {"status": "ok", "workspace_id": workspace_id, "tier": tier}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reset-daily")
async def reset_daily(user_id: str = Depends(get_current_user_id)):
    quota_engine.reset_daily_counters()
    return {"status": "ok"}
