"""OAuth2 flow manager for all integrations — supports PKCE, token refresh, revocation."""

import hashlib
import logging
import secrets
import time
import base64
import os
from urllib.parse import urlencode

import aiohttp


logger = logging.getLogger(__name__)


def _build_provider_configs() -> dict[str, dict]:
    """Build provider config dict from current environment variables.

    Lazy / call-time evaluation lets tests inject credentials and lets
    deployments rotate secrets without restarting the import system.
    """
    return {
        "google": {
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "revoke_url": "https://oauth2.googleapis.com/revoke",
            "scopes": [
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/spreadsheets",
                "openid",
                "email",
                "profile",
            ],
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        },
        "slack": {
            "auth_url": "https://slack.com/oauth/v2/authorize",
            "token_url": "https://slack.com/api/oauth.v2.access",
            "revoke_url": "https://slack.com/api/auth.revoke",
            "scopes": [
                "chat:write",
                "channels:read",
                "channels:history",
                "reactions:write",
                "search:read",
            ],
            "client_id": os.getenv("SLACK_CLIENT_ID", ""),
            "client_secret": os.getenv("SLACK_CLIENT_SECRET", ""),
        },
    }


# Eager snapshot kept for backwards compatibility; new code should call
# ``_build_provider_configs()`` to pick up env changes.
PROVIDER_CONFIGS: dict[str, dict] = _build_provider_configs()


class OAuthConfigurationError(RuntimeError):
    """Raised when an OAuth provider is invoked without configured credentials."""


def validate_oauth_credentials(
    required_providers: list[str] | None = None, *, strict: bool = False
) -> dict[str, list[str]]:
    """Validate OAuth provider credentials are present.

    Returns ``{"missing": [...], "configured": [...]}``. When ``strict=True``
    and any of ``required_providers`` is missing credentials, raises
    :class:`OAuthConfigurationError`. Intended to be invoked from app
    startup so deploys fail fast instead of returning runtime 500s on the
    first OAuth callback.
    """
    cfgs = _build_provider_configs()
    providers = required_providers or list(cfgs.keys())
    missing: list[str] = []
    configured: list[str] = []
    for p in providers:
        cfg = cfgs.get(p)
        if not cfg or not cfg.get("client_id") or not cfg.get("client_secret"):
            missing.append(p)
            logger.warning(
                "oauth.credentials_missing provider=%s — integration disabled", p
            )
        else:
            configured.append(p)
    if strict and missing:
        raise OAuthConfigurationError(
            "Missing OAuth credentials for: "
            + ", ".join(missing)
            + ". Set <PROVIDER>_CLIENT_ID and <PROVIDER>_CLIENT_SECRET env vars."
        )
    return {"missing": missing, "configured": configured}


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


