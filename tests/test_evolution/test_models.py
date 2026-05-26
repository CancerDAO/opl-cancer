"""Evolution Pydantic schema tests."""
from __future__ import annotations

import pytest

from opl_cancer.evolution.models import (
    EvolutionCandidates,
    EvolutionProposal,
    HypothesisStrategyCount,
    InvariantImpact,
    TraceDigest,
    WaveSummary,
)


def test_trace_digest_defaults_marked_scrubbed():
    d = TraceDigest(run_id="run-x")
    assert d.is_scrubbed() is True
    assert d.patient_code_scrubbed.startswith("[SCRUB")


def test_trace_digest_wave_summary_validates_range():
    with pytest.raises(Exception):
        WaveSummary(wave=0)
    with pytest.raises(Exception):
        WaveSummary(wave=6)
    w = WaveSummary(wave=3, tasks_completed=2)
    assert w.wave == 3


def test_hypothesis_strategy_count_tracks_speculative_with_testability():
    h = HypothesisStrategyCount(
        strategy="target_synergy_emergent",
        count=2,
        speculative_with_testability=2,
    )
    assert h.count == 2
    assert h.speculative_with_testability == 2


def test_invariant_impact_any_safety_hit_false_by_default():
    i = InvariantImpact()
    assert i.any_safety_hit() is False


def test_invariant_impact_any_safety_hit_true_when_henry_touched():
    i = InvariantImpact(touches_henry_l3_l4=True)
    assert i.any_safety_hit() is True


def test_invariant_impact_any_safety_hit_true_when_persona_prefix_touched():
    i = InvariantImpact(touches_persona_prefix=True)
    assert i.any_safety_hit() is True


def test_evolution_proposal_default_status_pending():
    p = EvolutionProposal(
        proposal_id="p001",
        kind="prompt_patch",
        summary="test",
        rationale="r",
    )
    assert p.status == "pending"
    assert p.requires_double_signoff is False
    assert p.regression_gate_status == "not_yet_implemented"


def test_skill_proposal_without_clinical_anchor_is_auto_rejected():
    p = EvolutionProposal(
        proposal_id="p002",
        kind="skill_addition",
        summary="add skill",
        rationale="r",
        clinical_anchor="",
    )
    assert p.is_auto_rejected() is True


def test_skill_proposal_with_clinical_anchor_not_auto_rejected():
    p = EvolutionProposal(
        proposal_id="p003",
        kind="skill_addition",
        summary="add skill",
        rationale="r",
        clinical_anchor="NCCN-CRC v3.2025 §SYS-A",
    )
    assert p.is_auto_rejected() is False


def test_prompt_patch_proposal_does_not_require_clinical_anchor():
    p = EvolutionProposal(
        proposal_id="p004",
        kind="prompt_patch",
        summary="tweak prompt",
        rationale="r",
        clinical_anchor="",
    )
    assert p.is_auto_rejected() is False


def test_evolution_candidates_default_no_proposals():
    c = EvolutionCandidates(iter_n=1)
    assert c.proposals == []
    assert c.used_heuristic_fallback is False
