import uuid
from sqlalchemy import Column, String, Integer, Float, JSON, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base, TimestampMixin

class MemoryTier(str, enum.Enum):
    correction = "correction"
    episodic = "episodic"
    semantic = "semantic"
    procedural = "procedural"

class Memory(Base, TimestampMixin):
    __tablename__ = "memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)

    tier = Column(SAEnum(MemoryTier), nullable=False, index=True)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True, index=True)  # dedup

    # Vector embedding reference (FAISS index id)
    faiss_index_id = Column(Integer, nullable=True)
    embedding_model = Column(String(50), default="all-MiniLM-L6-v2")

    # Relevance & decay
    importance_score = Column(Float, default=1.0)
    relevance_score = Column(Float, default=1.0)
    decay_factor = Column(Float, default=0.97)  # multiplied daily for episodic
    access_count = Column(Integer, default=0)
    strength = Column(Float, default=1.0)  # for procedural — increases with use

    # Context
    source_execution_id = Column(UUID(as_uuid=True), nullable=True)
    extra_metadata = Column("metadata", JSON, default=dict)
    tags = Column(JSON, default=list)

    agent = relationship("Agent", back_populates="memories")
