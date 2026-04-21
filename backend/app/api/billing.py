from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from dataclasses import asdict

from app.core.billing import billing_engine, PlanTier
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


# ── Pydantic models ──────────────────────────────────────────────────────────


class SubscribeRequest(BaseModel):
    plan: str = Field(min_length=1, max_length=50)


class RecordUsageRequest(BaseModel):
    metric: str = Field(min_length=1, max_length=100)
    value: float = Field(default=1, ge=0)


# ── Routes ────────────────────────────────────────────────────────────────────


# PUBLIC: pricing plan catalog is shown on the marketing/pricing page pre-login
@router.get("/plans")
async def list_plans():
    return {"plans": billing_engine.get_plans()}


@router.get("/subscription")
async def get_subscription(user_id: str = Depends(get_current_user_id)):
    sub = billing_engine.get_or_create_subscription(user_id)
    return {"subscription": asdict(sub)}


@router.post("/subscribe")
async def subscribe(
    body: SubscribeRequest, user_id: str = Depends(get_current_user_id)
):
    try:
        plan = PlanTier(body.plan)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {body.plan}")
    sub = billing_engine.upgrade_plan(user_id, plan)
    return {"subscription": asdict(sub)}


@router.get("/usage")
async def get_usage(user_id: str = Depends(get_current_user_id)):
    return {"usage": billing_engine.get_usage_summary(user_id)}


@router.post("/usage/record")
async def record_usage(
    body: RecordUsageRequest, user_id: str = Depends(get_current_user_id)
):
    billing_engine.record_usage(user_id, body.metric, body.value)
    return {"recorded": True, "metric": body.metric, "value": body.value}


@router.get("/quota/{metric}")
async def check_quota(metric: str, user_id: str = Depends(get_current_user_id)):
    return {"quota": billing_engine.check_quota(user_id, metric)}


@router.get("/stats")
async def billing_stats(user_id: str = Depends(get_current_user_id)):
    return billing_engine.stats
