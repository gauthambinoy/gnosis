from fastapi import APIRouter, HTTPException, Depends
from app.core.consent_manager import consent_manager
from app.core.auth import get_current_user_id
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/consent", tags=["consent"])


@router.post("/grant")
async def grant_consent(data: dict, user_id: str = Depends(get_current_user_id)):
    record = consent_manager.grant_consent(
        user_id=user_id,
        purpose=data.get("purpose", ""),
        ip_address=data.get("ip_address", ""),
    )
    return asdict(record)


@router.post("/revoke")
async def revoke_consent(data: dict, user_id: str = Depends(get_current_user_id)):
    record = consent_manager.revoke_consent(
        user_id=user_id,
        purpose=data.get("purpose", ""),
    )
    if not record:
        raise HTTPException(status_code=404, detail="No active consent found for this purpose")
    return asdict(record)


@router.get("/status")
async def consent_status(purpose: str = "", user_id: str = Depends(get_current_user_id)):
    return {"consented": consent_manager.check_consent(user_id, purpose)}


@router.get("/user/{target_user_id}")
async def list_user_consents(target_user_id: str, user_id: str = Depends(get_current_user_id)):
    return {"consents": consent_manager.list_consents(target_user_id)}
