import uuid
from sqlalchemy import Column, String, Integer, JSON, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin

class TrustEvent(Base, TimestampMixin):
    __tablename__ = "trust_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type = Column(String(50), nullable=False)  # promotion, demotion, correction, success, failure
    from_level = Column(Integer, nullable=False)
    to_level = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)

    metrics_snapshot = Column(JSON, default=dict)  # snapshot of agent metrics at time of event
