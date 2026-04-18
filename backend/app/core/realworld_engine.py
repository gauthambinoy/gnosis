"""
Real-World Connectors Engine
Agents that react to real-world events: weather, stocks, news, time, location.
"""

from __future__ import annotations

import logging
import uuid
import asyncio
import time
import re
import operator
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source definitions
# ---------------------------------------------------------------------------

REALWORLD_SOURCES: dict[str, dict[str, Any]] = {
    "weather": {
        "description": "Current weather for any city",
        "free_api": "https://wttr.in/{city}?format=j1",
        "refresh_rate": 1800,
        "params": ["city"],
    },
    "news": {
        "description": "Top headlines and news search",
        "free_api": "https://newsdata.io/api/1/news?apikey=demo&language=en",
        "refresh_rate": 900,
        "params": [],
    },
    "crypto": {
        "description": "Cryptocurrency prices",
        "free_api": "https://api.coingecko.com/api/v3/simple/price?ids={coins}&vs_currencies=usd",
        "refresh_rate": 60,
        "params": ["coins"],
    },
    "stocks": {
        "description": "Stock market data",
        "note": "Requires API key — Alpha Vantage or similar",
        "refresh_rate": 300,
        "params": ["symbol"],
    },
    "time": {
        "description": "World clock / timezone data",
        "free_api": "https://worldtimeapi.org/api/timezone/{zone}",
        "refresh_rate": 60,
        "params": ["zone"],
    },
    "ip_info": {
        "description": "IP geolocation",
        "free_api": "https://ipapi.co/{ip}/json/",
        "refresh_rate": 3600,
        "params": ["ip"],
    },
    "exchange_rates": {
        "description": "Currency exchange rates",
        "free_api": "https://open.er-api.com/v6/latest/{currency}",
        "refresh_rate": 3600,
        "params": ["currency"],
    },
    "random_data": {
        "description": "Random quotes, facts, jokes",
        "free_api": "https://api.quotable.io/random",
        "refresh_rate": 0,
        "params": [],
    },
}


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

CONDITION_OPS = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    "contains": lambda a, b: str(b).lower() in str(a).lower(),
    "changes": lambda _a, _b: True,  # handled specially
}


