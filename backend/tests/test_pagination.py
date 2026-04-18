"""Tests for pagination utility."""
from app.core.pagination import paginate, paginate_query, PaginationParams


class TestPaginationParams:
    def test_defaults(self):
        p = PaginationParams()
        assert p.page == 1
        assert p.per_page == 20

    def test_clamps_negative_page(self):
        p = PaginationParams(page=-1)
        assert p.page == 1

    def test_clamps_zero_page(self):
        p = PaginationParams(page=0)
        assert p.page == 1

    def test_clamps_excessive_per_page(self):
        p = PaginationParams(per_page=500)
        assert p.per_page == 100

    def test_clamps_zero_per_page(self):
        p = PaginationParams(per_page=0)
        assert p.per_page == 1

    def test_offset_calculation(self):
        p = PaginationParams(page=3, per_page=10)
        assert p.offset == 20

    def test_offset_first_page(self):
        p = PaginationParams(page=1, per_page=10)
        assert p.offset == 0


class TestPaginate:
    def test_first_page(self):
        items = list(range(50))
        result = paginate(items, page=1, per_page=10)
        assert result["items"] == list(range(10))
        assert result["pagination"]["total"] == 50
        assert result["pagination"]["total_pages"] == 5
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_prev"] is False

    def test_middle_page(self):
        items = list(range(50))
        result = paginate(items, page=3, per_page=10)
        assert result["items"] == list(range(20, 30))
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_prev"] is True

    def test_last_page(self):
        items = list(range(25))
        result = paginate(items, page=3, per_page=10)
        assert result["items"] == [20, 21, 22, 23, 24]
        assert result["pagination"]["has_next"] is False
        assert result["pagination"]["has_prev"] is True

    def test_empty_list(self):
        result = paginate([], page=1, per_page=10)
        assert result["items"] == []
        assert result["pagination"]["total"] == 0
        assert result["pagination"]["total_pages"] == 1

    def test_single_page(self):
        items = [1, 2, 3]
        result = paginate(items, page=1, per_page=10)
        assert result["items"] == [1, 2, 3]
        assert result["pagination"]["has_next"] is False

    def test_beyond_last_page(self):
        items = list(range(10))
        result = paginate(items, page=5, per_page=10)
        assert result["items"] == []


class TestPaginateQuery:
    def test_basic_pagination(self):
        items = list(range(30))
        result = paginate_query(items, page=2, per_page=10)
        assert result["items"] == list(range(10, 20))

    def test_with_sort_key(self):
        items = [{"name": "c"}, {"name": "a"}, {"name": "b"}]
        result = paginate_query(items, page=1, per_page=10, sort_key="name", reverse=False)
        assert result["items"][0]["name"] == "a"
