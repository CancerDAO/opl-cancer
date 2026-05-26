"""InvariantGate tests — verify safety-surface flagging on realistic patches."""
from __future__ import annotations

from opl_cancer.evolution.invariant_gate import analyze, apply_gate
from opl_cancer.evolution.models import EvolutionProposal


def test_safe_prompt_patch_no_invariant_hits():
    p = EvolutionProposal(
        proposal_id="p001",
        kind="prompt_patch",
        summary="extend Aviv's pathway list to include WikiPathways",
        rationale="r",
        proposed_diff="""--- a/prompts/experts/aviv/persona.md
+++ b/prompts/experts/aviv/persona.md
@@ -10,3 +10,4 @@
 pathway sources: KEGG, Reactome
+pathway sources: KEGG, Reactome, WikiPathways
""",
        target_path="prompts/experts/aviv/persona.md",
    )
    impact = analyze(p)
    assert impact.any_safety_hit() is False


def test_henry_safety_patch_flagged():
    p = EvolutionProposal(
        proposal_id="p002",
        kind="prompt_patch",
        summary="soften Henry L3 acknowledgment requirement",
        rationale="r",
        proposed_diff="""--- a/src/opl_cancer/validators/henry.py
+++ b/src/opl_cancer/validators/henry.py
-    if requires_patient_acknowledgment(level):
+    if False and requires_patient_acknowledgment(level):
""",
        target_path="src/opl_cancer/validators/henry.py",
    )
    impact = analyze(p)
    assert impact.touches_henry_l3_l4 is True


def test_persona_prefix_patch_flagged_via_path():
    p = EvolutionProposal(
        proposal_id="p003",
        kind="prompt_patch",
        summary="tweak G7 imperative-free language",
        rationale="r",
        proposed_diff="(some content)",
        target_path="prompts/experts/_shared/persona_prefix.md",
    )
    impact = analyze(p)
    assert impact.touches_persona_prefix is True


def test_claim_layer_patch_flagged():
    p = EvolutionProposal(
        proposal_id="p004",
        kind="prompt_patch",
        summary="relax three-tier requirement",
        rationale="r",
        proposed_diff="remove claim_layer enforcement",
        target_path="src/opl_cancer/orchestrator/generation.py",
    )
    impact = analyze(p)
    assert impact.touches_claim_layer_enforcement is True


def test_apply_gate_sets_double_signoff_on_safety_hit():
    p = EvolutionProposal(
        proposal_id="p005",
        kind="prompt_patch",
        summary="soften Henry behavior",
        rationale="r",
        proposed_diff="modify Henry verdict logic",
        target_path="src/opl_cancer/validators/henry.py",
    )
    p = apply_gate(p)
    assert p.requires_double_signoff is True
    assert "sid" in p.required_signoffs
    assert "henry" in p.required_signoffs


def test_apply_gate_blocks_skill_without_clinical_anchor():
    p = EvolutionProposal(
        proposal_id="p006",
        kind="skill_addition",
        summary="aggressive resistance mutation skill",
        rationale="r",
        clinical_anchor="",
    )
    p = apply_gate(p)
    assert p.status == "blocked"
    assert any("clinical_anchor" in r for r in p.rejected_by)


def test_apply_gate_passes_skill_with_clinical_anchor():
    p = EvolutionProposal(
        proposal_id="p007",
        kind="skill_addition",
        summary="cite-CSCO skill",
        rationale="r",
        clinical_anchor="CSCO CRC 2025 §3.2.1",
    )
    p = apply_gate(p)
    assert p.status == "pending"


def test_apply_gate_proactive_push_path_flagged_as_claim_layer():
    """v2.0.0: proactive_push.md is now a safety surface — modifying it
    would silently flip the [S]-push policy. Gate must require double signoff."""
    p = EvolutionProposal(
        proposal_id="p008",
        kind="prompt_patch",
        summary="re-ban speculative pushes",
        rationale="r",
        proposed_diff="revert v2.0.0 speculative-push policy",
        target_path="prompts/pi/proactive_push.md",
    )
    p = apply_gate(p)
    assert p.requires_double_signoff is True


def test_apply_gate_proactive_push_now_also_flags_henry():
    """v2.0.1 (post-review medical reviewer #7): proactive_push patches ARE
    Henry-adjacent. Push policy weakening must require Henry signoff, not
    just generic double-signoff."""
    p = EvolutionProposal(
        proposal_id="p009",
        kind="prompt_patch",
        summary="remove testability_path requirement",
        rationale="r",
        proposed_diff="drop testability_path mandate from rule 2",
        target_path="prompts/pi/proactive_push.md",
    )
    p = apply_gate(p)
    assert p.invariant_impact.touches_henry_l3_l4 is True
    assert "henry" in p.required_signoffs
