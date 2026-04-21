"""
Gnosis System Control — REST API
Secure endpoints for OS/system management.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from app.core.auth import get_current_user_id
from app.core.system_control import system_control

router = APIRouter()


class ExecuteRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=500)
    timeout: int = Field(default=30, ge=1, le=60)


# ─── System Info ───


@router.get("/info")
async def get_system_info(user_id: str = Depends(get_current_user_id)):
    """Get comprehensive system information (CPU, RAM, disk, OS)."""
    return system_control.get_system_info()


@router.get("/processes")
async def get_processes(top_n: int = Query(default=30, ge=1, le=100), user_id: str = Depends(get_current_user_id)):
    """Get top processes by CPU/memory usage."""
    return {"processes": system_control.list_processes(top_n=top_n)}


@router.get("/network")
async def get_network(user_id: str = Depends(get_current_user_id)):
    """Get active network connections."""
    return {"connections": system_control.get_network_connections()}


@router.get("/services")
async def get_services(user_id: str = Depends(get_current_user_id)):
    """Get status of key infrastructure services."""
    return {"services": system_control.get_running_services()}


# ─── Command Execution ───


@router.post("/execute")
async def execute_command(
    req: ExecuteRequest, user_id: str = Depends(get_current_user_id)
):
    """Execute a whitelisted system command with full auditing."""
    result = await system_control.execute_command(
        command=req.command,
        user_id=user_id,
        timeout=req.timeout,
    )
    return result


# ─── File Browser ───


@router.get("/files")
async def list_directory(path: str = Query(default="/app", max_length=500), user_id: str = Depends(get_current_user_id)):
    """List directory contents safely."""
    return system_control.list_directory(path=path)


@router.get("/files/read")
async def read_file(
    path: str = Query(..., max_length=500),
    max_lines: int = Query(default=200, ge=1, le=1000),
    user_id: str = Depends(get_current_user_id),
):
    """Read a file's contents (text only, limited size)."""
    result = system_control.read_file(path=path, max_lines=max_lines)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─── Docker ───


@router.get("/docker")
async def get_docker_status(user_id: str = Depends(get_current_user_id)):
    """Get Docker availability and container status."""
    status = system_control.get_docker_status()
    containers = await system_control.docker_ps()
    stats = await system_control.docker_stats()
    return {"status": status, "containers": containers, "stats": stats}


@router.get("/docker/{container}/logs")
async def get_docker_logs(
    container: str,
    lines: int = Query(default=50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
):
    """Get Docker container logs."""
    return await system_control.docker_logs(container=container, lines=lines)


# ─── Audit & History ───


@router.get("/audit")
async def get_audit_log(limit: int = Query(default=50, ge=1, le=200), user_id: str = Depends(get_current_user_id)):
    """Get the system control audit log."""
    return {"entries": system_control.get_audit_log(limit=limit)}


@router.get("/commands")
async def get_command_history(limit: int = Query(default=50, ge=1, le=200), user_id: str = Depends(get_current_user_id)):
    """Get command execution history."""
    return {"commands": system_control.get_command_history(limit=limit)}
