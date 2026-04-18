from fastapi import APIRouter, HTTPException, Depends
from app.core.gdpr_engine import gdpr_engine
from app.core.auth import get_current_user_id
from dataclasses import asdict
from typing import Optional, List
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/gdpr", tags=["compliance"])


@router.get("/data-inventory")
async def data_inventory(user_id: str = Depends(get_current_user_id)):
    return gdpr_engine.get_user_data_inventory(user_id)


@router.post("/erasure")
async def request_erasure(
    reason: str = "",
    categories: Optional[List[str]] = None,
    user_id: str = Depends(get_current_user_id),
):
    request = gdpr_engine.create_erasure_request(
        user_id=user_id,
        requested_by=user_id,
        reason=reason,
        data_categories=categories,
    )
    return asdict(request)


@router.post("/erasure/{request_id}/execute")
async def execute_erasure(request_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        result = await gdpr_engine.execute_erasure(request_id)
        return asdict(result)
    except ValueError as e:
        safe_http_error(e, "Operation failed", 404)


@router.get("/erasure/{request_id}")
async def get_erasure_status(
    request_id: str, user_id: str = Depends(get_current_user_id)
):
    request = gdpr_engine.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Erasure request not found")
    return asdict(request)


@router.get("/erasure")
async def list_erasure_requests(user_id: str = Depends(get_current_user_id)):
    return {"requests": gdpr_engine.list_requests(user_id=user_id)}
