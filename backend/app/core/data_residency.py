"""Data Residency Control — control where data is stored geographically."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid


AVAILABLE_REGIONS = [
    {"id": "us-east", "name": "US East (Virginia)", "provider": "aws"},
    {"id": "eu-west", "name": "EU West (Ireland)", "provider": "aws"},
    {"id": "ap-southeast", "name": "Asia Pacific (Singapore)", "provider": "aws"},
]

REGION_IDS = {r["id"] for r in AVAILABLE_REGIONS}


@dataclass
class ResidencyPolicy:
    id: str
    workspace_id: str
    region: str  # us-east / eu-west / ap-southeast
    enforced: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DataResidencyEngine:
    def __init__(self):
        self._policies: Dict[str, ResidencyPolicy] = {}  # workspace_id -> policy

    def set_policy(self, workspace_id: str, region: str, enforced: bool = True) -> ResidencyPolicy:
        if region not in REGION_IDS:
            raise ValueError(f"Invalid region: {region}. Must be one of {REGION_IDS}")
        policy = ResidencyPolicy(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            region=region,
            enforced=enforced,
        )
        self._policies[workspace_id] = policy
        return policy

    def get_policy(self, workspace_id: str) -> Optional[ResidencyPolicy]:
        return self._policies.get(workspace_id)

    def list_regions(self) -> List[dict]:
        return AVAILABLE_REGIONS

    def validate_residency(self, workspace_id: str, target_region: str) -> dict:
        policy = self._policies.get(workspace_id)
        if not policy:
            return {"valid": True, "reason": "No residency policy set"}
        if not policy.enforced:
            return {"valid": True, "reason": "Policy not enforced"}
        if target_region == policy.region:
            return {"valid": True, "reason": "Region matches policy"}
        return {"valid": False, "reason": f"Data must stay in {policy.region}, got {target_region}"}


residency_engine = DataResidencyEngine()
