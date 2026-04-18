"""Gnosis Self-Healer — Match errors to known fixes and auto-suggest remediation."""

import uuid
import re
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

logger = logging.getLogger("gnosis.self_healer")


@dataclass
class ErrorPattern:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern: str = ""  # regex
    fix_description: str = ""
    auto_fixable: bool = False
    category: str = "general"


BUILTIN_PATTERNS = [
    ErrorPattern(
        id="err-timeout",
        pattern=r"timeout|timed?\s*out|deadline exceeded",
        fix_description="Increase timeout threshold or add retry with exponential backoff",
        auto_fixable=True,
        category="timeout",
    ),
    ErrorPattern(
        id="err-oom",
        pattern=r"out of memory|OOM|memory limit|MemoryError",
        fix_description="Reduce batch size, enable streaming, or increase memory allocation",
        auto_fixable=False,
        category="resource",
    ),
    ErrorPattern(
        id="err-rate-limit",
        pattern=r"rate limit|429|too many requests|throttl",
        fix_description="Implement rate limiting with backoff, use request queuing",
        auto_fixable=True,
        category="rate-limit",
    ),
    ErrorPattern(
        id="err-auth",
        pattern=r"401|unauthorized|authentication failed|invalid token",
        fix_description="Refresh authentication token or re-authenticate",
        auto_fixable=True,
        category="auth",
    ),
    ErrorPattern(
        id="err-not-found",
        pattern=r"404|not found|does not exist|no such",
        fix_description="Verify resource ID/path, check if resource was deleted",
        auto_fixable=False,
        category="not-found",
    ),
    ErrorPattern(
        id="err-connection",
        pattern=r"connection refused|ECONNREFUSED|connection reset|network error",
        fix_description="Check service availability, retry with backoff, verify network config",
        auto_fixable=True,
        category="network",
    ),
    ErrorPattern(
        id="err-json",
        pattern=r"JSON|json decode|json parse|invalid json|JSONDecodeError",
        fix_description="Validate JSON input format, check for truncated responses",
        auto_fixable=False,
        category="parsing",
    ),
]


class SelfHealerEngine:
    def __init__(self):
        self._patterns: Dict[str, ErrorPattern] = {p.id: p for p in BUILTIN_PATTERNS}

    def register_pattern(
        self,
        pattern: str,
        fix_description: str,
        auto_fixable: bool = False,
        category: str = "general",
    ) -> ErrorPattern:
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
        ep = ErrorPattern(
            pattern=pattern,
            fix_description=fix_description,
            auto_fixable=auto_fixable,
            category=category,
        )
        self._patterns[ep.id] = ep
        logger.info(f"Registered error pattern: {ep.id} ({category})")
        return ep

    def match_error(self, error_msg: str) -> List[dict]:
        matches = []
        for ep in self._patterns.values():
            try:
                if re.search(ep.pattern, error_msg, re.IGNORECASE):
                    matches.append(asdict(ep))
            except re.error:
                continue
        return matches

    def list_patterns(self) -> List[dict]:
        return [asdict(p) for p in self._patterns.values()]

    def get_pattern(self, pattern_id: str) -> Optional[ErrorPattern]:
        return self._patterns.get(pattern_id)

    def delete_pattern(self, pattern_id: str) -> bool:
        if pattern_id in self._patterns:
            del self._patterns[pattern_id]
            return True
        return False


self_healer_engine = SelfHealerEngine()
