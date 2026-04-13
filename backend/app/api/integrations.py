from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_integrations():
    """List available integrations and their connection status."""
    return {
        "integrations": [
            {"id": "gmail", "name": "Gmail", "status": "not_connected", "icon": "📧"},
            {"id": "sheets", "name": "Google Sheets", "status": "not_connected", "icon": "📊"},
            {"id": "slack", "name": "Slack", "status": "not_connected", "icon": "💬"},
            {"id": "http", "name": "Universal HTTP", "status": "available", "icon": "🌐"},
        ]
    }


@router.post("/{integration_id}/connect")
async def connect_integration(integration_id: str):
    """Initiate OAuth flow for an integration."""
    return {"redirect_url": f"/oauth/{integration_id}/authorize", "integration_id": integration_id}
