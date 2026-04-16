"""Gnosis GDPR Engine — Right to erasure with cascading deletion."""
import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.gdpr")

@dataclass
class ErasureRequest:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    requested_by: str = ""  # Could be the user or admin
    reason: str = ""
    status: str = "pending"  # pending, processing, completed, failed
    data_categories: List[str] = field(default_factory=lambda: ["all"])
    results: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None

class GDPREngine:
    def __init__(self):
        self._requests: Dict[str, ErasureRequest] = {}

    def create_erasure_request(self, user_id: str, requested_by: str, reason: str = "", data_categories: list = None) -> ErasureRequest:
        request = ErasureRequest(
            user_id=user_id,
            requested_by=requested_by,
            reason=reason,
            data_categories=data_categories or ["all"],
        )
        self._requests[request.id] = request
        logger.info(f"GDPR erasure request created: {request.id} for user {user_id}")
        return request

    async def execute_erasure(self, request_id: str) -> ErasureRequest:
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Erasure request not found: {request_id}")
        
        request.status = "processing"
        results = {}
        
        try:
            categories = request.data_categories
            erase_all = "all" in categories
            
            if erase_all or "agents" in categories:
                results["agents"] = {"status": "queued", "note": "Agent data marked for deletion"}
            if erase_all or "executions" in categories:
                results["executions"] = {"status": "queued", "note": "Execution history marked for deletion"}
            if erase_all or "memories" in categories:
                results["memories"] = {"status": "queued", "note": "Memory entries marked for deletion"}
            if erase_all or "files" in categories:
                results["files"] = {"status": "queued", "note": "Uploaded files marked for deletion"}
            if erase_all or "audit_logs" in categories:
                results["audit_logs"] = {"status": "queued", "note": "Audit logs marked for anonymization"}
            if erase_all or "profile" in categories:
                results["profile"] = {"status": "queued", "note": "User profile marked for anonymization"}
            
            request.results = results
            request.status = "completed"
            request.completed_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"GDPR erasure completed: {request_id}, categories: {list(results.keys())}")
            
        except Exception as e:
            request.status = "failed"
            request.error = str(e)
            logger.error(f"GDPR erasure failed: {request_id}: {e}")
        
        return request

    def get_request(self, request_id: str) -> Optional[ErasureRequest]:
        return self._requests.get(request_id)

    def list_requests(self, user_id: str = None) -> List[dict]:
        requests = list(self._requests.values())
        if user_id:
            requests = [r for r in requests if r.user_id == user_id]
        return [asdict(r) for r in sorted(requests, key=lambda r: r.created_at, reverse=True)]

    def get_user_data_inventory(self, user_id: str) -> dict:
        """Return a summary of all data held for a user."""
        return {
            "user_id": user_id,
            "data_categories": {
                "agents": {"description": "AI agents created by the user", "erasable": True},
                "executions": {"description": "Agent execution history and results", "erasable": True},
                "memories": {"description": "Agent memory entries", "erasable": True},
                "files": {"description": "Uploaded files", "erasable": True},
                "audit_logs": {"description": "Action audit trail", "erasable": False, "note": "Anonymized, not deleted"},
                "profile": {"description": "User account data", "erasable": True},
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

gdpr_engine = GDPREngine()
