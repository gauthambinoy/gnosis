"""Lightweight tracing without heavy OpenTelemetry SDK dependency.
Uses a simple span context that can be exported to any backend."""

import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from app.core.logger import get_logger

logger = get_logger("tracing")

_current_trace: ContextVar[str] = ContextVar("current_trace", default="")
_current_span: ContextVar[str] = ContextVar("current_span", default="")


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_id: str | None
    operation: str
    start_time: float
    end_time: float | None = None
    status: str = "ok"
    attributes: dict = field(default_factory=dict)
    events: list = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0


class Tracer:
    """Lightweight distributed tracer."""

    def __init__(self):
        self.spans: list[Span] = []
        self.max_spans = 10000

    def start_trace(self, operation: str) -> Span:
        trace_id = uuid.uuid4().hex[:16]
        span_id = uuid.uuid4().hex[:8]
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_id=None,
            operation=operation,
            start_time=time.perf_counter(),
        )
        _current_trace.set(trace_id)
        _current_span.set(span_id)
        return span

    def start_span(self, operation: str, parent: Span = None) -> Span:
        trace_id = _current_trace.get() or uuid.uuid4().hex[:16]
        parent_id = parent.span_id if parent else _current_span.get() or None
        span_id = uuid.uuid4().hex[:8]
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_id=parent_id,
            operation=operation,
            start_time=time.perf_counter(),
        )
        _current_span.set(span_id)
        return span

    def end_span(self, span: Span, status: str = "ok", attributes: dict = None):
        span.end_time = time.perf_counter()
        span.status = status
        if attributes:
            span.attributes.update(attributes)
        self.spans.append(span)
        if len(self.spans) > self.max_spans:
            self.spans = self.spans[-self.max_spans :]

    def get_trace(self, trace_id: str) -> list[Span]:
        return [s for s in self.spans if s.trace_id == trace_id]

    def get_recent_traces(self, limit: int = 20) -> list[dict]:
        traces = {}
        for span in reversed(self.spans):
            if span.trace_id not in traces:
                traces[span.trace_id] = {
                    "trace_id": span.trace_id,
                    "root_operation": span.operation
                    if not span.parent_id
                    else traces.get(span.trace_id, {}).get(
                        "root_operation", span.operation
                    ),
                    "spans": [],
                    "total_duration_ms": 0,
                }
            traces[span.trace_id]["spans"].append(
                {
                    "span_id": span.span_id,
                    "parent_id": span.parent_id,
                    "operation": span.operation,
                    "duration_ms": round(span.duration_ms, 2),
                    "status": span.status,
                    "attributes": span.attributes,
                }
            )
            if not span.parent_id:
                traces[span.trace_id]["total_duration_ms"] = round(span.duration_ms, 2)
                traces[span.trace_id]["root_operation"] = span.operation
            if len(traces) >= limit:
                break
        return list(traces.values())[:limit]


tracer = Tracer()
