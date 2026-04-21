import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    JSON,
    Text,
    ForeignKey,
    DateTime,
    Index,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base, TimestampMixin


class MemoryTier(str, enum.Enum):
    sensory = "sensory"
    correction = "correction"
    episodic = "episodic"
    semantic = "semantic"
    procedural = "procedural"


class Memory(Base, TimestampMixin):
    __tablename__ = "memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Optional user owner (nullable for back-compat with existing rows)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    tier = Column(SAEnum(MemoryTier), nullable=False, index=True)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True, index=True)  # dedup

    # Vector embedding — stored portably as JSON-encoded list of floats so the
    # same column works on SQLite (tests) and PostgreSQL (prod). A future
    # migration can introduce pgvector's Vector type and migrate values over.
    embedding = Column(Text, nullable=True)

    # Vector embedding reference (FAISS index id) — legacy, kept for compat
    faiss_index_id = Column(Integer, nullable=True)
    embedding_model = Column(String(50), default="all-MiniLM-L6-v2")

    # Relevance & decay
    importance_score = Column(Float, default=1.0)
    relevance_score = Column(Float, default=1.0)
    decay_factor = Column(Float, default=0.97)  # multiplied daily for episodic
    access_count = Column(Integer, default=0)
    strength = Column(Float, default=1.0)  # for procedural — increases with use

    # Lifecycle timestamps
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Context
    source_execution_id = Column(UUID(as_uuid=True), nullable=True)
    extra_metadata = Column("metadata", JSON, default=dict)
    tags = Column(JSON, default=list)

    agent = relationship("Agent", back_populates="memories")

    __table_args__ = (
        Index("ix_memories_user_tier", "user_id", "tier"),
        Index("ix_memories_created_at", "created_at"),
    )
