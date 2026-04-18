"""Shared Response Bookmarks — bookmark excellent responses for reference."""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid


@dataclass
class Bookmark:
    id: str
    user_id: str
    execution_id: str
    title: str
    note: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class BookmarkEngine:
    def __init__(self):
        self._bookmarks: Dict[str, Bookmark] = {}

    def create(
        self,
        user_id: str,
        execution_id: str,
        title: str,
        note: str = "",
        tags: Optional[List[str]] = None,
    ) -> Bookmark:
        bm = Bookmark(
            id=str(uuid.uuid4()),
            user_id=user_id,
            execution_id=execution_id,
            title=title,
            note=note,
            tags=tags or [],
        )
        self._bookmarks[bm.id] = bm
        return bm

    def get(self, bookmark_id: str) -> Bookmark:
        bm = self._bookmarks.get(bookmark_id)
        if not bm:
            raise KeyError(f"Bookmark {bookmark_id} not found")
        return bm

    def delete(self, bookmark_id: str) -> bool:
        return self._bookmarks.pop(bookmark_id, None) is not None

    def list_all(self) -> List[dict]:
        return [asdict(b) for b in self._bookmarks.values()]

    def list_by_tag(self, tag: str) -> List[dict]:
        return [asdict(b) for b in self._bookmarks.values() if tag in b.tags]

    def search_bookmarks(self, query: str) -> List[dict]:
        q = query.lower()
        return [
            asdict(b)
            for b in self._bookmarks.values()
            if q in b.title.lower() or q in b.note.lower()
        ]

    def all_tags(self) -> List[str]:
        tags: set = set()
        for b in self._bookmarks.values():
            tags.update(b.tags)
        return sorted(tags)


bookmark_engine = BookmarkEngine()
