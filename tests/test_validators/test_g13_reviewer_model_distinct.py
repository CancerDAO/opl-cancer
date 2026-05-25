"""Test G13 reviewer-model-distinct gate."""
from opl_cancer.validators.gates.g13_reviewer_model_distinct import (
    G13ReviewerModelDistinctGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


def test_g13_pass_distinct_models() -> None:
    gate = G13ReviewerModelDistinctGate()
    claim = {
        "executor": {"model_id": "claude-opus-4-7"},
        "reviewer": {"model_id": "minimax-m2-7"},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g13_fail_same_model() -> None:
    gate = G13ReviewerModelDistinctGate()
    claim = {
        "executor": {"model_id": "claude-opus-4-7"},
        "reviewer": {"model_id": "claude-opus-4-7"},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "echo-chamber" in r.message


def test_g13_skip_missing_ids() -> None:
    gate = G13ReviewerModelDistinctGate()
    r = gate.check({"executor": {}, "reviewer": {}})
    assert r.status == GateStatus.SKIP


def test_g13_block_reviewer_not_in_pool() -> None:
    gate = G13ReviewerModelDistinctGate()
    # only triggers if pool was loaded from models.yaml at construction
    if not gate.reviewer_pool_ids:
        return  # environment didn't ship models.yaml — skip
    claim = {
        "executor": {"model_id": "claude-opus-4-7"},
        "reviewer": {"model_id": "totally-bogus-model"},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
