from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.oracle_engine import OracleEngine

router = APIRouter()
oracle = OracleEngine()


@router.get("/insights")
async def get_insights(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Get proactive insights from the Oracle engine."""
    insights = await oracle.generate_insights(db)
    limited = insights[:limit]
    return {"insights": limited, "total": len(insights)}


@router.get("/health")
async def get_health(db: AsyncSession = Depends(get_db)):
    """Get overall platform health score."""
    health = await oracle.get_health_score(db)
    return health


@router.get("/recommendations")
async def get_recommendations(db: AsyncSession = Depends(get_db)):
    """Get actionable suggestions for improving agent performance."""
    recs = await oracle.get_recommendations(db)
    return {"recommendations": recs, "total": len(recs)}
