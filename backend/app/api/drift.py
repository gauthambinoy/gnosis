from fastapi import APIRouter, Depends
from app.core.drift_detector import drift_detector_engine
from app.core.auth import get_current_user_id
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/drift", tags=["drift"])


class RecordMetricRequest(BaseModel):
    agent_id: str
    metric: str
    value: float


@router.post("/record")
async def record_metric(req: RecordMetricRequest, user_id: str = Depends(get_current_user_id)):
    return drift_detector_engine.record_metric(req.agent_id, req.metric, req.value)


@router.get("/{agent_id}")
async def check_drift(agent_id: str, user_id: str = Depends(get_current_user_id)):
    reports = drift_detector_engine.check_drift(agent_id)
    return {"agent_id": agent_id, "drift_reports": reports}
