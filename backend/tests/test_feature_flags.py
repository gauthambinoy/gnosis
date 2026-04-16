"""Tests for feature flag system."""
import pytest
from app.core.feature_flags import FeatureFlagEngine


class TestFeatureFlags:
    def setup_method(self):
        self.engine = FeatureFlagEngine()

    def test_create_flag(self):
        flag = self.engine.create_flag("test-flag", "A test flag")
        assert flag["name"] == "test-flag"
        assert flag["enabled"] is True

    def test_is_enabled_nonexistent(self):
        assert self.engine.is_enabled("nonexistent") is False

    def test_is_enabled_after_create(self):
        self.engine.create_flag("my-flag")
        assert self.engine.is_enabled("my-flag") is True

    def test_update_flag_disable(self):
        result = self.engine.create_flag("toggle-flag")
        self.engine.update_flag(result["id"], enabled=False)
        assert self.engine.is_enabled("toggle-flag") is False

    def test_list_flags(self):
        self.engine.create_flag("flag-1")
        self.engine.create_flag("flag-2")
        flags = self.engine.list_flags()
        assert len(flags) == 2

    def test_user_scope_targeting(self):
        result = self.engine.create_flag("user-flag", scope="user")
        self.engine.update_flag(result["id"], target_ids=["user-1"])
        assert self.engine.is_enabled("user-flag", user_id="user-1") is True
        assert self.engine.is_enabled("user-flag", user_id="user-2") is False

    def test_workspace_scope_targeting(self):
        result = self.engine.create_flag("ws-flag", scope="workspace")
        self.engine.update_flag(result["id"], target_ids=["ws-1"])
        assert self.engine.is_enabled("ws-flag", workspace_id="ws-1") is True
        assert self.engine.is_enabled("ws-flag", workspace_id="ws-2") is False

    def test_update_nonexistent_flag(self):
        result = self.engine.update_flag("no-such-id", enabled=False)
        assert "error" in result

    def test_create_flag_with_description(self):
        flag = self.engine.create_flag("desc-flag", description="My description")
        assert flag["description"] == "My description"
