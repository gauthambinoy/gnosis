import pytest

pytestmark = pytest.mark.anyio

"""Tests for template list, get, and deploy endpoints."""


async def test_list_templates(client, api_prefix):
    resp = await client.get(f"{api_prefix}/templates")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    assert len(data["templates"]) == 8
    assert len(data["categories"]) > 0


async def test_get_template(client, api_prefix):
    resp = await client.get(f"{api_prefix}/templates/email-triage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "email-triage"
    assert "name" in data
    assert "steps" in data


async def test_get_template_not_found(client, api_prefix):
    resp = await client.get(f"{api_prefix}/templates/nonexistent")
    assert resp.status_code == 404


async def test_deploy_template(client, api_prefix):
    resp = await client.post(
        f"{api_prefix}/templates/email-triage/deploy",
        json={
            "name": "My Email Agent",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "deployed"
    assert data["template_id"] == "email-triage"
    assert data["agent"]["name"] == "My Email Agent"
    assert "id" in data["agent"]
