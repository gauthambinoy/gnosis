"""Unit tests for AgentPermissionEngine."""

import pytest
from app.core.agent_permissions import AgentPermissionEngine


@pytest.fixture
def eng():
    return AgentPermissionEngine()


def test_grant_permission(eng):
    p = eng.grant_permission("a1", "u1", "viewer", "admin")
    assert p.role == "viewer"


def test_invalid_role(eng):
    with pytest.raises(ValueError):
        eng.grant_permission("a1", "u1", "superuser", "admin")


def test_check_view_with_viewer(eng):
    eng.grant_permission("a1", "u1", "viewer", "admin")
    assert eng.check_permission("a1", "u1", "view") is True
    assert eng.check_permission("a1", "u1", "execute") is False


def test_check_execute_with_operator(eng):
    eng.grant_permission("a1", "u1", "operator", "admin")
    assert eng.check_permission("a1", "u1", "execute") is True
    assert eng.check_permission("a1", "u1", "edit") is False


def test_check_admin_can_all(eng):
    eng.grant_permission("a1", "u1", "admin", "admin")
    for action in ("view", "execute", "edit", "manage"):
        assert eng.check_permission("a1", "u1", action) is True


def test_check_unknown_user_denied(eng):
    assert eng.check_permission("a1", "ghost", "view") is False


def test_check_invalid_action(eng):
    with pytest.raises(ValueError):
        eng.check_permission("a1", "u1", "frobnicate")


def test_grant_replaces_existing(eng):
    eng.grant_permission("a1", "u1", "viewer", "admin")
    eng.grant_permission("a1", "u1", "admin", "admin")
    perms = eng.list_permissions("a1")
    assert len(perms) == 1
    assert perms[0].role == "admin"


def test_revoke_permission(eng):
    p = eng.grant_permission("a1", "u1", "viewer", "admin")
    assert eng.revoke_permission(p.id) is True
    assert eng.list_permissions("a1") == []


def test_revoke_missing_raises(eng):
    with pytest.raises(KeyError):
        eng.revoke_permission("nope")


def test_list_permissions_filters_by_agent(eng):
    eng.grant_permission("a1", "u1", "viewer", "admin")
    eng.grant_permission("a2", "u1", "admin", "admin")
    assert len(eng.list_permissions("a1")) == 1
    assert len(eng.list_permissions("a2")) == 1
