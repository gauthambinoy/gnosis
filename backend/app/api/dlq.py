from fastapi import APIRouter, HTTPException, Depends
from app.core.dlq import dead_letter_queue
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/dlq", tags=["observability"])


@router.get("")
async def list_entries(
    operation: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    user_id: str = Depends(get_current_user_id),
):
    return {
        "entries": dead_letter_queue.list_entries(
            operation=operation, status=status, limit=limit
        )
    }


@router.get("/stats")
async def dlq_stats(user_id: str = Depends(get_current_user_id)):
    return dead_letter_queue.stats


@router.get("/{entry_id}")
async def get_entry(entry_id: str, user_id: str = Depends(get_current_user_id)):
    entry = dead_letter_queue.get(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="DLQ entry not found")
    from dataclasses import asdict

    return asdict(entry)


@router.post("/{entry_id}/retry")
async def retry_entry(entry_id: str, user_id: str = Depends(get_current_user_id)):
    result = dead_letter_queue.retry(entry_id)
    if not result:
        raise HTTPException(status_code=404, detail="DLQ entry not found")
    return result


@router.post("/{entry_id}/resolve")
async def resolve_entry(entry_id: str, user_id: str = Depends(get_current_user_id)):
    if not dead_letter_queue.mark_resolved(entry_id):
        raise HTTPException(status_code=404, detail="DLQ entry not found")
    return {"status": "resolved"}


@router.post("/purge")
async def purge_resolved(user_id: str = Depends(get_current_user_id)):
    count = dead_letter_queue.purge_resolved()
    return {"purged": count}
