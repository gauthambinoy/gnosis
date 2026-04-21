import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.rpa_engine import rpa_engine
from app.core.error_handling import ValidationError

router = APIRouter(prefix="/api/v1/rpa", tags=["rpa"])


# ─── Selector / xpath validation ───

_DANGEROUS_PATTERNS = (
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"\bon[a-z]+\s*=", re.IGNORECASE),
    re.compile(r"expression\s*\(", re.IGNORECASE),
)


def _validate_selector_value(value: str, field: str) -> None:
    """Reject obvious selector/xpath injection vectors."""
    if not value:
        return
    if len(value) > 1024:
        raise ValidationError(f"{field} exceeds 1024 character limit")
    if "<" in value or ">" in value:
        raise ValidationError(
            f"{field} may not contain '<' or '>' characters"
        )
    for pat in _DANGEROUS_PATTERNS:
        if pat.search(value):
            raise ValidationError(f"{field} contains a forbidden pattern")


def _validate_record_action(req: "RecordActionRequest") -> None:
    _validate_selector_value(req.selector, "selector")
    _validate_selector_value(req.xpath, "xpath")


def _validate_workflow_actions(actions: list[dict] | None) -> None:
    if not actions:
        return
    for idx, action in enumerate(actions):
        for field in ("selector", "xpath"):
            value = action.get(field)
            if isinstance(value, str):
                _validate_selector_value(value, f"actions[{idx}].{field}")


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
    _validate_record_action(req)
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
    _validate_workflow_actions(req.actions)
    return rpa_engine.create_workflow(req.model_dump())


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    wf = rpa_engine.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.put("/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, req: WorkflowUpdateRequest):
    _validate_workflow_actions(req.actions)
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
