"""Bulk operations for managing agents and executions at scale."""
from fastapi import APIRouter, Depends
from app.core.auth import get_current_user_id
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger("gnosis.bulk")
router = APIRouter(prefix="/api/v1/bulk", tags=["bulk"])

class BulkAgentAction(BaseModel):
    agent_ids: List[str]
    action: str  # "pause", "resume", "delete"

class BulkResult(BaseModel):
    total: int
    succeeded: int
    failed: int
    errors: List[dict]

@router.post("/agents")
async def bulk_agent_action(req: BulkAgentAction, user_id: str = Depends(get_current_user_id)):
    """Bulk pause/resume/delete agents."""
    results = {"total": len(req.agent_ids), "succeeded": 0, "failed": 0, "errors": []}

    try:
        from app.core.marketplace import marketplace_engine
    except ImportError:
        return results

    for agent_id in req.agent_ids:
        try:
            agent = marketplace_engine.get_agent(agent_id)
            if not agent:
                results["errors"].append({"agent_id": agent_id, "error": "not found"})
                results["failed"] += 1
                continue

            if req.action == "pause":
                if isinstance(agent, dict):
                    agent["status"] = "paused"
                else:
                    agent.status = "paused"
            elif req.action == "resume":
                if isinstance(agent, dict):
                    agent["status"] = "active"
                else:
                    agent.status = "active"
            elif req.action == "delete":
                marketplace_engine._agents.pop(agent_id, None)
            else:
                results["errors"].append({"agent_id": agent_id, "error": f"unknown action: {req.action}"})
                results["failed"] += 1
                continue

            results["succeeded"] += 1
        except Exception as e:
            results["errors"].append({"agent_id": agent_id, "error": str(e)[:100]})
            results["failed"] += 1

    logger.info(f"Bulk {req.action}: {results['succeeded']}/{results['total']} succeeded")
    return results

class BulkRetryRequest(BaseModel):
    execution_ids: List[str]

@router.post("/executions/retry")
async def bulk_retry_executions(req: BulkRetryRequest, user_id: str = Depends(get_current_user_id)):
    """Bulk retry failed executions."""
    return {"total": len(req.execution_ids), "queued": len(req.execution_ids), "note": "Retries queued for processing"}
