"""Unit tests for ApprovalGateEngine."""

import pytest
from app.core.approval_gates import ApprovalGateEngine


@pytest.fixture
def eng():
    return ApprovalGateEngine()


def test_create_gate(eng):
    g = eng.create_gate("p1", 0, ["alice"])
    assert g.status == "pending"
    assert g.required_approvers == ["alice"]


def test_approve_single_required(eng):
    g = eng.create_gate("p1", 0, ["alice"])
    g2 = eng.approve(g.id, "alice")
    assert g2.status == "approved"


def test_approve_multi_required_partial(eng):
    g = eng.create_gate("p1", 0, ["alice", "bob"])
    eng.approve(g.id, "alice")
    assert eng._gates[g.id].status == "pending"
    eng.approve(g.id, "bob")
    assert eng._gates[g.id].status == "approved"


def test_reject_marks_rejected(eng):
    g = eng.create_gate("p1", 0, ["alice"])
    g2 = eng.reject(g.id, "alice", reason="no")
    assert g2.status == "rejected"


def test_check_gate_true_after_approve(eng):
    g = eng.create_gate("p1", 0, ["alice"])
    eng.approve(g.id, "alice")
    assert eng.check_gate(g.id) is True


def test_check_gate_false_pending(eng):
    g = eng.create_gate("p1", 0, ["alice"])
    assert eng.check_gate(g.id) is False


def test_approve_missing_raises(eng):
    with pytest.raises(KeyError):
        eng.approve("missing", "alice")


def test_reject_missing_raises(eng):
    with pytest.raises(KeyError):
        eng.reject("missing", "alice")


def test_check_missing_raises(eng):
    with pytest.raises(KeyError):
        eng.check_gate("missing")


def test_list_pipeline_gates(eng):
    eng.create_gate("p1", 0, ["a"])
    eng.create_gate("p1", 1, ["a"])
    eng.create_gate("p2", 0, ["a"])
    assert len(eng.list_pipeline_gates("p1")) == 2
    assert len(eng.list_pipeline_gates("p2")) == 1
