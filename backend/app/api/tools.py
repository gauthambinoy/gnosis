from fastapi import APIRouter, HTTPException, Depends, Query
from app.core.tool_registry import tool_registry
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


@router.post("/register")
async def register_tool(data: dict, user_id: str = Depends(get_current_user_id)):
    tool = tool_registry.register(
        tool_id=data.get("id", ""),
        name=data.get("name", ""),
        description=data.get("description", ""),
        category=data.get("category", "custom"),
        schema=data.get("schema", {}),
        implementation=data.get("implementation", ""),
        workspace_id=data.get("workspace_id"),
        created_by=user_id,
        is_public=data.get("is_public", False),
        tags=data.get("tags", []),
    )
    from dataclasses import asdict

    return asdict(tool)


@router.get("")
async def list_tools(
    category: Optional[str] = None,
    workspace_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
):
    return {
        "tools": tool_registry.list_tools(category=category, workspace_id=workspace_id)
    }


@router.get("/search")
async def search_tools(
    q: str = Query(...), user_id: str = Depends(get_current_user_id)
):
    return {"results": tool_registry.search(q)}


@router.get("/{tool_id}")
async def get_tool(tool_id: str, user_id: str = Depends(get_current_user_id)):
    tool = tool_registry.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    from dataclasses import asdict

    return asdict(tool)


@router.post("/{tool_id}/grant/{agent_id}")
async def grant_access(
    tool_id: str, agent_id: str, user_id: str = Depends(get_current_user_id)
):
    tool_registry.grant_access(agent_id, tool_id)
    return {"status": "granted"}


@router.post("/{tool_id}/deprecate")
async def deprecate_tool(
    tool_id: str, message: str = "", user_id: str = Depends(get_current_user_id)
):
    tool_registry.deprecate(tool_id, message)
    return {"status": "deprecated"}
