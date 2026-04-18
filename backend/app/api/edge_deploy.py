"""Edge deployment configuration API."""
from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user_id
from app.core.edge_deploy import edge_deploy_engine
from dataclasses import asdict
from app.core.safe_error import safe_http_error

router = APIRouter()


@router.post("")
async def create_edge_deployment(body: dict, user_id: str = Depends(get_current_user_id)):
    agent_id = body.get("agent_id")
    target = body.get("target")
    if not agent_id or not target:
        raise HTTPException(status_code=400, detail="agent_id and target are required")
    try:
        dep = edge_deploy_engine.create_deployment(agent_id, target, body.get("config"))
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)
    return asdict(dep)


@router.get("")
async def list_edge_deployments(agent_id: str = None, user_id: str = Depends(get_current_user_id)):
    deps = edge_deploy_engine.list_deployments(agent_id)
    return {"deployments": [asdict(d) for d in deps]}


@router.get("/{deployment_id}")
async def get_edge_deployment(deployment_id: str, user_id: str = Depends(get_current_user_id)):
    dep = edge_deploy_engine.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return asdict(dep)
