from fastapi import APIRouter, HTTPException, Depends
from app.core.dpa_registry import dpa_registry
from app.core.auth import get_current_user_id
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/dpa", tags=["compliance"])

@router.post("")
async def register_dpa(data: dict, user_id: str = Depends(get_current_user_id)):
    dpa = dpa_registry.register(**data)
    return asdict(dpa)

@router.get("")
async def list_dpas(user_id: str = Depends(get_current_user_id)):
    return {"agreements": dpa_registry.list_all()}

@router.get("/summary")
async def provider_summary(user_id: str = Depends(get_current_user_id)):
    return {"providers": dpa_registry.provider_summary()}

@router.get("/check/{provider}")
async def check_compliance(provider: str, user_id: str = Depends(get_current_user_id)):
    return dpa_registry.check_compliance(provider)

@router.get("/{dpa_id}")
async def get_dpa(dpa_id: str, user_id: str = Depends(get_current_user_id)):
    dpa = dpa_registry.get(dpa_id)
    if not dpa:
        raise HTTPException(status_code=404, detail="DPA not found")
    return asdict(dpa)