class OAuthManager:
    """Manages OAuth2 flows for all integrations."""

    def __init__(self):
        self.tokens: dict[str, dict] = {}  # key = "user_id:provider"
        self._pkce_verifiers: dict[str, str] = {}  # key = "user_id:provider"
        self._states: dict[str, str] = {}  # state → "user_id:provider"

    @staticmethod
    def _key(provider: str, user_id: str) -> str:
        return f"{user_id}:{provider}"

    @staticmethod
    def _get_config(provider: str) -> dict:
        cfg = PROVIDER_CONFIGS.get(provider)
        if cfg is None:
            raise ValueError(f"Unknown OAuth provider: {provider}")
        return cfg

    # ------------------------------------------------------------------
    # Authorization URL
    # ------------------------------------------------------------------
    def get_auth_url(self, provider: str, user_id: str, redirect_uri: str) -> str:
        """Generate OAuth authorization URL with PKCE."""
        cfg = self._get_config(provider)
        key = self._key(provider, user_id)

        verifier, challenge = _generate_pkce()
        self._pkce_verifiers[key] = verifier

        state = secrets.token_urlsafe(32)
        self._states[state] = key

        params: dict[str, str] = {
            "client_id": cfg["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }

        if provider == "slack":
            params["scope"] = ",".join(cfg["scopes"])
        else:
            params["scope"] = " ".join(cfg["scopes"])

        return f"{cfg['auth_url']}?{urlencode(params)}"

    # ------------------------------------------------------------------
    # Code exchange
    # ------------------------------------------------------------------
    async def exchange_code(
        self, provider: str, user_id: str, code: str, redirect_uri: str
    ) -> dict:
        """Exchange auth code for access + refresh tokens."""
        cfg = self._get_config(provider)
        key = self._key(provider, user_id)
        verifier = self._pkce_verifiers.pop(key, "")

        payload = {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        if verifier:
            payload["code_verifier"] = verifier

        async with aiohttp.ClientSession() as session:
            async with session.post(cfg["token_url"], data=payload) as resp:
                data = await resp.json()

        if "error" in data:
            raise RuntimeError(
                f"Token exchange failed: {data.get('error_description', data['error'])}"
            )

        token_data = {
            "access_token": data.get("access_token")
            or data.get("authed_user", {}).get("access_token", ""),
            "refresh_token": data.get("refresh_token", ""),
            "expires_at": time.time() + int(data.get("expires_in", 3600)),
            "token_type": data.get("token_type", "Bearer"),
            "scope": data.get("scope", ""),
        }
        self.tokens[key] = token_data
        return token_data

    # ------------------------------------------------------------------
    # Get valid token (auto-refresh)
    # ------------------------------------------------------------------
    async def get_valid_token(self, provider: str, user_id: str) -> str:
        """Get valid access token, auto-refresh if expired."""
        key = self._key(provider, user_id)
        token_data = self.tokens.get(key)
        if token_data is None:
            raise RuntimeError(
                f"No token stored for {key}. User must authenticate first."
            )

        if time.time() >= token_data.get("expires_at", 0) - 60:
            token_data = await self.refresh_token(provider, user_id)

        return token_data["access_token"]

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------
    async def refresh_token(self, provider: str, user_id: str) -> dict:
        """Refresh expired access token."""
        cfg = self._get_config(provider)
        key = self._key(provider, user_id)
        token_data = self.tokens.get(key)
        if not token_data or not token_data.get("refresh_token"):
            raise RuntimeError(f"No refresh token available for {key}")

        payload = {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "refresh_token": token_data["refresh_token"],
            "grant_type": "refresh_token",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(cfg["token_url"], data=payload) as resp:
                data = await resp.json()

        if "error" in data:
            raise RuntimeError(
                f"Token refresh failed: {data.get('error_description', data['error'])}"
            )

        token_data["access_token"] = data["access_token"]
        token_data["expires_at"] = time.time() + int(data.get("expires_in", 3600))
        if "refresh_token" in data:
            token_data["refresh_token"] = data["refresh_token"]

        self.tokens[key] = token_data
        return token_data

    # ------------------------------------------------------------------
    # Revoke
    # ------------------------------------------------------------------
    async def revoke(self, provider: str, user_id: str) -> None:
        """Revoke OAuth tokens."""
        cfg = self._get_config(provider)
        key = self._key(provider, user_id)
        token_data = self.tokens.pop(key, None)
        if not token_data:
            return

        token = token_data.get("access_token", "")
        async with aiohttp.ClientSession() as session:
            if provider == "slack":
                await session.get(
                    cfg["revoke_url"],
                    headers={"Authorization": f"Bearer {token}"},
                )
            else:
                await session.post(cfg["revoke_url"], data={"token": token})

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    def resolve_state(self, state: str) -> tuple[str, str] | None:
        """Resolve OAuth state parameter → (provider, user_id) or None."""
        key = self._states.pop(state, None)
        if key is None:
            return None
        user_id, provider = key.split(":", 1)
        return provider, user_id

    def is_connected(self, provider: str, user_id: str) -> bool:
        return self._key(provider, user_id) in self.tokens


# Singleton instance
oauth_manager = OAuthManager()
