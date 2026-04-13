import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, JSON, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base, TimestampMixin

class AgentStatus(str, enum.Enum):
    active = "active"
    idle = "idle"
    paused = "paused"
    error = "error"
    learning = "learning"

class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    personality = Column(String(50), default="professional")
    avatar_emoji = Column(String(10), default="◎")

    # Configuration
    trigger_type = Column(String(50), default="manual")  # manual, schedule, webhook, email
    trigger_config = Column(JSON, default=dict)
    steps = Column(JSON, default=list)
    integrations = Column(JSON, default=list)
    guardrails = Column(JSON, default=list)

    # Status & Trust
    status = Column(SAEnum(AgentStatus), default=AgentStatus.idle, nullable=False)
    trust_level = Column(Integer, default=0)  # 0=Observer, 1=Apprentice, 2=Associate, 3=Autonomous

    # Performance metrics (real-time updated)
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    total_corrections = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    avg_latency_ms = Column(Float, default=0.0)
    total_tokens_used = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    time_saved_minutes = Column(Float, default=0.0)

    # Learning
    last_learned_at = Column(String, nullable=True)
    memory_count = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)

    owner = relationship("User", back_populates="agents")
    executions = relationship("Execution", back_populates="agent", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="agent", cascade="all, delete-orphan")
