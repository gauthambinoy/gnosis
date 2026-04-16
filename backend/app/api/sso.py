from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.core.sso import sso_engine
from dataclasses import asdict
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/auth/sso", tags=["sso"])


class AuthorizeRequest(BaseModel):
    provider: str = Field(description="OAuth provider: google or github")
    redirect_uri: str = Field(default="http://localhost:3000/auth/callback")


class CallbackRequest(BaseModel):
    provider: str
    code: str
    state: str


class LinkAccountRequest(BaseModel):
    provider: str
    provider_user_id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    gnosis_user_id: Optional[str] = None


@router.get("/providers")
async def list_providers():
    return {"providers": sso_engine.get_providers()}


@router.post("/authorize")
async def get_authorize_url(req: AuthorizeRequest):
    try:
        result = sso_engine.get_authorize_url(req.provider, req.redirect_uri)
        return result
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)


@router.post("/callback")
async def handle_callback(req: CallbackRequest):
    """Handle OAuth callback — in production this exchanges code for token."""
    oauth_state = sso_engine.validate_state(req.state)
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    # In production, exchange code for access token via HTTP
    # For now, return success with mock data
    return {
        "success": True,
        "provider": req.provider,
        "message": "OAuth callback processed. In production, this exchanges the code for an access token.",
        "code": req.code[:10] + "...",
    }


@router.post("/link")
async def link_sso_account(req: LinkAccountRequest):
    account = sso_engine.register_sso_account(
        provider=req.provider, provider_user_id=req.provider_user_id,
        email=req.email, name=req.name, avatar_url=req.avatar_url,
        gnosis_user_id=req.gnosis_user_id,
    )
    return asdict(account)


@router.get("/accounts/{user_id}")
async def get_linked_accounts(user_id: str):
    accounts = sso_engine.get_linked_accounts(user_id)
    return {"accounts": [asdict(a) for a in accounts], "total": len(accounts)}


@router.get("/stats")
async def sso_stats():
    return sso_engine.stats
