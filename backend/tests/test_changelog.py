"""Tests for changelog engine."""
from app.core.changelog import ChangelogEngine


class TestChangelogEngine:
    def setup_method(self):
        self.engine = ChangelogEngine()

    def test_initial_entries(self):
        entries = self.engine.list_entries()
        assert len(entries) >= 5

    def test_add_entry(self):
        entry = self.engine.add_entry("2.0.0", "Major Release", "Big update", category="feature", tags=["major"])
        assert entry["version"] == "2.0.0"
        assert entry["title"] == "Major Release"

    def test_latest_version_after_add(self):
        self.engine.add_entry("99.0.0", "Future", "Far future")
        assert self.engine.get_latest_version() == "99.0.0"

    def test_filter_by_category(self):
        entries = self.engine.list_entries(category="feature")
        assert len(entries) > 0
        assert all(e["category"] == "feature" for e in entries)

    def test_limit(self):
        entries = self.engine.list_entries(limit=2)
        assert len(entries) <= 2

    def test_add_entry_appears_first(self):
        self.engine.add_entry("3.0.0", "New Entry", "Brand new")
        entries = self.engine.list_entries()
        assert entries[0]["version"] == "3.0.0"

    def test_entry_has_date(self):
        entry = self.engine.add_entry("4.0.0", "Dated", "Has date")
        assert entry["date"] != ""
