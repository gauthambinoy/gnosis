"""Global search across all entities."""
from fastapi import APIRouter, Depends, Query
from app.core.auth import get_current_user_id
import logging

logger = logging.getLogger("gnosis.search")

router = APIRouter(prefix="/api/v1/search", tags=["search"])

@router.get("")
async def global_search(q: str = Query(..., min_length=1, max_length=200), user_id: str = Depends(get_current_user_id)):
    """Search across agents, executions, pipelines, files, and memories."""
    results = {"query": q, "agents": [], "pipelines": [], "files": [], "memories": [], "total": 0}
    query_lower = q.lower()

    # Search agents
    try:
        from app.core.marketplace import marketplace_engine
        for agent_id, agent in list(marketplace_engine._agents.items())[:1000]:
            name = getattr(agent, "name", str(agent.get("name", ""))) if isinstance(agent, dict) else getattr(agent, "name", "")
            desc = getattr(agent, "description", str(agent.get("description", ""))) if isinstance(agent, dict) else getattr(agent, "description", "")
            if query_lower in str(name).lower() or query_lower in str(desc).lower():
                results["agents"].append({"id": agent_id, "name": name, "type": "agent"})
    except Exception:
        pass

    # Search pipelines
    try:
        from app.core.pipeline import pipeline_engine
        for pid, pipeline in list(pipeline_engine._pipelines.items()):
            if query_lower in pipeline.name.lower() or query_lower in pipeline.description.lower():
                results["pipelines"].append({"id": pid, "name": pipeline.name, "type": "pipeline"})
    except Exception:
        pass

    # Search files
    try:
        from app.core.file_manager import file_manager
        for fid, record in list(file_manager._files.items()):
            if query_lower in record.original_name.lower() or any(query_lower in t.lower() for t in record.tags):
                results["files"].append({"id": fid, "name": record.original_name, "type": "file"})
    except Exception:
        pass

    results["total"] = sum(len(v) for v in results.values() if isinstance(v, list))
    return results
