"""Unit tests for DataResidencyEngine."""

import pytest
from app.core.data_residency import DataResidencyEngine, AVAILABLE_REGIONS


@pytest.fixture
def eng():
    return DataResidencyEngine()


def test_set_policy_valid(eng):
    p = eng.set_policy("ws1", "eu-west")
    assert p.region == "eu-west"
    assert p.enforced is True


def test_set_policy_invalid_region(eng):
    with pytest.raises(ValueError):
        eng.set_policy("ws1", "mars")


def test_get_policy(eng):
    eng.set_policy("ws1", "us-east")
    assert eng.get_policy("ws1").region == "us-east"
    assert eng.get_policy("missing") is None


def test_list_regions(eng):
    regions = eng.list_regions()
    assert regions == AVAILABLE_REGIONS
    assert any(r["id"] == "us-east" for r in regions)


def test_validate_no_policy_allows(eng):
    res = eng.validate_residency("ws1", "us-east")
    assert res["valid"] is True


def test_validate_matching_region(eng):
    eng.set_policy("ws1", "eu-west")
    res = eng.validate_residency("ws1", "eu-west")
    assert res["valid"] is True


def test_validate_mismatch_blocks(eng):
    eng.set_policy("ws1", "eu-west")
    res = eng.validate_residency("ws1", "us-east")
    assert res["valid"] is False
    assert "eu-west" in res["reason"]


def test_validate_unenforced_allows(eng):
    eng.set_policy("ws1", "eu-west", enforced=False)
    res = eng.validate_residency("ws1", "us-east")
    assert res["valid"] is True
