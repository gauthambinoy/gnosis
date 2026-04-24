"""Unit tests for agent_export."""

from app.core.agent_export import (
    export_agent,
    import_agent,
    export_agents_bulk,
    import_agents_bulk,
    validate_import,
    EXPORT_VERSION,
)


def test_export_includes_metadata():
    data = export_agent({"name": "A", "system_prompt": "Be helpful"})
    assert data["gnosis_export"] is True
    assert data["version"] == EXPORT_VERSION
    assert data["agent"]["name"] == "A"


def test_export_strips_secrets():
    data = export_agent({"name": "A", "api_keys": "secret", "secrets": {"k": "v"}, "internal_id": 42})
    a = data["agent"]
    assert "api_keys" not in a
    assert "secrets" not in a
    assert "internal_id" not in a


def test_validate_import_rejects_wrong_dict():
    ok, _ = validate_import({"foo": "bar"})
    assert ok is False


def test_validate_import_rejects_non_dict():
    ok, _ = validate_import("not a dict")
    assert ok is False


def test_validate_import_accepts_valid():
    ok, _ = validate_import({"gnosis_export": True, "agent": {}})
    assert ok is True


def test_import_round_trip_assigns_new_id():
    exported = export_agent({"id": "old-id", "name": "A", "system_prompt": "s"})
    imported = import_agent(exported)
    assert imported is not None
    assert imported["id"] != "old-id"
    assert imported["name"] == "A"
    assert "imported_at" in imported


def test_import_invalid_returns_none():
    assert import_agent({"not": "valid"}) is None


def test_bulk_export_round_trip():
    agents = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
    bundle = export_agents_bulk(agents)
    assert bundle["count"] == 3
    imported = import_agents_bulk(bundle)
    assert len(imported) == 3
    assert {a["name"] for a in imported} == {"A", "B", "C"}
    # Each gets a new id
    assert len({a["id"] for a in imported}) == 3


def test_bulk_import_invalid_returns_empty():
    assert import_agents_bulk({"invalid": True}) == []
