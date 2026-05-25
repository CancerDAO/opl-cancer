"""Tests for v1.5 epistemic gates G25 + G26.

P0-5 (docs/ANTI_PATTERNS_v1.4.md AP-1, AP-2, AP-3).
"""
from __future__ import annotations

from opl_cancer.validators.gates import (
    G25DeferredEvidenceBlockGate,
    G26EvidenceStrengthRankingGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


# ─── G25 — deferred-evidence BLOCK ──────────────────────────────────────


def test_g25_passes_when_no_deferred_marker() -> None:
    g = G25DeferredEvidenceBlockGate()
    r = g.check({"run_stage": "wave5_delivery", "verdict": "regimen X recommended"})
    assert r.status is GateStatus.PASS


def test_g25_skips_outside_delivery_stage() -> None:
    g = G25DeferredEvidenceBlockGate()
    r = g.check({"run_stage": "wave1_retrieval", "deferred": True})
    assert r.status is GateStatus.SKIP


def test_g25_blocks_on_explicit_deferred_flag_at_delivery() -> None:
    g = G25DeferredEvidenceBlockGate()
    r = g.check(
        {
            "run_stage": "wave5_delivery",
            "deferred": True,
            "evidence_criticality": "critical",
        }
    )
    assert r.status is GateStatus.FAIL
    assert r.block is True
    assert "deferred" in r.message.lower()


def test_g25_blocks_on_marker_phrase_at_delivery() -> None:
    g = G25DeferredEvidenceBlockGate()
    r = g.check(
        {
            "run_stage": "wave5_delivery",
            "verdict": "regimen ranking [SKIPPED] due to Wave 3 missing",
        }
    )
    assert r.status is GateStatus.FAIL


def test_g25_blocks_on_docker_unavailable_wave3_skipped_phrase() -> None:
    """This is the exact failure mode from the PT-EXAMPLE-A run."""
    g = G25DeferredEvidenceBlockGate()
    r = g.check(
        {
            "run_stage": "wave5_delivery",
            "summary": "Docker unavailable, Wave 3 skipped",
        }
    )
    assert r.status is GateStatus.FAIL
    assert "wave 3 skipped" in r.message.lower() or "docker" in r.message.lower()


def test_g25_passes_when_non_critical_evidence_deferred() -> None:
    g = G25DeferredEvidenceBlockGate()
    r = g.check(
        {
            "run_stage": "wave5_delivery",
            "deferred": True,
            "evidence_criticality": "informational",
        }
    )
    assert r.status is GateStatus.PASS


def test_g25_passes_when_patient_opted_out_explicitly() -> None:
    g = G25DeferredEvidenceBlockGate()
    r = g.check(
        {
            "run_stage": "wave5_delivery",
            "deferred": True,
            "patient_optout": True,
            "patient_optout_rationale": "patient prefers to skip Wave 3 ctDNA monitoring",
        }
    )
    assert r.status is GateStatus.PASS


# ─── G26 — evidence-strength → ranking demotion ────────────────────────


def test_g26_skips_when_no_elo_boost() -> None:
    g = G26EvidenceStrengthRankingGate()
    r = g.check({"regimen_id": "H02"})
    assert r.status is GateStatus.SKIP


def test_g26_skips_when_elo_boost_zero_or_negative() -> None:
    g = G26EvidenceStrengthRankingGate()
    r = g.check({"elo_boost": 0, "evidence_anchor": {"subgroup_match_fraction": 0.3}})
    assert r.status is GateStatus.SKIP


def test_g26_passes_when_evidence_strong_enough() -> None:
    g = G26EvidenceStrengthRankingGate()
    r = g.check(
        {
            "elo_boost": 25,
            "evidence_anchor": {
                "subgroup_match_fraction": 0.7,
                "i_squared": 30,
            },
        }
    )
    assert r.status is GateStatus.PASS


def test_g26_blocks_when_subgroup_mismatch_and_boost_too_high() -> None:
    """v1.4 H02 sotorasib pattern: subgroup-mismatch + boost not capped."""
    g = G26EvidenceStrengthRankingGate()
    r = g.check(
        {
            "elo_boost": 25,
            "evidence_anchor": {
                "subgroup_match_fraction": 0.3,
                "i_squared": 30,
            },
            "regimen_id": "H02",
        }
    )
    assert r.status is GateStatus.FAIL
    assert r.block is True
    assert "subgroup" in r.message.lower()


def test_g26_blocks_when_high_heterogeneity_and_boost_too_high() -> None:
    g = G26EvidenceStrengthRankingGate()
    r = g.check(
        {
            "elo_boost": 30,
            "evidence_anchor": {
                "subgroup_match_fraction": 0.6,
                "i_squared": 77.4,  # the v1.4 pool I²
            },
        }
    )
    assert r.status is GateStatus.FAIL
    assert "i_squared" in r.message.lower() or "heterogeneity" in r.message.lower()


def test_g26_passes_when_boost_capped_and_demotion_disclosed() -> None:
    g = G26EvidenceStrengthRankingGate()
    r = g.check(
        {
            "elo_boost": 12,  # ≤ default cap 15
            "evidence_anchor": {
                "subgroup_match_fraction": 0.3,
                "i_squared": 77.4,
            },
            "narrative": "boost capped — demotion_disclosed in render per G26",
        }
    )
    assert r.status is GateStatus.PASS


def test_g26_blocks_when_no_demotion_marker_even_if_boost_capped() -> None:
    """Capped boost alone isn't enough — must explicitly disclose demotion."""
    g = G26EvidenceStrengthRankingGate()
    r = g.check(
        {
            "elo_boost": 12,
            "evidence_anchor": {
                "subgroup_match_fraction": 0.3,
                "i_squared": 30,
            },
            # no demotion marker / flag
        }
    )
    assert r.status is GateStatus.FAIL
    assert "demotion_disclosed" in r.message.lower()


def test_g26_passes_via_flags_field() -> None:
    g = G26EvidenceStrengthRankingGate()
    r = g.check(
        {
            "elo_boost": 14,
            "evidence_anchor": {
                "subgroup_match_fraction": 0.3,
                "i_squared": 30,
            },
            "flags": ["demotion_disclosed", "patient_l4_thin_subgroup"],
        }
    )
    assert r.status is GateStatus.PASS


def test_g26_custom_thresholds() -> None:
    g = G26EvidenceStrengthRankingGate(max_allowed_boost=10)
    r = g.check(
        {
            "elo_boost": 12,
            "evidence_anchor": {
                "subgroup_match_fraction": 0.3,
                "i_squared": 30,
            },
            "flags": ["demotion_disclosed"],
        }
    )
    assert r.status is GateStatus.FAIL  # 12 > custom cap of 10
    assert "max_allowed_boost=10" in r.message


def test_g25_g26_both_exported() -> None:
    """Sanity check both gates are exported in the registry __all__."""
    from opl_cancer.validators import gates

    assert hasattr(gates, "G25DeferredEvidenceBlockGate")
    assert hasattr(gates, "G26EvidenceStrengthRankingGate")
