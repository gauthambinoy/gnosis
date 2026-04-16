from fastapi import APIRouter, Depends
from app.core.data_flow_audit import data_flow_engine
from app.core.auth import get_current_user_id
from dataclasses import asdict
from typing import Optional

router = APIRouter(prefix="/api/v1/data-flow", tags=["data-flow"])


@router.get("")
async def get_flows(source: Optional[str] = None, destination: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    return {"flows": data_flow_engine.get_flows(source=source, destination=destination)}


@router.get("/map")
async def get_flow_map(user_id: str = Depends(get_current_user_id)):
    return data_flow_engine.generate_flow_map()


@router.post("/record")
async def record_flow(data: dict, user_id: str = Depends(get_current_user_id)):
    record = data_flow_engine.record_flow(
        source=data.get("source", ""),
        destination=data.get("destination", ""),
        data_type=data.get("data_type", ""),
        purpose=data.get("purpose", ""),
        user_id=user_id,
    )
    return asdict(record)
