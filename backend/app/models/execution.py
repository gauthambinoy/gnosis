import uuid
from sqlalchemy import Column, String, Integer, Float, JSON, Text, ForeignKey, Enum as SAEnum, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base, TimestampMixin

class ExecutionStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    awaiting_approval = "awaiting_approval"

class Execution(Base, TimestampMixin):
    __tablename__ = "executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)

    trigger_type = Column(String(50), nullable=False)
    trigger_data = Column(JSON, default=dict)

    status = Column(SAEnum(ExecutionStatus), default=ExecutionStatus.queued, nullable=False, index=True)

    # Cortex phases (stored as JSON steps)
    steps = Column(JSON, default=list)  # [{phase, content, confidence, latency_ms, cost_usd, timestamp}]

    # Results
    result_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Metrics — use Numeric for precise cost tracking
    total_latency_ms = Column(Float, default=0.0)
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Numeric(precision=12, scale=6), default=0)
    reasoning_tier = Column(String(10), nullable=True)  # L0, L1, L2, L3

    # Human feedback
    was_corrected = Column(Boolean, default=False, nullable=False)
    correction_text = Column(Text, nullable=True)
    user_rating = Column(Integer, nullable=True)  # 1-5

    # Config version tracking for reproducibility
    config_version_id = Column(UUID(as_uuid=True), nullable=True)

    agent = relationship("Agent", back_populates="executions")
