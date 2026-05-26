"""v2 paradigm tests — extended generation strategies + Hypothesis acceptance."""
from __future__ import annotations

from typing import get_args

from opl_cancer.memory.schemas import ClaimLayer, GenerationStrategy, Hypothesis
from opl_cancer.orchestrator.generation import STRATEGIES, _STRATEGY_GUIDANCE


def test_generation_strategy_includes_v2_strategies():
    strategies = get_args(GenerationStrategy)
    assert "target_synergy_emergent" in strategies
    assert "undrugged_target_design" in strategies


def test_hypothesis_accepts_v2_strategy():
    h = Hypothesis(
        id="hyp_test_001",
        text="dummy",
        claim_layer=ClaimLayer.SPECULATIVE,
        rationale="dummy",
        generation_strategy="target_synergy_emergent",
        evidence_refs=[],
    )
    assert h.generation_strategy == "target_synergy_emergent"


def test_strategies_tuple_extended_to_six():
    assert len(STRATEGIES) == 6
    assert "target_synergy_emergent" in STRATEGIES
    assert "undrugged_target_design" in STRATEGIES
    assert "target_synergy_emergent" in _STRATEGY_GUIDANCE
    assert "undrugged_target_design" in _STRATEGY_GUIDANCE


def test_v2_strategy_guidance_mentions_kg_or_undrugged():
    syn_guidance = _STRATEGY_GUIDANCE["target_synergy_emergent"]
    assert "synergy" in syn_guidance.lower()
    assert "kg" in syn_guidance.lower() or "primekg" in syn_guidance.lower() or "knowledge" in syn_guidance.lower() or "open targets" in syn_guidance.lower()

    drug_guidance = _STRATEGY_GUIDANCE["undrugged_target_design"]
    assert "undrugged" in drug_guidance.lower() or "no fda" in drug_guidance.lower()
    assert "diffdock" in drug_guidance.lower() or "esmfold" in drug_guidance.lower() or "vina" in drug_guidance.lower()
