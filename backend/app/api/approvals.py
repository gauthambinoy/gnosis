from fastapi import APIRouter, HTTPException, Depends
from app.core.approval_gates import approval_engine
from app.core.auth import get_current_user_id
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


@router.post("/gate")
async def create_gate(data: dict, user_id: str = Depends(get_current_user_id)):
    gate = approval_engine.create_gate(
        pipeline_id=data.get("pipeline_id", ""),
        step_index=data.get("step_index", 0),
        required_approvers=data.get("required_approvers", []),
    )
    return asdict(gate)


@router.post("/{gate_id}/approve")
async def approve_gate(gate_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        gate = approval_engine.approve(gate_id, user_id)
        return asdict(gate)
    except KeyError:
        raise HTTPException(status_code=404, detail="Gate not found")


@router.post("/{gate_id}/reject")
async def reject_gate(
    gate_id: str, data: dict = None, user_id: str = Depends(get_current_user_id)
):
    data = data or {}
    try:
        gate = approval_engine.reject(gate_id, user_id, reason=data.get("reason", ""))
        return asdict(gate)
    except KeyError:
        raise HTTPException(status_code=404, detail="Gate not found")


@router.get("/pipeline/{pipeline_id}")
async def list_pipeline_gates(
    pipeline_id: str, user_id: str = Depends(get_current_user_id)
):
    return {"gates": approval_engine.list_pipeline_gates(pipeline_id)}
