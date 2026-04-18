"""Consent Management — track user consent for data processing."""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid


@dataclass
class ConsentRecord:
    id: str
    user_id: str
    purpose: str
    granted: bool
    ip_address: str = ""
    granted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    revoked_at: Optional[str] = None


class ConsentManager:
    def __init__(self):
        self._records: Dict[str, ConsentRecord] = {}

    def grant_consent(
        self, user_id: str, purpose: str, ip_address: str = ""
    ) -> ConsentRecord:
        record = ConsentRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            purpose=purpose,
            granted=True,
            ip_address=ip_address,
        )
        self._records[record.id] = record
        return record

    def revoke_consent(self, user_id: str, purpose: str) -> Optional[ConsentRecord]:
        for record in self._records.values():
            if (
                record.user_id == user_id
                and record.purpose == purpose
                and record.granted
            ):
                record.granted = False
                record.revoked_at = datetime.now(timezone.utc).isoformat()
                return record
        return None

    def check_consent(self, user_id: str, purpose: str) -> bool:
        for record in self._records.values():
            if (
                record.user_id == user_id
                and record.purpose == purpose
                and record.granted
            ):
                return True
        return False

    def list_consents(self, user_id: str) -> List[dict]:
        return [asdict(r) for r in self._records.values() if r.user_id == user_id]


consent_manager = ConsentManager()
