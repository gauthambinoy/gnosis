"""Gnosis Internal Agent Marketplace — API routes."""

from dataclasses import asdict
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.core.internal_marketplace import internal_marketplace_engine
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/internal-marketplace", tags=["internal-marketplace"])


class PublishRequest(BaseModel):
    agent_id: str
    title: str
    description: str
    category: str
    version: str
    tags: List[str] = []


class RateRequest(BaseModel):
    score: float


@router.get("/")
async def search_listings(
    query: Optional[str] = Query(None), category: Optional[str] = Query(None)
):
    results = internal_marketplace_engine.search(query=query, category=category)
    return [asdict(r) for r in results]


@router.post("/")
async def publish_listing(
    body: PublishRequest, user_id: str = Depends(get_current_user_id)
):
    listing = internal_marketplace_engine.publish(
        agent_id=body.agent_id,
        title=body.title,
        description=body.description,
        category=body.category,
        author=user_id,
        version=body.version,
        tags=body.tags,
    )
    return asdict(listing)


@router.get("/{listing_id}")
async def get_listing(listing_id: str):
    listing = internal_marketplace_engine.get_listing(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return asdict(listing)


@router.post("/{listing_id}/rate")
async def rate_listing(listing_id: str, body: RateRequest):
    try:
        listing = internal_marketplace_engine.rate(listing_id, body.score)
        return asdict(listing)
    except KeyError as e:
        safe_http_error(e, "Operation failed", 404)
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)


@router.post("/{listing_id}/download")
async def download_listing(listing_id: str):
    try:
        listing = internal_marketplace_engine.increment_downloads(listing_id)
        return asdict(listing)
    except KeyError as e:
        safe_http_error(e, "Operation failed", 404)
