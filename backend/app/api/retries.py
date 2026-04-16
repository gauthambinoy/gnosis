from fastapi import APIRouter, Depends, Query
from app.core.retry_engine import retry_engine
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/retries", tags=["reliability"])

@router.get("")
async def list_retries(status: Optional[str] = None, limit: int = 50, user_id: str = Depends(get_current_user_id)):
    return {"records": retry_engine.list_records(status=status, limit=limit)}

@router.get("/stats")
async def retry_stats(user_id: str = Depends(get_current_user_id)):
    return retry_engine.stats

@router.get("/{execution_id}")
async def get_retry(execution_id: str, user_id: str = Depends(get_current_user_id)):
    record = retry_engine.get_record(execution_id)
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Retry record not found")
    return record
