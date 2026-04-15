"""First-time user onboarding tracking."""
from fastapi import APIRouter, Depends
from app.core.auth import get_current_user_id
from typing import Dict
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])

# In-memory onboarding state
_onboarding: Dict[str, dict] = {}

ONBOARDING_STEPS = [
    {"id": "welcome", "title": "Welcome to Gnosis", "description": "Your AI agent platform is ready"},
    {"id": "create_agent", "title": "Create Your First Agent", "description": "Describe what you need and Gnosis builds it"},
    {"id": "first_execution", "title": "Run Your First Task", "description": "See your agent in action"},
    {"id": "explore_memory", "title": "Explore Agent Memory", "description": "See how your agent learns and remembers"},
    {"id": "connect_llm", "title": "Connect Your LLM", "description": "Add your OpenRouter or API key"},
    {"id": "invite_team", "title": "Invite Your Team", "description": "Collaborate on agents and workflows"},
]

@router.get("/status")
async def get_onboarding_status(user_id: str = Depends(get_current_user_id)):
    if user_id not in _onboarding:
        _onboarding[user_id] = {
            "completed_steps": [],
            "current_step": "welcome",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed": False,
        }
    state = _onboarding[user_id]
    completed_ids = set(state["completed_steps"])
    steps = [
        {**step, "completed": step["id"] in completed_ids}
        for step in ONBOARDING_STEPS
    ]
    progress = len(completed_ids) / len(ONBOARDING_STEPS) * 100
    return {"steps": steps, "progress": round(progress, 1), "completed": state["completed"], "current_step": state["current_step"]}

@router.post("/complete/{step_id}")
async def complete_step(step_id: str, user_id: str = Depends(get_current_user_id)):
    if user_id not in _onboarding:
        _onboarding[user_id] = {"completed_steps": [], "current_step": "welcome", "started_at": datetime.now(timezone.utc).isoformat(), "completed": False}
    state = _onboarding[user_id]
    if step_id not in state["completed_steps"]:
        state["completed_steps"].append(step_id)

    # Find next step
    completed_ids = set(state["completed_steps"])
    for step in ONBOARDING_STEPS:
        if step["id"] not in completed_ids:
            state["current_step"] = step["id"]
            break
    else:
        state["completed"] = True
        state["current_step"] = "done"

    return {"step_id": step_id, "completed": True, "next_step": state["current_step"], "all_done": state["completed"]}

@router.post("/skip")
async def skip_onboarding(user_id: str = Depends(get_current_user_id)):
    _onboarding[user_id] = {"completed_steps": [s["id"] for s in ONBOARDING_STEPS], "current_step": "done", "started_at": datetime.now(timezone.utc).isoformat(), "completed": True}
    return {"status": "skipped"}
