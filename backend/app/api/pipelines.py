from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from app.core.auth import get_current_user_id
from app.core.pipeline import pipeline_engine
from dataclasses import asdict
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/pipelines", tags=["pipelines"])


class StepInput(BaseModel):
    agent_id: str
    name: str = "Untitled Step"
    transform_input: Optional[str] = None
    condition: Optional[str] = None
    timeout_seconds: int = 300
    max_retries: int = 1


class CreatePipelineRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    steps: List[StepInput] = Field(default_factory=list)


class UpdatePipelineRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class AddStepRequest(BaseModel):
    agent_id: str
    name: str = "New Step"
    transform_input: Optional[str] = None
    condition: Optional[str] = None


class ExecutePipelineRequest(BaseModel):
    input_data: dict = Field(default_factory=dict)


@router.post("")
async def create_pipeline(req: CreatePipelineRequest, user_id: str = Depends(get_current_user_id)):
    steps = [s.model_dump() for s in req.steps]
    pipeline = pipeline_engine.create_pipeline(
        name=req.name, description=req.description, steps=steps
    )
    return asdict(pipeline)


@router.get("")
async def list_pipelines(user_id: str = Depends(get_current_user_id)):
    pipelines = pipeline_engine.list_pipelines()
    return {"pipelines": [asdict(p) for p in pipelines], "total": len(pipelines)}


@router.get("/stats")
async def pipeline_stats(user_id: str = Depends(get_current_user_id)):
    return pipeline_engine.stats


@router.get("/{pipeline_id}")
async def get_pipeline(pipeline_id: str, user_id: str = Depends(get_current_user_id)):
    pipeline = pipeline_engine.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return asdict(pipeline)


@router.patch("/{pipeline_id}")
async def update_pipeline(pipeline_id: str, req: UpdatePipelineRequest, user_id: str = Depends(get_current_user_id)):
    updates = req.model_dump(exclude_none=True)
    pipeline = pipeline_engine.update_pipeline(pipeline_id, **updates)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return asdict(pipeline)


@router.delete("/{pipeline_id}")
async def delete_pipeline(pipeline_id: str, user_id: str = Depends(get_current_user_id)):
    if not pipeline_engine.delete_pipeline(pipeline_id):
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"deleted": True}


@router.post("/{pipeline_id}/steps")
async def add_step(pipeline_id: str, req: AddStepRequest, user_id: str = Depends(get_current_user_id)):
    step = pipeline_engine.add_step(
        pipeline_id,
        req.agent_id,
        req.name,
        transform_input=req.transform_input,
        condition=req.condition,
    )
    if not step:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return asdict(step)


@router.delete("/{pipeline_id}/steps/{step_id}")
async def remove_step(pipeline_id: str, step_id: str, user_id: str = Depends(get_current_user_id)):
    if not pipeline_engine.remove_step(pipeline_id, step_id):
        raise HTTPException(status_code=404, detail="Pipeline or step not found")
    return {"deleted": True}


@router.post("/{pipeline_id}/execute")
async def execute_pipeline(pipeline_id: str, req: ExecutePipelineRequest, user_id: str = Depends(get_current_user_id)):
    try:
        run = await pipeline_engine.execute(pipeline_id, initial_input=req.input_data)
        return asdict(run)
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)


@router.get("/{pipeline_id}/runs")
async def list_pipeline_runs(pipeline_id: str, user_id: str = Depends(get_current_user_id)):
    runs = pipeline_engine.list_runs(pipeline_id=pipeline_id)
    return {"runs": [asdict(r) for r in runs], "total": len(runs)}


@router.get("/runs/{run_id}")
async def get_pipeline_run(run_id: str, user_id: str = Depends(get_current_user_id)):
    run = pipeline_engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return asdict(run)
