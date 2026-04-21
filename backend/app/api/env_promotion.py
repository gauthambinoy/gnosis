"""Gnosis Environment Promotion — API routes."""

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.core.env_promotion import env_promotion_engine
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/promotions", tags=["env-promotion"])


class PromoteRequest(BaseModel):
    agent_id: str
    from_env: str
    to_env: str
    config_snapshot: dict


@router.post("/")
async def create_promotion(
    body: PromoteRequest, user_id: str = Depends(get_current_user_id)
):
    try:
        record = env_promotion_engine.promote(
            agent_id=body.agent_id,
            from_env=body.from_env,
            to_env=body.to_env,
            config_snapshot=body.config_snapshot,
            promoted_by=user_id,
        )
        return asdict(record)
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)


@router.post("/{promotion_id}/approve")
async def approve_promotion(
    promotion_id: str, user_id: str = Depends(get_current_user_id)
):
    try:
        record = env_promotion_engine.approve_promotion(promotion_id)
        return asdict(record)
    except KeyError as e:
        safe_http_error(e, "Operation failed", 404)
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)


@router.post("/{promotion_id}/deploy")
async def deploy_promotion(promotion_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        record = env_promotion_engine.deploy_promotion(promotion_id)
        return asdict(record)
    except KeyError as e:
        safe_http_error(e, "Operation failed", 404)
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)


@router.post("/{promotion_id}/rollback")
async def rollback_promotion(promotion_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        record = env_promotion_engine.rollback(promotion_id)
        return asdict(record)
    except KeyError as e:
        safe_http_error(e, "Operation failed", 404)
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)


@router.get("/")
async def list_promotions(agent_id: Optional[str] = Query(None), user_id: str = Depends(get_current_user_id)):
    records = env_promotion_engine.list_promotions(agent_id=agent_id)
    return [asdict(r) for r in records]
