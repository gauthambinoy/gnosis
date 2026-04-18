"""Docker export API for agents."""
from fastapi import APIRouter, Depends
from app.core.auth import get_current_user_id
from app.core.docker_exporter import docker_exporter

router = APIRouter()


@router.post("/{agent_id}")
async def export_agent_docker(agent_id: str, body: dict = None, user_id: str = Depends(get_current_user_id)):
    config = body if body else {}
    config.setdefault("name", f"agent-{agent_id}")
    result = docker_exporter.export_agent(agent_id, config)
    return result
