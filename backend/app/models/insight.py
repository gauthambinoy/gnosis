import uuid
from sqlalchemy import Column, String, JSON, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin

class Insight(Base, TimestampMixin):
    __tablename__ = "insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)

    insight_type = Column(String(50), nullable=False)  # anomaly, trend, suggestion, optimization
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), default="info", index=True)  # info, warning, critical

    data = Column(JSON, default=dict)
    suggested_action = Column(Text, nullable=True)

    is_read = Column(String, default="false")
    is_dismissed = Column(String, default="false")
    is_acted_upon = Column(String, default="false")
