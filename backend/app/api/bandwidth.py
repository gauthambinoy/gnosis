"""Bandwidth optimization API."""
from fastapi import APIRouter, Depends
from app.core.auth import get_current_user_id
from app.core.compression import compression_engine

router = APIRouter()


@router.post("/compress")
async def compress_data(body: dict, user_id: str = Depends(get_current_user_id)):
    data = body.get("data", body)
    previous_hash = body.get("previous_hash")
    result = compression_engine.compress_response(data, previous_hash)
    return result


@router.get("/stats")
async def bandwidth_stats(user_id: str = Depends(get_current_user_id)):
    return compression_engine.get_stats()
