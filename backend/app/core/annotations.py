"""Inline Response Annotations — highlight, note, correct, or question agent responses."""
from dataclasses import dataclass, field, asdict
from typing import Dict, List
from datetime import datetime, timezone
import uuid


@dataclass
class Annotation:
    id: str
    execution_id: str
    user_id: str
    text: str
    selection_start: int
    selection_end: int
    type: str  # highlight / note / correction / question
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


VALID_TYPES = {"highlight", "note", "correction", "question"}


class AnnotationEngine:
    def __init__(self):
        self._annotations: Dict[str, Annotation] = {}

    def add_annotation(
        self,
        execution_id: str,
        user_id: str,
        text: str,
        selection_start: int,
        selection_end: int,
        annotation_type: str,
    ) -> Annotation:
        if annotation_type not in VALID_TYPES:
            raise ValueError(f"Invalid type: {annotation_type}. Must be one of {VALID_TYPES}")
        ann = Annotation(
            id=str(uuid.uuid4()),
            execution_id=execution_id,
            user_id=user_id,
            text=text,
            selection_start=selection_start,
            selection_end=selection_end,
            type=annotation_type,
        )
        self._annotations[ann.id] = ann
        return ann

    def list_annotations(self, execution_id: str) -> List[dict]:
        return [
            asdict(a)
            for a in self._annotations.values()
            if a.execution_id == execution_id
        ]

    def delete_annotation(self, annotation_id: str) -> bool:
        return self._annotations.pop(annotation_id, None) is not None


annotation_engine = AnnotationEngine()
