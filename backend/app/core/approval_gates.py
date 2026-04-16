"""Pipeline Approval Gates — require human approval before pipeline steps proceed."""
from dataclasses import dataclass, field, asdict
from typing import Dict, List
from datetime import datetime, timezone
import uuid


@dataclass
class ApprovalGate:
    id: str
    pipeline_id: str
    step_index: int
    status: str  # pending / approved / rejected
    required_approvers: List[str] = field(default_factory=list)
    approvals: List[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ApprovalGateEngine:
    def __init__(self):
        self._gates: Dict[str, ApprovalGate] = {}

    def create_gate(self, pipeline_id: str, step_index: int, required_approvers: List[str]) -> ApprovalGate:
        gate = ApprovalGate(
            id=str(uuid.uuid4()),
            pipeline_id=pipeline_id,
            step_index=step_index,
            status="pending",
            required_approvers=required_approvers,
        )
        self._gates[gate.id] = gate
        return gate

    def approve(self, gate_id: str, user_id: str) -> ApprovalGate:
        gate = self._gates.get(gate_id)
        if not gate:
            raise KeyError(f"Gate {gate_id} not found")
        gate.approvals.append({"user_id": user_id, "action": "approved", "at": datetime.now(timezone.utc).isoformat()})
        approver_ids = {a["user_id"] for a in gate.approvals if a["action"] == "approved"}
        if all(r in approver_ids for r in gate.required_approvers):
            gate.status = "approved"
        return gate

    def reject(self, gate_id: str, user_id: str, reason: str = "") -> ApprovalGate:
        gate = self._gates.get(gate_id)
        if not gate:
            raise KeyError(f"Gate {gate_id} not found")
        gate.approvals.append({"user_id": user_id, "action": "rejected", "reason": reason, "at": datetime.now(timezone.utc).isoformat()})
        gate.status = "rejected"
        return gate

    def check_gate(self, gate_id: str) -> bool:
        gate = self._gates.get(gate_id)
        if not gate:
            raise KeyError(f"Gate {gate_id} not found")
        return gate.status == "approved"

    def list_pipeline_gates(self, pipeline_id: str) -> List[dict]:
        return [asdict(g) for g in self._gates.values() if g.pipeline_id == pipeline_id]


approval_engine = ApprovalGateEngine()
