"""In-app changelog for tracking updates."""
import uuid, logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List

logger = logging.getLogger("gnosis.changelog")

@dataclass
class ChangelogEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: str = ""
    title: str = ""
    description: str = ""
    category: str = "feature"  # feature, bugfix, improvement, breaking
    date: str = ""
    tags: List[str] = field(default_factory=list)

INITIAL_ENTRIES = [
    ChangelogEntry(id="cl-1", version="1.0.0", title="Gnosis AI Agent Platform Launch", description="Initial release with 5-layer Cortex brain, 4-tier memory, and 30+ page routes", category="feature", date="2025-01-15", tags=["launch", "core"]),
    ChangelogEntry(id="cl-2", version="1.0.1", title="Security Hardening", description="Added prompt injection protection, PII detection, GDPR erasure, and input sanitization", category="improvement", date="2025-01-20", tags=["security"]),
    ChangelogEntry(id="cl-3", version="1.0.2", title="Performance Optimizations", description="LLM streaming SSE, Redis batching, query analyzer, and memory prefetching", category="improvement", date="2025-01-25", tags=["performance"]),
    ChangelogEntry(id="cl-4", version="1.1.0", title="Collaboration Features", description="Comment threads, annotations, approval gates, A/B comparison, and bookmarks", category="feature", date="2025-02-01", tags=["collaboration"]),
    ChangelogEntry(id="cl-5", version="1.1.1", title="Observability Suite", description="Time-travel debugger, flamegraphs, cost tracking, and drift detection", category="feature", date="2025-02-05", tags=["observability"]),
    ChangelogEntry(id="cl-6", version="1.2.0", title="Edge & Multi-Platform", description="Ollama bridge, Docker export, edge deployment, PWA support", category="feature", date="2025-02-10", tags=["edge", "deployment"]),
]

class ChangelogEngine:
    def __init__(self):
        self._entries: List[ChangelogEntry] = list(INITIAL_ENTRIES)

    def add_entry(self, version: str, title: str, description: str, category: str = "feature", tags: list = None) -> dict:
        entry = ChangelogEntry(version=version, title=title, description=description, category=category, date=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%d"), tags=tags or [])
        self._entries.insert(0, entry)
        return asdict(entry)

    def list_entries(self, limit: int = 20, category: str = None) -> List[dict]:
        entries = self._entries
        if category:
            entries = [e for e in entries if e.category == category]
        return [asdict(e) for e in entries[:limit]]

    def get_latest_version(self) -> str:
        return self._entries[0].version if self._entries else "0.0.0"

changelog_engine = ChangelogEngine()
