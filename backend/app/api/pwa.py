"""PWA manifest and configuration API."""

from fastapi import APIRouter

router = APIRouter()

PWA_MANIFEST = {
    "name": "Gnosis AI",
    "short_name": "Gnosis",
    "description": "Gnosis AI Agent Platform",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0f172a",
    "theme_color": "#6366f1",
    "icons": [
        {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
    ],
    "categories": ["productivity", "utilities"],
    "orientation": "any",
}


# PUBLIC: PWA manifest must be fetchable without auth for install prompts
@router.get("/manifest")
async def pwa_manifest():
    return PWA_MANIFEST


# PUBLIC: frontend fetches PWA config before login to bootstrap service worker
@router.get("/config")
async def pwa_config():
    return {
        "service_worker": "/sw.js",
        "manifest_url": "/api/v1/pwa/manifest",
        "offline_enabled": True,
        "push_notifications": False,
        "cache_strategy": "network-first",
        "app_name": "Gnosis AI",
        "theme_color": "#6366f1",
        "display": "standalone",
    }
