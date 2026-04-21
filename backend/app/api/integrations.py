from fastapi import APIRouter, HTTPException, Request, Query, Depends

from app.core.auth import get_current_user_id
from app.integrations.oauth import oauth_manager

router = APIRouter()

PROVIDERS = {
    "gmail": {"name": "Gmail", "icon": "📧", "oauth_provider": "google"},
    "sheets": {"name": "Google Sheets", "icon": "📊", "oauth_provider": "google"},
    "slack": {"name": "Slack", "icon": "💬", "oauth_provider": "slack"},
    "http": {"name": "Universal HTTP", "icon": "🌐", "oauth_provider": None},
}

# Placeholder user_id until full auth middleware is wired
_DEFAULT_USER = "default"


@router.get("/providers")
async def list_providers(user_id: str = Depends(get_current_user_id)):
    """List available integrations with connection status."""
    results = []
    for pid, meta in PROVIDERS.items():
        oauth_prov = meta["oauth_provider"]
        if oauth_prov:
            connected = oauth_manager.is_connected(oauth_prov, user_id)
            status = "connected" if connected else "not_connected"
        else:
            status = "available"
        results.append(
            {"id": pid, "name": meta["name"], "icon": meta["icon"], "status": status}
        )
    return {"integrations": results}


@router.get("/{provider}/auth")
async def start_oauth(
    provider: str, request: Request, user_id: str = Depends(get_current_user_id)
):
    """Start OAuth flow — returns the authorization URL."""
    meta = PROVIDERS.get(provider)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")
    oauth_prov = meta["oauth_provider"]
    if not oauth_prov:
        raise HTTPException(status_code=400, detail=f"{provider} does not use OAuth")

    redirect_uri = (
        str(request.base_url).rstrip("/") + f"/api/v1/integrations/{provider}/callback"
    )
    auth_url = oauth_manager.get_auth_url(oauth_prov, user_id, redirect_uri)
    return {"auth_url": auth_url, "provider": provider}


# PUBLIC: OAuth provider redirects the end user here with code/state; protected by state validation in oauth_manager
@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str = Query(...),
    state: str = Query(default=""),
):
    """Handle OAuth callback — exchange code for tokens."""
    meta = PROVIDERS.get(provider)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")
    oauth_prov = meta["oauth_provider"]
    if not oauth_prov:
        raise HTTPException(status_code=400, detail=f"{provider} does not use OAuth")

    redirect_uri = (
        str(request.base_url).rstrip("/") + f"/api/v1/integrations/{provider}/callback"
    )
    try:
        token_data = await oauth_manager.exchange_code(
            oauth_prov, _DEFAULT_USER, code, redirect_uri
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "status": "connected",
        "provider": provider,
        "scope": token_data.get("scope", ""),
    }


@router.delete("/{provider}")
async def disconnect_provider(
    provider: str, user_id: str = Depends(get_current_user_id)
):
    """Disconnect / revoke OAuth tokens for a provider."""
    meta = PROVIDERS.get(provider)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")
    oauth_prov = meta["oauth_provider"]
    if not oauth_prov:
        raise HTTPException(status_code=400, detail=f"{provider} does not use OAuth")

    await oauth_manager.revoke(oauth_prov, user_id)
    return {"status": "disconnected", "provider": provider}


@router.get("/{provider}/status")
async def provider_status(
    provider: str, user_id: str = Depends(get_current_user_id)
):
    """Check connection status for a provider."""
    meta = PROVIDERS.get(provider)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")
    oauth_prov = meta["oauth_provider"]
    if not oauth_prov:
        return {"provider": provider, "status": "available"}
    connected = oauth_manager.is_connected(oauth_prov, user_id)
    return {
        "provider": provider,
        "status": "connected" if connected else "not_connected",
    }
