"""Gnosis Time-Boxed Integration Tokens — Scoped, expiring API tokens."""
import uuid, hashlib, logging
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("gnosis.integration_tokens")


@dataclass
class IntegrationToken:
    id: str
    name: str
    token_hash: str
    scopes: List[str]
    expires_at: str
    max_uses: int
    current_uses: int = 0
    created_by: str = ""
    active: bool = True


class IntegrationTokenEngine:
    def __init__(self):
        self._tokens: Dict[str, IntegrationToken] = {}
        self._token_map: Dict[str, str] = {}  # raw_token -> token_id

    def generate_token(self, name: str, scopes: List[str], ttl_hours: int,
                       max_uses: int, created_by: str) -> Tuple[IntegrationToken, str]:
        raw_token = uuid.uuid4().hex
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()
        token = IntegrationToken(
            id=uuid.uuid4().hex[:12],
            name=name,
            token_hash=token_hash,
            scopes=scopes,
            expires_at=expires_at,
            max_uses=max_uses,
            created_by=created_by,
        )
        self._tokens[token.id] = token
        self._token_map[raw_token] = token.id
        logger.info(f"Token {token.id} generated for {created_by}, expires {expires_at}")
        return token, raw_token

    def validate_token(self, raw_token: str) -> dict:
        token_id = self._token_map.get(raw_token)
        if not token_id:
            return {"valid": False, "reason": "Token not found"}
        token = self._tokens.get(token_id)
        if not token:
            return {"valid": False, "reason": "Token not found"}
        if not token.active:
            return {"valid": False, "reason": "Token has been revoked"}
        now = datetime.now(timezone.utc).isoformat()
        if now > token.expires_at:
            return {"valid": False, "reason": "Token has expired"}
        if token.max_uses > 0 and token.current_uses >= token.max_uses:
            return {"valid": False, "reason": "Token has exceeded maximum uses"}
        token.current_uses += 1
        return {"valid": True, "scopes": token.scopes}

    def revoke_token(self, token_id: str) -> bool:
        token = self._tokens.get(token_id)
        if not token:
            raise KeyError("Token not found")
        token.active = False
        logger.info(f"Token {token_id} revoked")
        return True

    def list_tokens(self, user_id: str) -> List[IntegrationToken]:
        return [t for t in self._tokens.values() if t.created_by == user_id]


integration_token_engine = IntegrationTokenEngine()
