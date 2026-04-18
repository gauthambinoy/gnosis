from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.rpa_engine import rpa_engine

router = APIRouter(prefix="/api/v1/rpa", tags=["rpa"])


# ─── Request Models ───


class StartRecordingRequest(BaseModel):
    user_id: str = ""
    start_url: str = ""


class RecordActionRequest(BaseModel):
    action_type: str = "click"
    selector: str = ""
    xpath: str = ""
    value: str = ""
    description: str = ""
    x: int = 0
    y: int = 0
    wait_before_ms: int = 0
    wait_after_ms: int = 500
    page_url: str = ""
    element_tag: str = ""
    element_text: str = ""
    element_id: str = ""
    element_class: str = ""


class StopRecordingRequest(BaseModel):
    name: str = ""
    description: str = ""


class WorkflowCreateRequest(BaseModel):
    name: str = "Untitled"
    description: str = ""
    actions: list[dict] = []
    variables: dict = {}
    start_url: str = ""
    tags: list[str] = []
    schedule: str = ""
    created_by: str = ""


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    actions: Optional[list[dict]] = None
    variables: Optional[dict] = None
    start_url: Optional[str] = None
    tags: Optional[list[str]] = None
    schedule: Optional[str] = None
    status: Optional[str] = None


class ExecuteRequest(BaseModel):
    variables: dict = {}


# ─── Recording Endpoints ───


@router.post("/record/start")
async def start_recording(req: StartRecordingRequest):
    session_id = rpa_engine.start_recording(
        user_id=req.user_id, start_url=req.start_url
    )
    return {"session_id": session_id}


@router.post("/record/{session_id}/action")
async def record_action(session_id: str, req: RecordActionRequest):
    result = rpa_engine.record_action(session_id, req.model_dump())
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/record/{session_id}/actions")
async def get_recording_actions(session_id: str):
    actions = rpa_engine.get_recording_actions(session_id)
    return {"session_id": session_id, "actions": actions, "count": len(actions)}


@router.post("/record/{session_id}/stop")
async def stop_recording(session_id: str, req: StopRecordingRequest):
    result = rpa_engine.stop_recording(
        session_id, name=req.name, description=req.description
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Recording session not found")
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─── Workflow CRUD ───


@router.get("/workflows")
async def list_workflows(tag: str = "", status: str = ""):
    workflows = rpa_engine.list_workflows(tag=tag, status=status)
    return {"workflows": workflows, "total": len(workflows)}


@router.post("/workflows")
async def create_workflow(req: WorkflowCreateRequest):
    return rpa_engine.create_workflow(req.model_dump())


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    wf = rpa_engine.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.put("/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, req: WorkflowUpdateRequest):
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    wf = rpa_engine.update_workflow(workflow_id, data)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    if not rpa_engine.delete_workflow(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"deleted": True}


@router.post("/workflows/{workflow_id}/duplicate")
async def duplicate_workflow(workflow_id: str):
    wf = rpa_engine.duplicate_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


# ─── Execution ───


@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, req: ExecuteRequest):
    result = await rpa_engine.execute_workflow(workflow_id, variables=req.variables)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/workflows/{workflow_id}/stop")
async def stop_execution(workflow_id: str):
    stopped = rpa_engine.stop_execution(workflow_id)
    return {"stopped": stopped}


@router.get("/workflows/{workflow_id}/script")
async def generate_script(workflow_id: str):
    script = rpa_engine.generate_playwright_script(workflow_id)
    if script is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"script": script, "language": "python", "framework": "playwright"}


# ─── Executions ───


@router.get("/executions")
async def list_executions(workflow_id: str = ""):
    execs = rpa_engine.list_executions(workflow_id=workflow_id)
    return {"executions": execs, "total": len(execs)}


@router.get("/executions/{run_id}")
async def get_execution(run_id: str):
    ex = rpa_engine.get_execution(run_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ex


# ─── Stats ───


@router.get("/stats")
async def get_stats():
    return rpa_engine.get_stats()
