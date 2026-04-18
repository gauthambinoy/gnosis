import uuid

from sqlalchemy import Boolean, Column, Integer, JSON, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin


class EngineState(Base, TimestampMixin):
    __tablename__ = "engine_states"
    __table_args__ = (
        UniqueConstraint(
            "engine_name", "entity_id", name="uq_engine_states_engine_entity"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_name = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(128), nullable=False, index=True)
    group_id = Column(String(128), nullable=True, index=True)
    state_type = Column(String(64), nullable=True, index=True)
    version_number = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("false"))
    state_json = Column(JSON, nullable=False, default=dict)
