from fastapi import APIRouter

from app.core.standup_engine import standup_engine

router = APIRouter()


@router.get("/today")
async def get_today_standup():
    """Get today's standup report (backward compatible)."""
    report = await standup_engine.generate()
    return report


@router.get("/daily")
async def get_daily_standup():
    """Full daily standup report."""
    return await standup_engine.generate()


@router.get("/agent/{agent_id}")
async def get_agent_standup(agent_id: str):
    """Per-agent 24h summary."""
    return await standup_engine.get_agent_summary(agent_id)
