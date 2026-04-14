"""Gnosis Auto-API Discovery — Connect to any API by name."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.core.auto_api import auto_api

router = APIRouter(prefix="/api/v1/apis", tags=["auto-api"])


# ─── Request Models ───

class ConnectRequest(BaseModel):
    api_name: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1, max_length=500)
    extra_config: Optional[dict] = None


class CallAPIRequest(BaseModel):
    endpoint_path: str = Field(min_length=1)
    method: str = Field(default="GET")
    body: Optional[dict] = None
    params: Optional[dict] = None


# ─── Catalog ───

@router.get("/catalog")
async def list_catalog(category: Optional[str] = Query(None)):
    """List all known APIs in the catalog."""
    apis = auto_api.list_catalog(category=category or "")
    return {"apis": apis, "count": len(apis)}


@router.get("/catalog/{name}")
async def get_api_info(name: str):
    """Get detailed info about a specific API."""
    info = auto_api.get_api_info(name)
    if not info:
        raise HTTPException(status_code=404, detail=f"API '{name}' not found in catalog")
    return info


@router.get("/search")
async def search_apis(q: str = Query(..., min_length=1, description="Search query")):
    """Search APIs by name, description, or category."""
    results = auto_api.search_api(q)
    return {"results": results, "count": len(results)}


@router.get("/categories")
async def list_categories():
    """List all API categories."""
    categories = auto_api.get_categories()
    return {"categories": sorted(categories)}


# ─── Connections ───

@router.post("/connect")
async def connect_api(req: ConnectRequest):
    """Connect to an API with credentials."""
    result = auto_api.connect(req.api_name, req.api_key, req.extra_config)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/connections")
async def list_connections():
    """List all API connections."""
    connections = auto_api.list_connections()
    # Mask API keys in response
    for c in connections:
        if c.get("api_key"):
            c["api_key"] = c["api_key"][:4] + "***"
    return {"connections": connections, "count": len(connections)}


@router.get("/connections/{connection_id}")
async def get_connection(connection_id: str):
    """Get a specific connection (key masked)."""
    conn = auto_api.get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn


@router.post("/connections/{connection_id}/test")
async def test_connection(connection_id: str):
    """Test an API connection."""
    result = await auto_api.test_connection(connection_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/connections/{connection_id}/call")
async def call_api(connection_id: str, req: CallAPIRequest):
    """Make an API call through a connection."""
    result = await auto_api.call_api(
        connection_id, req.endpoint_path, req.method, req.body, req.params
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: str):
    """Delete an API connection."""
    removed = auto_api.delete_connection(connection_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"status": "deleted", "connection_id": connection_id}


# ─── Code Generation ───

@router.get("/generate/{name}")
async def generate_connector(name: str):
    """Generate a Python connector class for an API."""
    code = auto_api.generate_connector_code(name)
    if not code:
        raise HTTPException(status_code=404, detail=f"API '{name}' not found")
    return {"api": name, "language": "python", "code": code}


# ─── Stats ───

@router.get("/stats")
async def get_stats():
    """Get Auto-API engine statistics."""
    return auto_api.get_stats()
