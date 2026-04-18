"""Reusable pagination utilities for all list endpoints."""

from dataclasses import dataclass
from typing import List, Any, TypeVar

T = TypeVar("T")


@dataclass
class PaginationParams:
    page: int = 1
    per_page: int = 20

    def __post_init__(self):
        self.page = max(1, self.page)
        self.per_page = max(1, min(100, self.per_page))

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


def paginate(items: List[Any], page: int = 1, per_page: int = 20) -> dict:
    """Apply pagination to a list and return standardized response."""
    params = PaginationParams(page=page, per_page=per_page)
    total = len(items)
    total_pages = max(1, (total + params.per_page - 1) // params.per_page)

    start = params.offset
    end = start + params.per_page
    page_items = items[start:end]

    return {
        "items": page_items,
        "pagination": {
            "page": params.page,
            "per_page": params.per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": params.page < total_pages,
            "has_prev": params.page > 1,
        },
    }


def paginate_query(
    items: List[Any],
    page: int = 1,
    per_page: int = 20,
    sort_key: str = None,
    reverse: bool = True,
) -> dict:
    """Paginate with optional sorting."""
    if sort_key:
        try:
            items = sorted(
                items,
                key=lambda x: (
                    getattr(x, sort_key, x.get(sort_key, ""))
                    if isinstance(x, dict)
                    else getattr(x, sort_key, "")
                ),
                reverse=reverse,
            )
        except (AttributeError, TypeError):
            pass
    return paginate(items, page, per_page)