@dataclass
class RealWorldTrigger:
    """Watches a source and fires when a condition is met."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    source: str = ""
    params: dict[str, str] = field(default_factory=dict)
    field_path: str = ""  # dot-separated path into JSON response
    condition: str = ">"  # one of CONDITION_OPS keys
    threshold: Any = None
    action_description: str = ""
    active: bool = True
    last_value: Any = None
    last_checked: str = ""
    last_fired: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class TriggerEvent:
    """Record of a trigger that fired."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trigger_id: str = ""
    source: str = ""
    field_path: str = ""
    condition: str = ""
    value: Any = None
    threshold: Any = None
    fired_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class RealWorldEngine:
    """Fetches real-world data, evaluates triggers, keeps history."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, Any]] = {}  # key -> (ts, data)
        self._triggers: dict[str, RealWorldTrigger] = {}  # id -> trigger
        self._history: list[TriggerEvent] = []
        self._lock = asyncio.Lock()

    # -- sources -----------------------------------------------------------

    def list_sources(self) -> list[dict[str, Any]]:
        out = []
        for name, meta in REALWORLD_SOURCES.items():
            out.append(
                {
                    "name": name,
                    "description": meta["description"],
                    "refresh_rate": meta.get("refresh_rate", 0),
                    "params": meta.get("params", []),
                    "has_free_api": "free_api" in meta,
                }
            )
        return out

    # -- fetch -------------------------------------------------------------

    async def fetch_source(
        self, source: str, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        params = params or {}
        meta = REALWORLD_SOURCES.get(source)
        if not meta:
            return {"error": f"Unknown source: {source}"}

        # Build cache key
        cache_key = f"{source}:{sorted(params.items())}"
        refresh = meta.get("refresh_rate", 0)
        now = time.time()

        # Check cache
        if cache_key in self._cache:
            ts, data = self._cache[cache_key]
            if refresh > 0 and (now - ts) < refresh:
                return {
                    "source": source,
                    "cached": True,
                    "data": data,
                    "fetched_at": ts,
                }

        url_template = meta.get("free_api")
        if not url_template:
            return {
                "source": source,
                "cached": False,
                "data": {
                    "message": f"No free API configured for '{source}'. An API key is required."
                },
                "fetched_at": now,
            }

        url = url_template
        for k, v in params.items():
            url = url.replace(f"{{{k}}}", v)

        # Check for un-replaced placeholders
        if re.search(r"\{[a-z_]+\}", url):
            missing = re.findall(r"\{([a-z_]+)\}", url)
            return {"error": f"Missing required params: {missing}"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers={"User-Agent": "Gnosis/1.0"})
                try:
                    data = resp.json()
                except Exception:
                    data = {"text": resp.text[:2000]}
        except Exception as exc:
            data = {"error": str(exc)}

        self._cache[cache_key] = (now, data)
        return {"source": source, "cached": False, "data": data, "fetched_at": now}

    # -- triggers ----------------------------------------------------------

    async def create_trigger(
        self,
        user_id: str,
        source: str,
        field_path: str,
        condition: str,
        threshold: Any,
        action_description: str = "",
        params: dict[str, str] | None = None,
    ) -> RealWorldTrigger:
        if condition not in CONDITION_OPS:
            raise ValueError(
                f"Unknown condition '{condition}'. Choose from: {list(CONDITION_OPS)}"
            )
        trigger = RealWorldTrigger(
            user_id=user_id,
            source=source,
            params=params or {},
            field_path=field_path,
            condition=condition,
            threshold=threshold,
            action_description=action_description,
        )
        async with self._lock:
            self._triggers[trigger.id] = trigger
        return trigger

    async def delete_trigger(self, trigger_id: str) -> bool:
        async with self._lock:
            return self._triggers.pop(trigger_id, None) is not None

    def list_triggers(self, user_id: str | None = None) -> list[dict[str, Any]]:
        out = []
        for t in self._triggers.values():
            if user_id and t.user_id != user_id:
                continue
            out.append(self._trigger_to_dict(t))
        return out

    async def check_triggers(self) -> list[dict[str, Any]]:
        """Evaluate all active triggers; return list of those that fired."""
        fired: list[dict[str, Any]] = []
        for trigger in list(self._triggers.values()):
            if not trigger.active:
                continue
            result = await self.fetch_source(trigger.source, trigger.params)
            data = result.get("data", {})
            value = self._resolve_field(data, trigger.field_path)
            now_iso = datetime.now(timezone.utc).isoformat()
            trigger.last_checked = now_iso

            if value is None:
                continue

            did_fire = False
            if trigger.condition == "changes":
                did_fire = (
                    trigger.last_value is not None and value != trigger.last_value
                )
            else:
                try:
                    cmp_fn = CONDITION_OPS[trigger.condition]
                    # Try numeric comparison
                    try:
                        did_fire = cmp_fn(float(value), float(trigger.threshold))
                    except (ValueError, TypeError):
                        did_fire = cmp_fn(value, trigger.threshold)
                except Exception:
                    logger.warning("Real-world event processing failed", exc_info=True)

            trigger.last_value = value

            if did_fire:
                trigger.last_fired = now_iso
                event = TriggerEvent(
                    trigger_id=trigger.id,
                    source=trigger.source,
                    field_path=trigger.field_path,
                    condition=trigger.condition,
                    value=value,
                    threshold=trigger.threshold,
                )
                self._history.append(event)
                fired.append(
                    {
                        "trigger_id": trigger.id,
                        "event_id": event.id,
                        "source": trigger.source,
                        "field_path": trigger.field_path,
                        "condition": trigger.condition,
                        "value": value,
                        "threshold": trigger.threshold,
                        "action": trigger.action_description,
                        "fired_at": event.fired_at,
                    }
                )
        return fired

    # -- history / stats ---------------------------------------------------

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [
            {
                "id": e.id,
                "trigger_id": e.trigger_id,
                "source": e.source,
                "field_path": e.field_path,
                "condition": e.condition,
                "value": e.value,
                "threshold": e.threshold,
                "fired_at": e.fired_at,
            }
            for e in reversed(self._history[-limit:])
        ]

    def get_stats(self) -> dict[str, Any]:
        active = sum(1 for t in self._triggers.values() if t.active)
        return {
            "sources_available": len(REALWORLD_SOURCES),
            "triggers_total": len(self._triggers),
            "triggers_active": active,
            "events_fired": len(self._history),
            "cache_entries": len(self._cache),
        }

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _resolve_field(data: Any, path: str) -> Any:
        """Resolve a dot-separated field path in nested dicts/lists."""
        if not path:
            return data
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, (list, tuple)):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current

    @staticmethod
    def _trigger_to_dict(t: RealWorldTrigger) -> dict[str, Any]:
        return {
            "id": t.id,
            "user_id": t.user_id,
            "source": t.source,
            "params": t.params,
            "field_path": t.field_path,
            "condition": t.condition,
            "threshold": t.threshold,
            "action_description": t.action_description,
            "active": t.active,
            "last_value": t.last_value,
            "last_checked": t.last_checked,
            "last_fired": t.last_fired,
            "created_at": t.created_at,
        }


# Module-level singleton
realworld_engine = RealWorldEngine()
