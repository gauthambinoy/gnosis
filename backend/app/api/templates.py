from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

from app.core.templates import WORKFLOW_TEMPLATES
from app.core.event_bus import event_bus, Events

router = APIRouter()


class DeployRequest(BaseModel):
    name: Optional[str] = None
    personality: Optional[str] = "professional"


@router.get("")
async def list_templates(category: Optional[str] = None):
    """List all workflow templates, optionally filtered by category."""
    templates = WORKFLOW_TEMPLATES
    if category:
        templates = [t for t in templates if t["category"] == category]
    return {
        "templates": templates,
        "total": len(templates),
        "categories": sorted(set(t["category"] for t in WORKFLOW_TEMPLATES)),
    }


@router.get("/{template_id}")
async def get_template(template_id: str):
    """Get a specific template by ID."""
    for t in WORKFLOW_TEMPLATES:
        if t["id"] == template_id:
            return t
    raise HTTPException(status_code=404, detail="Template not found")


@router.post("/{template_id}/deploy")
async def deploy_template(template_id: str, body: DeployRequest = DeployRequest()):
    """Create an agent from a workflow template."""
    template = None
    for t in WORKFLOW_TEMPLATES:
        if t["id"] == template_id:
            template = t
            break
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    now = datetime.now(timezone.utc).isoformat()
    agent_id = str(uuid.uuid4())
    agent = {
        "id": agent_id,
        "name": body.name or template["name"],
        "description": template["description"],
        "personality": body.personality or "professional",
        "avatar_emoji": template["emoji"],
        "status": "idle",
        "trigger_type": template["trigger"],
        "trigger_config": {},
        "trust_level": 0,
        "total_executions": 0,
        "successful_executions": 0,
        "failed_executions": 0,
        "total_corrections": 0,
        "accuracy": 0.0,
        "avg_latency_ms": 0.0,
        "total_tokens_used": 0,
        "total_cost_usd": 0.0,
        "time_saved_minutes": 0.0,
        "memory_count": 0,
        "integrations": template["integrations"],
        "guardrails": template["guardrails"],
        "steps": template["steps"],
        "template_id": template["id"],
        "created_at": now,
        "updated_at": now,
    }

    await event_bus.emit(
        Events.AGENT_CREATED,
        {"agent_id": agent_id, "name": agent["name"], "template": template_id},
    )

    return {
        "status": "deployed",
        "agent": agent,
        "template_id": template_id,
    }
