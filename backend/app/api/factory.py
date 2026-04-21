"""Gnosis Agent Factory API — Create AI agents from natural language."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from app.core.auth import get_current_user_id
from app.core.agent_factory import agent_factory, INTENT_TEMPLATES

router = APIRouter(prefix="/api/v1/factory", tags=["factory"])


class AnalyzeRequest(BaseModel):
    description: str = Field(
        min_length=5,
        max_length=2000,
        description="Natural language description of what you want to automate",
    )


@router.post("/analyze")
async def analyze(req: AnalyzeRequest, user_id: str = Depends(get_current_user_id)):
    """Analyze a natural language description and return a deployment plan."""
    plan = agent_factory.analyze(req.description)
    return plan


@router.get("/plans")
async def list_plans(user_id: str = Depends(get_current_user_id)):
    """List all deployment plans."""
    return agent_factory.list_plans()


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str, user_id: str = Depends(get_current_user_id)):
    """Get a specific deployment plan."""
    plan = agent_factory.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/plans/{plan_id}/deploy")
async def deploy_plan(plan_id: str, user_id: str = Depends(get_current_user_id)):
    """Deploy (approve) a plan — creates agents, pipelines, schedules."""
    plan = agent_factory.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    result = await agent_factory.deploy(plan_id)
    if "error" in result and result["error"] == "Plan not found":
        raise HTTPException(status_code=404, detail="Plan not found")
    return result


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str, user_id: str = Depends(get_current_user_id)):
    """Delete a deployment plan."""
    if not agent_factory.delete_plan(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"status": "deleted"}


@router.get("/deployments")
async def list_deployments(user_id: str = Depends(get_current_user_id)):
    """List all completed deployments."""
    return agent_factory.get_deployments()


@router.get("/intents")
async def list_intents(user_id: str = Depends(get_current_user_id)):
    """List available intent categories with their keywords."""
    return {
        name: {
            "description": config["description"],
            "keywords": config["keywords"],
            "requires": config.get("requires", []),
            "default_schedule": config.get("default_schedule"),
        }
        for name, config in INTENT_TEMPLATES.items()
    }


@router.get("/stats")
async def factory_stats(user_id: str = Depends(get_current_user_id)):
    """Get factory statistics."""
    return agent_factory.get_stats()
