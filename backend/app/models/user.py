import uuid
from sqlalchemy import Column, String, Boolean, Integer, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # LLM settings
    llm_provider = Column(String(50), default="openrouter")
    llm_config = Column(
        JSON, default=dict
    )  # {tier_l1: {provider, model, api_key}, ...}
    llm_preset = Column(
        String(20), default="balanced"
    )  # budget, balanced, max, local, speed

    # Usage tracking
    total_tokens_used = Column(Integer, default=0)
    total_cost_usd = Column(Integer, default=0)  # stored in cents

    agents = relationship("Agent", back_populates="owner", cascade="all, delete-orphan")
