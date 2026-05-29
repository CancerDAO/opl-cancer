"""Tests for G43 epistemic_symmetry gate (reasoning-quality layer, ADR-0026).

Imports the gate module DIRECTLY (before the orchestrator registers it) so the
unit test stands on its own. Replays the KRAS-G12C/MSS cross-model findings:
  * Finding 2 (CRITICAL): asymmetric skepticism — trusted n=981, dismissed a
    contradicting n=30 as "small sample" while never holding the relied source
    to the same bar.
  * Finding 8 (MINOR): flattened pooling — pooled HR 0.68 I²=0% across
    non-equivalent agents with no clinical-heterogeneity flag.
G43 is WARN-only (Fork A quality gate): a violation FAILs with block=False.
"""
from opl_cancer.validators.gates.g43_epistemic_symmetry import (
    G43EpistemicSymmetryGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


# ── SKIP: neither field present ─────────────────────────────────────────────
def test_g43_skip_no_fields() -> None:
    gate = G43EpistemicSymmetryGate()
    r = gate.check({"claim_id": "c_001", "claim_text": "no skepticism block here"})
    assert r.status == GateStatus.SKIP
    assert r.block is False


# ── BLOCKING (warn) case — replay Finding 2: asymmetric skepticism ──────────
def test_g43_fail_asymmetric_skepticism_not_reconciled() -> None:
    """The finding: dismissed a contradicting n=30 source as 'small sample'
    while relying on an n=981 source, never affirming the same bar applied."""
    gate = G43EpistemicSymmetryGate()
    claim = {
        "claim_id": "c_kras",
        "claim_text": "Sotorasib + panitumumab is favoured for KRAS-G12C mCRC.",
        "skepticism": {
            "dismissed": [
                {"ref": "PMID:30000030", "ground": "small sample (n=30)"},
            ],
            "relied": [
                {"ref": "PMID:30000981"},  # the trusted n=981 cohort
            ],
            # symmetric NOT set to true, no rationale → unreconciled asymmetry
        },
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False  # WARN-only (Fork A)
    kinds = {v["kind"] for v in r.evidence["violations"]}
    assert "asymmetry_not_reconciled" in kinds


def test_g43_fail_symmetric_false_no_rationale() -> None:
    """Producer explicitly declared asymmetry but gave no rationale."""
    gate = G43EpistemicSymmetryGate()
    claim = {
        "claim_id": "c_a",
        "claim_text": "x",
        "skepticism": {
            "dismissed": [{"ref": "PMID:1", "ground": "off-population"}],
            "relied": [{"ref": "PMID:2"}],
            "symmetric": False,
            # no rationale
        },
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False
    kinds = {v["kind"] for v in r.evidence["violations"]}
    assert "asymmetric_no_rationale" in kinds


def test_g43_fail_dismissed_without_ground() -> None:
    gate = G43EpistemicSymmetryGate()
    claim = {
        "claim_id": "c_b",
        "claim_text": "x",
        "skepticism": {
            "dismissed": [{"ref": "PMID:9"}],  # no ground
            "relied": [],
            "symmetric": True,
        },
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False
    kinds = {v["kind"] for v in r.evidence["violations"]}
    assert "dismissed_without_ground" in kinds


# ── BLOCKING (warn) case — replay Finding 8: flattened pooling ──────────────
def test_g43_fail_flattened_pooling_low_i2_no_flag() -> None:
    """Pooled HR 0.68 with I²=0% across non-equivalent agents, no heterogeneity
    flag — the finding-8 flattening."""
    gate = G43EpistemicSymmetryGate()
    claim = {
        "claim_id": "c_pool",
        "claim_text": "Pooled HR 0.68 (I²=0%) supports the combination.",
        "pooled_estimate": {
            "agents": ["Aviv", "Bert", "Cara"],
            "i2": 0.0,
            # heterogeneity_flagged absent → not flagged
        },
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False
    kinds = {v["kind"] for v in r.evidence["violations"]}
    assert "flattened_pooling" in kinds


def test_g43_fail_flattened_pooling_percent_scale() -> None:
    """I² written on the 0-100 scale (24%) is still 'low' and must be flagged."""
    gate = G43EpistemicSymmetryGate()
    claim = {
        "claim_id": "c_pool2",
        "claim_text": "x",
        "pooled_estimate": {
            "agents": ["A", "B"],
            "i2": 24.0,
            "heterogeneity_flagged": False,
        },
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False
    assert any(v["kind"] == "flattened_pooling" for v in r.evidence["violations"])


# ── CLEAN PASSING cases ─────────────────────────────────────────────────────
def test_g43_pass_symmetric_skepticism_affirmed() -> None:
    gate = G43EpistemicSymmetryGate()
    claim = {
        "claim_id": "c_ok",
        "claim_text": "x",
        "skepticism": {
            "dismissed": [{"ref": "PMID:30000030", "ground": "retracted 2024"}],
            "relied": [{"ref": "PMID:30000981"}],
            "symmetric": True,
            "rationale": (
                "Applied the same RCT-vs-cohort bar to both; the dismissed source "
                "was retracted, not merely small."
            ),
        },
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS
    assert r.block is False


def test_g43_asymmetry_with_rationale_clears_clause_a_only() -> None:
    """A rationale clears clause (a) (no 'asymmetric_no_rationale'), but clause
    (b) still fires because symmetric is not explicitly true."""
    gate = G43EpistemicSymmetryGate()
    claim = {
        "claim_id": "c_ok2",
        "claim_text": "x",
        "skepticism": {
            "dismissed": [{"ref": "PMID:1", "ground": "preclinical only"}],
            "relied": [{"ref": "PMID:2"}],
            "symmetric": False,
            "rationale": (
                "Down-weighted the preclinical signal vs. a phase-III readout; "
                "the bar difference is design level, not convenience."
            ),
        },
    }
    r = gate.check(claim)
    # symmetric=False but rationale given → no asymmetric_no_rationale; and
    # symmetric is not True so reconciliation relies on the rationale path.
    # The spec's (b) clause fires only when symmetric is not explicitly true,
    # so an explained asymmetry should still be reported as unreconciled —
    # confirm the gate treats a rationale as sufficient for clause (a) only.
    assert r.status == GateStatus.FAIL
    kinds = {v["kind"] for v in r.evidence["violations"]}
    assert "asymmetric_no_rationale" not in kinds
    assert "asymmetry_not_reconciled" in kinds


def test_g43_pass_pooled_high_i2_no_flag_needed() -> None:
    """High I² is G17's domain, not G43's low-I² flattening check; G43 passes."""
    gate = G43EpistemicSymmetryGate()
    claim = {
        "claim_id": "c_ok3",
        "claim_text": "x",
        "pooled_estimate": {
            "agents": ["A", "B"],
            "i2": 0.62,  # high — not the flattening failure
        },
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g43_pass_pooled_low_i2_flagged() -> None:
    gate = G43EpistemicSymmetryGate()
    claim = {
        "claim_id": "c_ok4",
        "claim_text": "x",
        "pooled_estimate": {
            "agents": ["A", "B"],
            "i2": 0.0,
            "heterogeneity_flagged": True,
        },
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g43_pass_single_agent_pool_not_flattening() -> None:
    """Only one distinct agent ⇒ no cross-agent flattening to flag."""
    gate = G43EpistemicSymmetryGate()
    claim = {
        "claim_id": "c_ok5",
        "claim_text": "x",
        "pooled_estimate": {"agents": ["A", "A"], "i2": 0.0},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g43_pass_only_dismissed_no_relied() -> None:
    """Dismissed-with-ground but nothing relied on ⇒ clause (b) does not fire."""
    gate = G43EpistemicSymmetryGate()
    claim = {
        "claim_id": "c_ok6",
        "claim_text": "x",
        "skepticism": {
            "dismissed": [{"ref": "PMID:1", "ground": "retracted"}],
            "relied": [],
        },
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS
