from fastapi import APIRouter, Depends
from app.core.redis_batcher import redis_batcher
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/api/v1/redis", tags=["performance"])


@router.get("/metrics")
async def get_redis_metrics(user_id: str = Depends(get_current_user_id)):
    return redis_batcher.metrics
