"""Tests for webhook dispatcher."""

from app.core.webhook_dispatcher import WebhookDispatcher, ALL_EVENTS


class TestWebhookDispatcher:
    def setup_method(self):
        self.dispatcher = WebhookDispatcher()

    def test_register_endpoint(self):
        ep = self.dispatcher.register(
            "https://example.com/hook", ["execution.completed"]
        )
        assert ep.url == "https://example.com/hook"
        assert ep.active is True

    def test_unregister(self):
        ep = self.dispatcher.register("https://example.com/hook", ["*"])
        assert self.dispatcher.unregister(ep.id) is True
        assert self.dispatcher.unregister("nonexistent") is False

    def test_list_endpoints(self):
        self.dispatcher.register("https://a.com", ["*"], workspace_id="ws-1")
        self.dispatcher.register("https://b.com", ["*"], workspace_id="ws-2")
        all_eps = self.dispatcher.list_endpoints()
        assert len(all_eps) == 2
        ws1_eps = self.dispatcher.list_endpoints(workspace_id="ws-1")
        assert len(ws1_eps) == 1

    def test_all_events_defined(self):
        assert len(ALL_EVENTS) > 0
        assert "execution.completed" in ALL_EVENTS
        assert "agent.error" in ALL_EVENTS

    def test_stats_empty(self):
        stats = self.dispatcher.stats
        assert stats["total_endpoints"] == 0
        assert stats["active_endpoints"] == 0

    def test_stats_after_register(self):
        self.dispatcher.register("https://a.com", ["*"])
        stats = self.dispatcher.stats
        assert stats["total_endpoints"] == 1
        assert stats["active_endpoints"] == 1

    def test_register_with_secret(self):
        ep = self.dispatcher.register("https://a.com", ["*"], secret="my-secret")
        assert ep.secret == "my-secret"

    def test_register_with_workspace(self):
        ep = self.dispatcher.register(
            "https://a.com", ["*"], workspace_id="ws-1", created_by="user-1"
        )
        assert ep.workspace_id == "ws-1"
        assert ep.created_by == "user-1"
