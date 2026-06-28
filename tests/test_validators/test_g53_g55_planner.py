"""G53 + G55 — outcome-backward planning made enforceable (D1/E1).

G53 novel_candidate_presence: the run must surface >=1 option the treating team
did NOT name (traceable to the patient's endpoint, with a real testability path +
tier) OR honestly state none was found — negative-guarded so a novel-looking but
unbacked option cannot satisfy it. G55 plan_floor_coverage: the LLM-composed plan
may expand freely but must cover the deterministic red-line safety floor (a
contraindication-mandated expert/task is present). LLM judges, gate verifies.
"""
from __future__ import annotations

from opl_cancer.validators.gates.g53_novel_candidate_presence import (
    G53NovelCandidatePresenceGate,
)
from opl_cancer.validators.gates.g55_plan_floor_coverage import (
    G55PlanFloorCoverageGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


# ---- G53 ----

def test_g53_pass_with_real_novel_candidate():
    res = G53NovelCandidatePresenceGate().check({"claims": [
        {"claim_id": "x", "not_in_treating_plan": True,
         "testability_path": "DepMap co-essentiality + PDO assay", "claim_layer": "speculative"},
    ]})
    assert res.status == GateStatus.PASS


def test_g53_pass_with_honest_null():
    res = G53NovelCandidatePresenceGate().check(
        {"claims": [{"claim_id": "y"}], "no_option_beyond_plan": True}
    )
    assert res.status == GateStatus.PASS


def test_g53_block_when_nothing_novel_and_no_honest_null():
    res = G53NovelCandidatePresenceGate().check(
        {"claims": [{"claim_id": "y", "claim_text": "re-narrates SoC"}]}
    )
    assert res.status == GateStatus.FAIL and res.block is True


def test_g53_block_when_novel_candidate_unbacked_negative_guard():
    # not_in_treating_plan but NO testability_path/tier → must not satisfy the gate
    res = G53NovelCandidatePresenceGate().check({"claims": [
        {"claim_id": "z", "not_in_treating_plan": True, "claim_text": "shiny but unbacked"},
    ]})
    assert res.status == GateStatus.FAIL and res.block is True


# ---- G55 ----

def test_g55_skip_when_no_red_line_floor():
    res = G55PlanFloorCoverageGate().check({"planned_experts": ["rosa", "bert"], "floor_required": []})
    assert res.status == GateStatus.SKIP


def test_g55_pass_when_floor_covered():
    res = G55PlanFloorCoverageGate().check(
        {"planned_experts": ["rosa", "bert", "mary"], "floor_required": ["mary"]}
    )
    assert res.status == GateStatus.PASS


def test_g55_block_when_floor_expert_dropped():
    res = G55PlanFloorCoverageGate().check(
        {"planned_experts": ["rosa", "bert"], "floor_required": ["mary", "dennis"]}
    )
    assert res.status == GateStatus.FAIL and res.block is True
