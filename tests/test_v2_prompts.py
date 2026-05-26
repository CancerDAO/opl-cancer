"""v2 paradigm tests — prompts must list new strategies + flip empty-integrator rule for [S]-with-testability."""
from __future__ import annotations

from pathlib import Path


HYPGEN = Path("prompts/tasks/hypothesis_generation.md").read_text(encoding="utf-8")
PROACTIVE = Path("prompts/pi/proactive_push.md").read_text(encoding="utf-8")


def test_hypgen_prompt_lists_v2_strategies():
    assert "target_synergy_emergent" in HYPGEN
    assert "undrugged_target_design" in HYPGEN


def test_hypgen_prompt_v2_synthesis_policy_section():
    assert "Synthesis policy (v2.0.0" in HYPGEN
    # Accept backtick-wrapped `[S]` or bare [S]
    assert "[S]` is a feature, not a defect" in HYPGEN or "[S] is a feature, not a defect" in HYPGEN


def test_hypgen_prompt_requires_testability_path_field():
    assert '"testability_path"' in HYPGEN
    # Mandatory wording
    assert "MANDATORY for strategies 5 + 6" in HYPGEN


def test_hypgen_prompt_lifts_synthesis_ban_for_v2_strategies():
    # The phrase "is LIFTED for v2 strategies 5 + 6" anchors the rule flip.
    assert "LIFTED for v2 strategies 5 + 6" in HYPGEN


def test_proactive_push_allows_speculative_with_testability():
    # v2: speculative ALLOWED when testability_path present + surface section dedicated
    # v1 hard ban "Never push speculative claims proactively" must be marked deprecated
    assert "v1 deprecated" in PROACTIVE.lower() or "speculative claims ARE allowed" in PROACTIVE
    assert "world_unknown_candidates" in PROACTIVE


def test_proactive_push_references_testability_path():
    assert "testability_path" in PROACTIVE
