"""Gnosis SSO — OAuth2 login with Google and GitHub."""

import uuid
import hashlib
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, Optional
from urllib.parse import urlencode

logger = logging.getLogger("gnosis.sso")


@dataclass
class OAuthState:
    state: str
    provider: str
    redirect_uri: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class SSOAccount:
    id: str
    provider: str  # google, github
    provider_user_id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    gnosis_user_id: Optional[str] = None  # Linked Gnosis account
    access_token: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


PROVIDERS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": ["openid", "email", "profile"],
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scopes": ["user:email", "read:user"],
    },
}


class SSOEngine:
    def __init__(self):
        self._states: Dict[str, OAuthState] = {}
        self._accounts: Dict[
            str, SSOAccount
        ] = {}  # provider:provider_user_id -> account
        self._user_sso: Dict[str, list] = {}  # gnosis_user_id -> SSO accounts

        # Config (would come from env in production)
        self._client_ids: Dict[str, str] = {}
        self._client_secrets: Dict[str, str] = {}

    def configure(self, provider: str, client_id: str, client_secret: str):
        self._client_ids[provider] = client_id
        self._client_secrets[provider] = client_secret

    def get_authorize_url(self, provider: str, redirect_uri: str) -> dict:
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")

        state = hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:32]
        self._states[state] = OAuthState(
            state=state, provider=provider, redirect_uri=redirect_uri
        )

        config = PROVIDERS[provider]
        params = {
            "client_id": self._client_ids.get(provider, f"gnosis-{provider}-client-id"),
            "redirect_uri": redirect_uri,
            "scope": " ".join(config["scopes"]),
            "state": state,
            "response_type": "code",
        }

        if provider == "google":
            params["access_type"] = "offline"
            params["prompt"] = "consent"

        url = f"{config['authorize_url']}?{urlencode(params)}"
        return {"authorize_url": url, "state": state, "provider": provider}

    def validate_state(self, state: str) -> Optional[OAuthState]:
        return self._states.pop(state, None)

    def register_sso_account(
        self,
        provider: str,
        provider_user_id: str,
        email: str,
        name: str,
        avatar_url: Optional[str] = None,
        gnosis_user_id: Optional[str] = None,
    ) -> SSOAccount:
        key = f"{provider}:{provider_user_id}"
        if key in self._accounts:
            account = self._accounts[key]
            account.email = email
            account.name = name
            account.avatar_url = avatar_url
            return account

        account = SSOAccount(
            id=str(uuid.uuid4()),
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
            gnosis_user_id=gnosis_user_id,
        )
        self._accounts[key] = account
        if gnosis_user_id:
            self._user_sso.setdefault(gnosis_user_id, []).append(account)

        logger.info(f"SSO account registered: {provider}/{email}")
        return account

    def get_linked_accounts(self, gnosis_user_id: str) -> list:
        return self._user_sso.get(gnosis_user_id, [])

    def get_providers(self) -> list:
        return [
            {
                "id": pid,
                "name": pid.title(),
                "configured": pid in self._client_ids,
                "authorize_url": config["authorize_url"],
                "scopes": config["scopes"],
            }
            for pid, config in PROVIDERS.items()
        ]

    @property
    def stats(self) -> dict:
        provider_counts: dict[str, int] = {}
        for key in self._accounts:
            provider = key.split(":")[0]
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        return {
            "total_sso_accounts": len(self._accounts),
            "by_provider": provider_counts,
        }


sso_engine = SSOEngine()
