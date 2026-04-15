"""Agent export/import as portable JSON bundles."""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from app.core.auth import get_current_user_id
import json
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.export")
router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

EXPORT_VERSION = "1.0"

@router.get("/{agent_id}/export")
async def export_agent(agent_id: str, user_id: str = Depends(get_current_user_id)):
    """Export agent as a portable JSON bundle."""
    try:
        from app.core.marketplace import marketplace_engine
    except ImportError:
        raise HTTPException(status_code=500, detail="Marketplace unavailable")

    agent = marketplace_engine.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    data = agent if isinstance(agent, dict) else (agent.__dict__.copy() if hasattr(agent, '__dict__') else {})

    bundle = {
        "_gnosis_export": True,
        "_version": EXPORT_VERSION,
        "_exported_at": datetime.now(timezone.utc).isoformat(),
        "_exported_by": user_id,
        "agent": {k: v for k, v in data.items() if not k.startswith("_") and k not in ("owner_id",)},
    }

    # Include memory summary if available
    try:
        from app.core.memory_engine import memory_engine
        memories = await memory_engine.get_agent_memories(agent_id, limit=100)
        bundle["memories"] = [{"tier": m.tier, "content": m.content, "metadata": m.metadata} for m in memories]
    except Exception:
        bundle["memories"] = []

    return JSONResponse(
        content=bundle,
        headers={"Content-Disposition": f'attachment; filename="gnosis-agent-{agent_id[:8]}.json"'},
    )


@router.post("/import")
async def import_agent(file: UploadFile = File(...), user_id: str = Depends(get_current_user_id)):
    """Import agent from a JSON bundle."""
    content = await file.read()
    try:
        bundle = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    if not bundle.get("_gnosis_export"):
        raise HTTPException(status_code=400, detail="Not a valid Gnosis export file")

    agent_data = bundle.get("agent", {})
    if not agent_data:
        raise HTTPException(status_code=400, detail="No agent data in bundle")

    # Create new agent with fresh ID
    new_id = str(uuid.uuid4())
    agent_data["id"] = new_id
    agent_data["name"] = f"{agent_data.get('name', 'Imported Agent')} (Imported)"
    agent_data["created_at"] = datetime.now(timezone.utc).isoformat()
    agent_data["total_executions"] = 0
    agent_data["imported_from"] = bundle.get("_exported_at", "unknown")

    try:
        from app.core.marketplace import marketplace_engine
        marketplace_engine._agents[new_id] = agent_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {e}")

    # Import memories if present
    memory_count = 0
    if bundle.get("memories"):
        try:
            from app.core.memory_engine import memory_engine
            for mem in bundle["memories"]:
                await memory_engine.store(new_id, mem.get("tier", "semantic"), mem.get("content", ""), mem.get("metadata"))
                memory_count += 1
        except Exception:
            pass

    logger.info(f"Agent imported: {new_id} with {memory_count} memories by {user_id}")
    return {"id": new_id, "name": agent_data["name"], "memories_imported": memory_count}
