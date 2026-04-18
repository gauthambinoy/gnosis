"""Execution Comment Threads — threaded comments on executions."""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid


@dataclass
class Comment:
    id: str
    execution_id: str
    parent_id: Optional[str]
    user_id: str
    text: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    reactions: dict = field(default_factory=dict)


class CommentThreadEngine:
    def __init__(self):
        self._comments: Dict[str, Comment] = {}

    def add_comment(self, execution_id: str, user_id: str, text: str) -> Comment:
        comment = Comment(
            id=str(uuid.uuid4()),
            execution_id=execution_id,
            parent_id=None,
            user_id=user_id,
            text=text,
        )
        self._comments[comment.id] = comment
        return comment

    def reply(self, parent_id: str, user_id: str, text: str) -> Comment:
        parent = self._comments.get(parent_id)
        if not parent:
            raise KeyError(f"Parent comment {parent_id} not found")
        comment = Comment(
            id=str(uuid.uuid4()),
            execution_id=parent.execution_id,
            parent_id=parent_id,
            user_id=user_id,
            text=text,
        )
        self._comments[comment.id] = comment
        return comment

    def list_thread(self, execution_id: str) -> List[dict]:
        return [
            asdict(c) for c in self._comments.values() if c.execution_id == execution_id
        ]

    def add_reaction(self, comment_id: str, emoji: str, user_id: str) -> Comment:
        comment = self._comments.get(comment_id)
        if not comment:
            raise KeyError(f"Comment {comment_id} not found")
        if emoji not in comment.reactions:
            comment.reactions[emoji] = []
        if user_id not in comment.reactions[emoji]:
            comment.reactions[emoji].append(user_id)
        comment.updated_at = datetime.now(timezone.utc).isoformat()
        return comment


comment_engine = CommentThreadEngine()
