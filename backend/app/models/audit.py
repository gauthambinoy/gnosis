"""Durable fallback storage for per-request audit records.

This is a separate concern from :mod:`app.core.audit_log` (the hash-chained
immutable domain audit log). This table backs
:class:`app.middleware.audit_log.AuditStore` when Redis is unavailable.
"""

import uuid

from sqlalchemy import Column, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class RequestAuditLog(Base):
    __tablename__ = "request_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    method = Column(String(10), nullable=False)
    path = Column(String(512), nullable=False, index=True)
    status_code = Column(Integer, nullable=False, index=True)
    latency_ms = Column(Float, nullable=False, default=0.0)
    user_id = Column(String(128), nullable=True, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(256), nullable=True)
    request_size = Column(Integer, nullable=False, default=0)
    response_size = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
