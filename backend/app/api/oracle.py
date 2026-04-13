from fastapi import APIRouter

router = APIRouter()


@router.get("/insights")
async def get_insights(limit: int = 20):
    """Get proactive insights from the Oracle engine."""
    return {"insights": [], "total": 0}
