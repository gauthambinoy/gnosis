"""Gnosis Time-Boxed Integration Tokens — API routes."""

from dataclasses import asdict
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.core.integration_tokens import integration_token_engine
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/integration-tokens", tags=["integration-tokens"])


class GenerateTokenRequest(BaseModel):
    name: str
    scopes: List[str]
    ttl_hours: int = 24
    max_uses: int = 0


class ValidateTokenRequest(BaseModel):
    token: str


@router.post("/")
async def generate_token(
    body: GenerateTokenRequest, user_id: str = Depends(get_current_user_id)
):
    token, raw_token = integration_token_engine.generate_token(
        name=body.name,
        scopes=body.scopes,
        ttl_hours=body.ttl_hours,
        max_uses=body.max_uses,
        created_by=user_id,
    )
    result = asdict(token)
    result["raw_token"] = raw_token
    return result


@router.get("/")
async def list_tokens(user_id: str = Depends(get_current_user_id)):
    tokens = integration_token_engine.list_tokens(user_id)
    return [asdict(t) for t in tokens]


@router.delete("/{token_id}")
async def revoke_token(token_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        integration_token_engine.revoke_token(token_id)
        return {"status": "revoked"}
    except KeyError as e:
        safe_http_error(e, "Operation failed", 404)


@router.post("/{token_id}/validate")
async def validate_token(token_id: str, body: ValidateTokenRequest, user_id: str = Depends(get_current_user_id)):
    result = integration_token_engine.validate_token(body.token)
    return result
