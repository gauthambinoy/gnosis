from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from app.core.auth import get_current_user_id
from app.core.marketplace import marketplace_engine
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/marketplace", tags=["marketplace"])


class PublishRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1000)
    category: str
    config: dict
    tags: List[str] = Field(default_factory=list)


class ReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=500)


# PUBLIC: marketplace category listing is browseable without auth
@router.get("/categories")
async def list_categories():
    return {"categories": marketplace_engine.get_categories()}


# PUBLIC: marketplace browse is intentionally anonymous
@router.get("/browse")
async def browse_marketplace(
    category: Optional[str] = None,
    search: Optional[str] = None,
    featured: bool = False,
    sort_by: str = "popular",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    agents, total = marketplace_engine.browse(
        category=category,
        search=search,
        featured_only=featured,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    return {
        "agents": [asdict(a) for a in agents],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# PUBLIC: aggregate non-sensitive marketplace counts
@router.get("/stats")
async def marketplace_stats():
    return marketplace_engine.stats


@router.post("/publish")
async def publish_agent(req: PublishRequest, user_id: str = Depends(get_current_user_id)):
    agent = marketplace_engine.publish(
        name=req.name,
        description=req.description,
        category=req.category,
        config=req.config,
        tags=req.tags,
    )
    return asdict(agent)


# PUBLIC: public listing view
@router.get("/{agent_id}")
async def get_marketplace_agent(agent_id: str):
    agent = marketplace_engine.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found in marketplace")
    return asdict(agent)


@router.post("/{agent_id}/clone")
async def clone_agent(agent_id: str, user_id: str = Depends(get_current_user_id)):
    config = marketplace_engine.clone_config(agent_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"config": config, "message": "Use this config to create a new agent"}


@router.post("/{agent_id}/reviews")
async def add_review(
    agent_id: str,
    req: ReviewRequest,
    user_id: str = Depends(get_current_user_id),
):
    review = marketplace_engine.add_review(
        agent_id, user_id=user_id, rating=req.rating, comment=req.comment
    )
    if not review:
        raise HTTPException(status_code=404, detail="Agent not found")
    return asdict(review)


# PUBLIC: reviews are displayed on public listing page
@router.get("/{agent_id}/reviews")
async def get_reviews(agent_id: str):
    reviews = marketplace_engine.get_reviews(agent_id)
    return {"reviews": [asdict(r) for r in reviews], "total": len(reviews)}
