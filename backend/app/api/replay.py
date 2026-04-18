from fastapi import APIRouter, HTTPException
from app.core.execution_recorder import execution_recorder
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/replay", tags=["replay"])


@router.get("")
async def list_recordings(agent_id: str = None, limit: int = 50):
    recordings = execution_recorder.list_recordings(agent_id=agent_id, limit=limit)
    # Return summaries without full steps for list view
    summaries = []
    for r in recordings:
        summaries.append(
            {
                "id": r.id,
                "agent_id": r.agent_id,
                "task": r.task,
                "status": r.status,
                "total_duration_ms": r.total_duration_ms,
                "step_count": len(r.steps),
                "started_at": r.started_at,
                "completed_at": r.completed_at,
            }
        )
    return {"recordings": summaries, "total": len(summaries)}


@router.get("/stats/overview")
async def replay_stats():
    return execution_recorder.stats


@router.get("/{recording_id}")
async def get_recording(recording_id: str):
    recording = execution_recorder.get_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return asdict(recording)


@router.get("/{recording_id}/steps")
async def get_recording_steps(recording_id: str):
    recording = execution_recorder.get_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return {
        "recording_id": recording_id,
        "agent_id": recording.agent_id,
        "steps": [asdict(s) for s in recording.steps],
        "total_duration_ms": recording.total_duration_ms,
    }
