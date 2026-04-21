from fastapi import APIRouter, HTTPException, Depends
from app.core.auth import get_current_user_id
from app.core.version_manager import version_manager
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/agents/{agent_id}/versions", tags=["versions"])


@router.get("")
async def list_versions(agent_id: str, user_id: str = Depends(get_current_user_id)):
    versions = version_manager.get_versions(agent_id)
    return {"versions": [asdict(v) for v in versions], "total": len(versions)}


@router.get("/current")
async def get_current_version(agent_id: str, user_id: str = Depends(get_current_user_id)):
    version = version_manager.get_current(agent_id)
    if not version:
        raise HTTPException(status_code=404, detail="No versions found")
    return asdict(version)


@router.get("/stats/overview")
async def version_stats(user_id: str = Depends(get_current_user_id)):
    return version_manager.stats


@router.get("/{version_id}")
async def get_version(agent_id: str, version_id: str, user_id: str = Depends(get_current_user_id)):
    version = version_manager.get_version(agent_id, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return asdict(version)


@router.post("/{version_id}/rollback")
async def rollback_version(agent_id: str, version_id: str, user_id: str = Depends(get_current_user_id)):
    new_version = version_manager.rollback(agent_id, version_id)
    if not new_version:
        raise HTTPException(status_code=404, detail="Version not found")
    return asdict(new_version)


@router.get("/{version_a}/diff/{version_b}")
async def diff_versions(agent_id: str, version_a: str, version_b: str, user_id: str = Depends(get_current_user_id)):
    result = version_manager.diff(agent_id, version_a, version_b)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
