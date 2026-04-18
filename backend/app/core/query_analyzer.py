"""Gnosis Query Analyzer — Auto-analyze slow queries with EXPLAIN plans."""

import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.query_analyzer")


@dataclass
class QueryRecord:
    query: str
    duration_ms: float
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    explain_plan: Optional[str] = None
    rows_affected: int = 0
    source: str = ""  # Which module initiated the query


@dataclass
class QueryStats:
    query_pattern: str
    call_count: int = 0
    total_ms: float = 0
    avg_ms: float = 0
    max_ms: float = 0
    min_ms: float = float("inf")
    last_called: str = ""


class QueryAnalyzer:
    """Tracks and analyzes database query performance."""

    SLOW_THRESHOLD_MS = 100  # Queries slower than this are flagged

    def __init__(self):
        self._records: List[QueryRecord] = []
        self._patterns: Dict[str, QueryStats] = {}
        self._max_records = 10000

    def record(self, query: str, duration_ms: float, source: str = "", rows: int = 0):
        """Record a query execution."""
        record = QueryRecord(
            query=query, duration_ms=duration_ms, source=source, rows_affected=rows
        )
        self._records.append(record)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records :]

        # Normalize query for pattern matching
        pattern = self._normalize(query)
        if pattern not in self._patterns:
            self._patterns[pattern] = QueryStats(query_pattern=pattern)

        stats = self._patterns[pattern]
        stats.call_count += 1
        stats.total_ms += duration_ms
        stats.avg_ms = stats.total_ms / stats.call_count
        stats.max_ms = max(stats.max_ms, duration_ms)
        stats.min_ms = min(stats.min_ms, duration_ms)
        stats.last_called = record.timestamp

        if duration_ms > self.SLOW_THRESHOLD_MS:
            logger.warning(f"Slow query ({duration_ms:.1f}ms): {query[:200]}...")

    def _normalize(self, query: str) -> str:
        """Normalize a query to a pattern (replace literals with ?)."""
        normalized = re.sub(r"'[^']*'", "'?'", query)
        normalized = re.sub(r"\b\d+\b", "?", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized[:200]

    def get_slow_queries(
        self, threshold_ms: float = None, limit: int = 20
    ) -> List[dict]:
        threshold = threshold_ms or self.SLOW_THRESHOLD_MS
        slow = [r for r in self._records if r.duration_ms >= threshold]
        slow.sort(key=lambda r: r.duration_ms, reverse=True)
        return [asdict(r) for r in slow[:limit]]

    def get_top_patterns(self, by: str = "total_ms", limit: int = 20) -> List[dict]:
        patterns = list(self._patterns.values())
        if by == "count":
            patterns.sort(key=lambda p: p.call_count, reverse=True)
        elif by == "avg_ms":
            patterns.sort(key=lambda p: p.avg_ms, reverse=True)
        else:
            patterns.sort(key=lambda p: p.total_ms, reverse=True)
        return [asdict(p) for p in patterns[:limit]]

    def get_summary(self) -> dict:
        total = len(self._records)
        if not total:
            return {"total_queries": 0}
        avg = sum(r.duration_ms for r in self._records) / total
        slow_count = sum(
            1 for r in self._records if r.duration_ms > self.SLOW_THRESHOLD_MS
        )
        return {
            "total_queries": total,
            "unique_patterns": len(self._patterns),
            "avg_duration_ms": round(avg, 2),
            "slow_queries": slow_count,
            "slow_percentage": round(slow_count / total * 100, 1),
            "threshold_ms": self.SLOW_THRESHOLD_MS,
        }

    def reset(self):
        self._records.clear()
        self._patterns.clear()


query_analyzer = QueryAnalyzer()
