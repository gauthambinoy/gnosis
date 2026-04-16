"""Data Flow Audit — track how data flows through the system."""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid


@dataclass
class DataFlowRecord:
    id: str
    source: str
    destination: str
    data_type: str
    purpose: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    user_id: str = ""


class DataFlowAuditEngine:
    def __init__(self):
        self._records: Dict[str, DataFlowRecord] = {}

    def record_flow(
        self, source: str, destination: str, data_type: str, purpose: str, user_id: str = ""
    ) -> DataFlowRecord:
        record = DataFlowRecord(
            id=str(uuid.uuid4()),
            source=source,
            destination=destination,
            data_type=data_type,
            purpose=purpose,
            user_id=user_id,
        )
        self._records[record.id] = record
        return record

    def get_flows(self, source: Optional[str] = None, destination: Optional[str] = None) -> List[dict]:
        flows = list(self._records.values())
        if source:
            flows = [f for f in flows if f.source == source]
        if destination:
            flows = [f for f in flows if f.destination == destination]
        return [asdict(f) for f in flows]

    def generate_flow_map(self) -> dict:
        nodes: set = set()
        edges: List[dict] = []
        for record in self._records.values():
            nodes.add(record.source)
            nodes.add(record.destination)
            edges.append({
                "source": record.source,
                "destination": record.destination,
                "data_type": record.data_type,
                "purpose": record.purpose,
            })
        return {"nodes": sorted(nodes), "edges": edges}


data_flow_engine = DataFlowAuditEngine()
