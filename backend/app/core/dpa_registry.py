"""Gnosis DPA Registry — Track Data Processing Agreements per LLM provider."""
import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.dpa")

@dataclass
class DataProcessingAgreement:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    provider: str = ""  # "openai", "anthropic", "google", etc.
    version: str = "1.0"
    status: str = "active"  # active, expired, pending_review
    data_types_shared: List[str] = field(default_factory=list)  # ["prompts", "responses", "embeddings"]
    data_retention_days: int = 0  # Provider's retention period
    region: str = ""  # Provider data processing region
    signed_at: Optional[str] = None
    expires_at: Optional[str] = None
    document_url: str = ""
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class DPARegistry:
    def __init__(self):
        self._agreements: Dict[str, DataProcessingAgreement] = {}

    def register(self, provider: str, **kwargs) -> DataProcessingAgreement:
        dpa = DataProcessingAgreement(provider=provider, **kwargs)
        self._agreements[dpa.id] = dpa
        logger.info(f"DPA registered: {dpa.id} for provider {provider}")
        return dpa

    def get(self, dpa_id: str) -> Optional[DataProcessingAgreement]:
        return self._agreements.get(dpa_id)

    def get_by_provider(self, provider: str) -> List[DataProcessingAgreement]:
        return [d for d in self._agreements.values() if d.provider == provider]

    def list_all(self) -> List[dict]:
        return [asdict(d) for d in sorted(self._agreements.values(), key=lambda d: d.provider)]

    def check_compliance(self, provider: str) -> dict:
        dpas = self.get_by_provider(provider)
        active = [d for d in dpas if d.status == "active"]
        return {
            "provider": provider,
            "has_active_dpa": len(active) > 0,
            "active_count": len(active),
            "total_count": len(dpas),
            "compliant": len(active) > 0,
        }

    def provider_summary(self) -> List[dict]:
        providers = set(d.provider for d in self._agreements.values())
        return [self.check_compliance(p) for p in sorted(providers)]

dpa_registry = DPARegistry()
