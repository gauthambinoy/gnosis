"""Execution priority queue API."""
from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user_id
from app.core.exec_queue import execution_queue
from dataclasses import asdict

router = APIRouter()


@router.post("")
async def enqueue_execution(body: dict, user_id: str = Depends(get_current_user_id)):
    agent_id = body.get("agent_id")
    task = body.get("task")
    if not agent_id or not task:
        raise HTTPException(status_code=400, detail="agent_id and task are required")
    priority = body.get("priority", 5)
    item = execution_queue.enqueue(agent_id, task, priority, user_id)
    return asdict(item)


@router.get("")
async def list_queue(user_id: str = Depends(get_current_user_id)):
    items = execution_queue.list_queue()
    return {"queue": [asdict(i) for i in items], "total": len(items)}


@router.get("/{item_id}/position")
async def get_queue_position(item_id: str, user_id: str = Depends(get_current_user_id)):
    position = execution_queue.get_position(item_id)
    if position is None:
        raise HTTPException(status_code=404, detail="Item not found in queue")
    return {"id": item_id, "position": position}


@router.delete("/{item_id}")
async def cancel_execution(item_id: str, user_id: str = Depends(get_current_user_id)):
    if not execution_queue.cancel(item_id):
        raise HTTPException(status_code=404, detail="Item not found or already processed")
    return {"id": item_id, "status": "cancelled"}
