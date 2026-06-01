"""Test G13 reviewer-model-distinct gate (harness-split redefinition).

Reasoning is now two host-agent subagent dispatches (executor + reviewer); the
gate verifies the two report artifacts DECLARE distinct model identities, and
BLOCKs when a declaration is absent.
"""
from opl_cancer.validators.gates.g13_reviewer_model_distinct import (
    G13ReviewerModelDistinctGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


# ── report-artifact shape (the new model-declaration carriers) ──────────────


def test_g13_pass_distinct_report_artifacts() -> None:
    gate = G13ReviewerModelDistinctGate()
    claim = {
        "executor_report": {"_meta": {"model_id": "claude-opus-4-7"}},
        "reviewer_report": {"reviewer_model": "minimax-m2-7"},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS
    assert r.evidence == {"executor": "claude-opus-4-7", "reviewer": "minimax-m2-7"}


def test_g13_fail_same_model_report_artifacts() -> None:
    gate = G13ReviewerModelDistinctGate()
    claim = {
        "executor_report": {"_meta": {"model": "claude-opus-4-7"}},
        "reviewer_report": {"reviewer_model": "claude-opus-4-7"},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "echo-chamber" in r.message


def test_g13_block_when_executor_declaration_absent() -> None:
    # No executor model anywhere (and models.yaml fallback may or may not exist;
    # construct a gate with no fallback to force the absent path).
    gate = G13ReviewerModelDistinctGate()
    gate.executor_model_id = None  # force: no models.yaml fallback
    claim = {
        "executor_report": {"_meta": {"produced_by": "host-agent"}},  # placeholder only
        "reviewer_report": {"reviewer_model": "minimax-m2-7"},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "executor report carries no model declaration" in r.message


def test_g13_block_when_reviewer_declaration_absent() -> None:
    gate = G13ReviewerModelDistinctGate()
    claim = {
        "executor_report": {"_meta": {"model_id": "claude-opus-4-7"}},
        "reviewer_report": {"reviewer_model": "host-agent-reviewer"},  # placeholder
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "reviewer report carries no model declaration" in r.message


def test_g13_block_when_both_reports_missing_entirely() -> None:
    gate = G13ReviewerModelDistinctGate()
    gate.executor_model_id = None
    r = gate.check({})
    assert r.status == GateStatus.FAIL
    assert r.block is True


# ── legacy nested shape (executor.model_id / reviewer.model_id) ─────────────


def test_g13_pass_distinct_models_legacy_shape() -> None:
    gate = G13ReviewerModelDistinctGate()
    claim = {
        "executor": {"model_id": "claude-opus-4-7"},
        "reviewer": {"model_id": "minimax-m2-7"},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g13_fail_same_model_legacy_shape() -> None:
    gate = G13ReviewerModelDistinctGate()
    claim = {
        "executor": {"model_id": "claude-opus-4-7"},
        "reviewer": {"model_id": "claude-opus-4-7"},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "echo-chamber" in r.message


# ── reviewer_pool enforcement (driven by models.yaml when present) ──────────


def test_g13_block_reviewer_not_in_pool() -> None:
    gate = G13ReviewerModelDistinctGate()
    # only triggers if pool was loaded from models.yaml at construction
    if not gate.reviewer_pool_ids:
        return  # environment didn't ship models.yaml — skip
    claim = {
        "executor_report": {"_meta": {"model_id": "claude-opus-4-7"}},
        "reviewer_report": {"reviewer_model": "totally-bogus-model"},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "not in reviewer_pool" in r.message
