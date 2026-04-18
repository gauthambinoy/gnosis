"""Gnosis Waterfall — Track timing of each step in execution pipeline."""

import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from collections import defaultdict
import time

logger = logging.getLogger("gnosis.waterfall")


@dataclass
class WaterfallSpan:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = ""
    name: str = ""
    start_ms: float = 0.0
    end_ms: float = 0.0
    parent_id: Optional[str] = None


class WaterfallEngine:
    def __init__(self):
        self._spans: Dict[str, Dict[str, WaterfallSpan]] = defaultdict(dict)
        self._active_spans: Dict[str, WaterfallSpan] = {}

    def start_span(
        self, execution_id: str, name: str, parent_id: Optional[str] = None
    ) -> WaterfallSpan:
        span = WaterfallSpan(
            execution_id=execution_id,
            name=name,
            start_ms=round(time.time() * 1000, 2),
            parent_id=parent_id,
        )
        self._spans[execution_id][span.id] = span
        self._active_spans[span.id] = span
        logger.info(f"Started span '{name}' ({span.id}) for execution {execution_id}")
        return span

    def end_span(self, span_id: str) -> Optional[WaterfallSpan]:
        span = self._active_spans.pop(span_id, None)
        if span is None:
            for exec_spans in self._spans.values():
                if span_id in exec_spans:
                    span = exec_spans[span_id]
                    break
        if span is None:
            return None
        span.end_ms = round(time.time() * 1000, 2)
        logger.info(
            f"Ended span '{span.name}' ({span_id}) duration={span.end_ms - span.start_ms:.1f}ms"
        )
        return span

    def get_waterfall(self, execution_id: str) -> List[dict]:
        spans = self._spans.get(execution_id, {})
        result = [asdict(s) for s in spans.values()]
        result.sort(key=lambda s: s["start_ms"])
        return result

    def get_span(self, span_id: str) -> Optional[WaterfallSpan]:
        for exec_spans in self._spans.values():
            if span_id in exec_spans:
                return exec_spans[span_id]
        return None


waterfall_engine = WaterfallEngine()
