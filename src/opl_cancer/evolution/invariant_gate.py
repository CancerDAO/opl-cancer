"""InvariantGate — static analysis of proposed patches. ADR-0020 §What we add #10.

Flags proposals that touch OPL safety surfaces (Henry L3/L4, G7 imperative-
free voice, G13 reviewer split, persona prefix, claim_layer enforcement,
Retraction DB logic).

Hits → ``requires_double_signoff = True`` automatically; Sid alone cannot
approve. This is the medical-domain backstop against EvoMaster's blind
``_write_prompt_overlays`` pattern.
"""
from __future__ import annotations

import re

from .models import EvolutionProposal, InvariantImpact


# Static regex set — intentionally over-flag rather than under-flag.
_HENRY_L3_L4 = re.compile(
    r"\b(requires_acknowledgment|requires_double_signoff|risk_disclosure|L3_HIGH_RISK|L4_BOUNDARY|Henry|requires_patient_ack)\b",
    re.IGNORECASE,
)
_G7_IMPERATIVE = re.compile(
    r"\b(imperative.?free|imperative.?voice|G7|should not\s+(say|recommend)|patient should|directive)\b",
    re.IGNORECASE,
)
_G13_REVIEWER = re.compile(
    r"\b(reviewer.?model|G13|reviewer_pool|executor_model.*?reviewer|cross.?model)\b",
    re.IGNORECASE,
)
_PERSONA_PREFIX = re.compile(
    r"(persona_prefix|_shared/persona|patient-?anchor|canonical persona|G7 voice)",
    re.IGNORECASE,
)
_CLAIM_LAYER = re.compile(
    r"\b(claim_layer|ClaimLayer|three.?tier|established/exploratory/speculative|\[E\]/\[X\]/\[S\])\b",
    re.IGNORECASE,
)
_RETRACTION = re.compile(
    r"\b(retraction|RetractionDB|retracted|withdrawn paper)\b",
    re.IGNORECASE,
)

# Paths considered safety-critical regardless of patch content
_SAFETY_PATHS = (
    "validators/henry.py",
    "validators/gates/g7",
    "validators/gates/g13",
    "validators/permission_levels.py",
    "prompts/experts/_shared/persona_prefix.md",
    "prompts/auditor/",
    "prompts/pi/proactive_push.md",  # v2.0.0 — speculative-push policy lives here
    "integrators/retractiondb.py",
)


def analyze(proposal: EvolutionProposal) -> InvariantImpact:
    """Compute the InvariantImpact for a proposal.

    Inspects both ``proposed_diff`` content and ``target_path`` location.
    """
    impact = InvariantImpact()
    blob = (proposal.proposed_diff or "") + "\n" + (proposal.target_path or "")

    if _HENRY_L3_L4.search(blob):
        impact.touches_henry_l3_l4 = True
    if _G7_IMPERATIVE.search(blob):
        impact.touches_g7_imperative_voice = True
    if _G13_REVIEWER.search(blob):
        impact.touches_g13_reviewer_split = True
    if _PERSONA_PREFIX.search(blob):
        impact.touches_persona_prefix = True
    if _CLAIM_LAYER.search(blob):
        impact.touches_claim_layer_enforcement = True
    if _RETRACTION.search(blob):
        impact.touches_retraction_db_logic = True

    # Path-based check — if target_path is in safety surfaces, mark all-true conservatively
    path = (proposal.target_path or "").lower()
    for safety_path in _SAFETY_PATHS:
        if safety_path in path:
            impact.extra_flags.append(f"target_path_in_safety_surface:{safety_path}")
            # Don't blanket-flag, but mark persona_prefix specifically since that
            # is the most common safety-path landing
            if "persona_prefix" in safety_path:
                impact.touches_persona_prefix = True
            if "henry" in safety_path or "permission_levels" in safety_path or "auditor" in safety_path:
                impact.touches_henry_l3_l4 = True
            if "retractiondb" in safety_path:
                impact.touches_retraction_db_logic = True
            if "proactive_push" in safety_path:
                impact.touches_claim_layer_enforcement = True

    return impact


def apply_gate(proposal: EvolutionProposal) -> EvolutionProposal:
    """Run analyze() + set requires_double_signoff + auto-block skill proposals
    missing clinical_anchor.

    Returns the same proposal (mutated). Status may transition:
        pending → blocked if auto-reject conditions met
    """
    proposal.invariant_impact = analyze(proposal)
    if proposal.invariant_impact.any_safety_hit():
        proposal.requires_double_signoff = True
        # default required signoffs when safety hit
        if not proposal.required_signoffs:
            proposal.required_signoffs = ["sid", "henry"]
    if proposal.is_auto_rejected():
        proposal.status = "blocked"
        proposal.rejected_by = proposal.rejected_by + ["invariant_gate:missing_clinical_anchor"]
    return proposal
