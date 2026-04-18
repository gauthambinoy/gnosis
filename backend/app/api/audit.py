from fastapi import APIRouter, Depends
from app.middleware.audit_log import audit_store
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/recent")
async def recent_requests(
    limit: int = 50,
    path: Optional[str] = None,
    method: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
):
    return {
        "records": audit_store.recent(
            limit=limit, path_filter=path, method_filter=method
        )
    }


@router.get("/stats")
async def audit_stats(user_id: str = Depends(get_current_user_id)):
    return audit_store.stats
