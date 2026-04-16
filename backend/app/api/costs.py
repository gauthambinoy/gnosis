from fastapi import APIRouter, Depends, Query
from app.core.cost_tracker import cost_tracker
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/costs", tags=["observability"])

@router.get("/summary")
async def get_summary(user_id: str = Depends(get_current_user_id)):
    return cost_tracker.total_stats

@router.get("/today")
async def get_today(user_id: str = Depends(get_current_user_id)):
    return cost_tracker.today_stats

@router.get("/by-agent/{agent_id}")
async def get_by_agent(agent_id: str, user_id: str = Depends(get_current_user_id)):
    return cost_tracker.agent_stats(agent_id)

@router.get("/recent")
async def get_recent(limit: int = 50, user_id: str = Depends(get_current_user_id)):
    return {"records": cost_tracker.recent_records(limit=limit)}
