from fastapi import APIRouter

router = APIRouter()


@router.get("/today")
async def get_today_standup():
    """Get today's standup report."""
    return {
        "date": "2026-04-13",
        "agents": [],
        "total_actions": 0,
        "time_saved_minutes": 0,
        "accuracy": 0.0,
    }
