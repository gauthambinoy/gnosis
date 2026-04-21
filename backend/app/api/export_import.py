from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from typing import List
from app.core.auth import get_current_user_id
from app.core.agent_export import (
    export_agent,
    export_agents_bulk,
    import_agent,
    import_agents_bulk,
    validate_import,
)
import json

router = APIRouter(prefix="/api/v1/agents", tags=["export-import"])


def _get_agents_store():
    """Get the in-memory agents store from the agents module."""
    try:
        from app.api.agents import _agents

        return _agents
    except Exception:
        return {}


@router.get("/{agent_id}/export")
async def export_single_agent(agent_id: str, user_id: str = Depends(get_current_user_id)):
    agents = _get_agents_store()
    agent = agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    data = export_agent(agent)
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f"attachment; filename=gnosis-agent-{agent_id[:8]}.json"
        },
    )


@router.post("/export/bulk")
async def export_bulk(agent_ids: List[str], user_id: str = Depends(get_current_user_id)):
    agents = _get_agents_store()
    agent_list = [agents[aid] for aid in agent_ids if aid in agents]
    if not agent_list:
        raise HTTPException(status_code=404, detail="No agents found")
    data = export_agents_bulk(agent_list)
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": "attachment; filename=gnosis-agents-export.json"
        },
    )


@router.post("/import")
async def import_single_agent(data: dict, user_id: str = Depends(get_current_user_id)):
    valid, msg = validate_import(data)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    agent = import_agent(data)
    if not agent:
        raise HTTPException(status_code=400, detail="Failed to import agent")

    agents = _get_agents_store()
    agents[agent["id"]] = agent
    return {"imported": True, "agent_id": agent["id"], "agent": agent}


@router.post("/import/bulk")
async def import_bulk_agents(data: dict, user_id: str = Depends(get_current_user_id)):
    valid, msg = validate_import(data)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    agents_list = import_agents_bulk(data)
    if not agents_list:
        raise HTTPException(status_code=400, detail="No agents to import")

    agents = _get_agents_store()
    imported = []
    for agent in agents_list:
        agents[agent["id"]] = agent
        imported.append(agent["id"])

    return {"imported": True, "count": len(imported), "agent_ids": imported}


@router.post("/import/file")
async def import_from_file(file: UploadFile = File(...), user_id: str = Depends(get_current_user_id)):
    try:
        content = await file.read()
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    valid, msg = validate_import(data)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    if "agents" in data:
        agents_list = import_agents_bulk(data)
        agents = _get_agents_store()
        for agent in agents_list:
            agents[agent["id"]] = agent
        return {"imported": True, "count": len(agents_list)}
    else:
        agent = import_agent(data)
        agents = _get_agents_store()
        agents[agent["id"]] = agent
        return {"imported": True, "agent_id": agent["id"]}
