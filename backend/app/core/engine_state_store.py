"""Shared persistence helpers for stateful in-memory engines."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, is_dataclass
from typing import Any

from sqlalchemy import delete, select

from app.core.database import async_session_factory, db_available
from app.models.engine_state import EngineState

logger = logging.getLogger("gnosis.engine_state_store")


def _to_payload(value: Any) -> Any:
    if is_dataclass(value):
        return json.loads(json.dumps(asdict(value), default=str))
    if hasattr(value, "model_dump"):
        return json.loads(json.dumps(value.model_dump(), default=str))
    if isinstance(value, dict):
        return json.loads(json.dumps(value, default=str))
    if hasattr(value, "__dict__"):
        return json.loads(json.dumps(value.__dict__, default=str))
    return value


async def load_states(
    engine_name: str, group_id: str | None = None
) -> list[EngineState]:
    if not db_available:
        return []
    async with async_session_factory() as session:
        stmt = select(EngineState).where(EngineState.engine_name == engine_name)
        if group_id is not None:
            stmt = stmt.where(EngineState.group_id == group_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def upsert_state(
    engine_name: str,
    entity_id: str,
    payload: Any,
    *,
    group_id: str | None = None,
    state_type: str | None = None,
    version_number: int | None = None,
    is_active: bool | None = None,
) -> None:
    if not db_available:
        return
    async with async_session_factory() as session:
        stmt = select(EngineState).where(
            EngineState.engine_name == engine_name,
            EngineState.entity_id == entity_id,
        )
        result = await session.execute(stmt)
        row = result.scalars().first()
        if row is None:
            row = EngineState(
                engine_name=engine_name,
                entity_id=entity_id,
                group_id=group_id,
                state_type=state_type,
                version_number=version_number,
                is_active=bool(is_active) if is_active is not None else False,
                state_json=_to_payload(payload),
            )
            session.add(row)
        else:
            row.group_id = group_id
            row.state_type = state_type
            row.version_number = version_number
            if is_active is not None:
                row.is_active = is_active
            row.state_json = _to_payload(payload)
        await session.flush()


async def delete_state(engine_name: str, entity_id: str) -> None:
    if not db_available:
        return
    async with async_session_factory() as session:
        await session.execute(
            delete(EngineState).where(
                EngineState.engine_name == engine_name,
                EngineState.entity_id == entity_id,
            )
        )
        await session.flush()
