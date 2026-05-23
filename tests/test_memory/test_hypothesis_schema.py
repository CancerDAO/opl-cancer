"""P2-T1+T2: Hypothesis + TournamentRound schemas."""
from __future__ import annotations

import pytest

from opl_cancer.memory.schemas import (
    ClaimLayer,
    Hypothesis,
    TournamentOutcome,
    TournamentRound,
)


def test_hypothesis_minimum_valid() -> None:
    h = Hypothesis(id="hyp_001", text="WNT/β-catenin activation predicts ICI non-response in HCC.")
    assert h.id == "hyp_001"
    assert h.claim_layer == ClaimLayer.SPECULATIVE  # default — founder-mode safety
    assert h.elo_rating == 1200.0
    assert h.status == "active"
    assert h.generation_strategy == "literature_gap"
    assert h.parent_chain == []


def test_hypothesis_full_payload() -> None:
    h = Hypothesis(
        id="hyp_002",
        text="Combine ICI + Wnt-inhibitor in HCC TACE-refractory.",
        claim_layer=ClaimLayer.EXPLORATORY,
        elo_rating=1250.0,
        status="active",
        parent_chain=["hyp_001"],
        generation_strategy="evolution_combination",
        evidence_refs=[{"type": "pmid", "id": "38219045"}],
        meta_critique_inherited=["Prior round flagged confounding by HBV status."],
        rationale="Mechanistic link via β-catenin → T-cell exclusion.",
    )
    assert h.parent_chain == ["hyp_001"]
    assert h.evidence_refs[0]["id"] == "38219045"
    assert h.generation_strategy == "evolution_combination"


def test_hypothesis_status_enum() -> None:
    h = Hypothesis(id="x", text="t", status="falsified")
    assert h.status == "falsified"
    with pytest.raises(Exception):
        Hypothesis(id="x", text="t", status="invalid_status")  # type: ignore[arg-type]


def test_tournament_outcome_validates_winner() -> None:
    o = TournamentOutcome(a="hyp_a", b="hyp_b", winner="A", reason="A's mechanism is stronger.")
    assert o.winner == "A"
    with pytest.raises(Exception):
        TournamentOutcome(a="x", b="y", winner="C")  # type: ignore[arg-type]


def test_tournament_round_minimum() -> None:
    r = TournamentRound(round_id="r1", wave_index=2, participants=["hyp_a", "hyp_b"])
    assert r.round_id == "r1"
    assert r.wave_index == 2
    assert r.outcomes == []
    assert r.meta_critique == ""


def test_tournament_round_full() -> None:
    r = TournamentRound(
        round_id="r1",
        wave_index=2,
        participants=["hyp_a", "hyp_b"],
        pairings=[("hyp_a", "hyp_b")],
        outcomes=[TournamentOutcome(a="hyp_a", b="hyp_b", winner="A", reason="…")],
        elo_deltas=[{"hyp_a": 12.5, "hyp_b": -12.5}],
        meta_critique="Round 1 surfaced confounding by HBV status.",
    )
    assert r.outcomes[0].winner == "A"
    assert r.elo_deltas[0]["hyp_a"] == 12.5
