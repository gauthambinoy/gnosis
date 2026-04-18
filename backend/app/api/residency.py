from fastapi import APIRouter, HTTPException, Depends
from app.core.data_residency import residency_engine
from app.core.auth import get_current_user_id
from dataclasses import asdict
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/residency", tags=["residency"])


@router.get("/policy")
async def get_policy(
    workspace_id: str = "", user_id: str = Depends(get_current_user_id)
):
    policy = residency_engine.get_policy(workspace_id)
    if not policy:
        raise HTTPException(status_code=404, detail="No residency policy found")
    return asdict(policy)


@router.put("/policy")
async def set_policy(data: dict, user_id: str = Depends(get_current_user_id)):
    try:
        policy = residency_engine.set_policy(
            workspace_id=data.get("workspace_id", ""),
            region=data.get("region", ""),
            enforced=data.get("enforced", True),
        )
        return asdict(policy)
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)


@router.get("/regions")
async def list_regions(user_id: str = Depends(get_current_user_id)):
    return {"regions": residency_engine.list_regions()}
