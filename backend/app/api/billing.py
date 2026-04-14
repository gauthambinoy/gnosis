from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from dataclasses import asdict

from app.core.billing import billing_engine, PlanTier

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

DEMO_USER_ID = "demo-user"


# ── Pydantic models ──────────────────────────────────────────────────────────

class SubscribeRequest(BaseModel):
    plan: str = Field(min_length=1, max_length=50)


class RecordUsageRequest(BaseModel):
    metric: str = Field(min_length=1, max_length=100)
    value: float = Field(default=1, ge=0)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/plans")
async def list_plans():
    return {"plans": billing_engine.get_plans()}


@router.get("/subscription")
async def get_subscription():
    sub = billing_engine.get_or_create_subscription(DEMO_USER_ID)
    return {"subscription": asdict(sub)}


@router.post("/subscribe")
async def subscribe(body: SubscribeRequest):
    try:
        plan = PlanTier(body.plan)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {body.plan}")
    sub = billing_engine.upgrade_plan(DEMO_USER_ID, plan)
    return {"subscription": asdict(sub)}


@router.get("/usage")
async def get_usage():
    return {"usage": billing_engine.get_usage_summary(DEMO_USER_ID)}


@router.post("/usage/record")
async def record_usage(body: RecordUsageRequest):
    billing_engine.record_usage(DEMO_USER_ID, body.metric, body.value)
    return {"recorded": True, "metric": body.metric, "value": body.value}


@router.get("/quota/{metric}")
async def check_quota(metric: str):
    return {"quota": billing_engine.check_quota(DEMO_USER_ID, metric)}


@router.get("/stats")
async def billing_stats():
    return billing_engine.stats
