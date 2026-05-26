"""Chemistry gate tests — verify mechanical override of LLM-self-reported flags."""
from __future__ import annotations

from opl_cancer.validators.chemistry_gate import (
    _HAS_RDKIT,
    filter_candidates_for_brief,
    validate_candidate,
)


def test_empty_smiles_suppressed():
    out = validate_candidate({"candidate_smiles": "", "lipinski_compliant": True, "pains_clean": True})
    assert out["chemistry_gate"]["suppress_from_brief"] is True
    assert out["lipinski_compliant"] is None
    assert out["pains_clean"] is None


def test_missing_smiles_key_suppressed():
    out = validate_candidate({"lipinski_compliant": True, "pains_clean": True})
    assert out["chemistry_gate"]["suppress_from_brief"] is True


def test_llm_self_report_overridden_when_rdkit_absent():
    """The whole point of the gate — if no RDKit, LLM flags get downgraded."""
    out = validate_candidate({
        "candidate_smiles": "CCO",  # ethanol — would pass Lipinski
        "lipinski_compliant": True,
        "pains_clean": True,
    })
    if not _HAS_RDKIT:
        assert out["chemistry_gate"]["status"] == "unverified_no_rdkit"
        assert out["lipinski_compliant"] is None
        assert out["pains_clean"] is None
        assert out["chemistry_gate"]["suppress_from_brief"] is True
    else:
        # When RDKit IS installed, ethanol should mechanically pass Lipinski
        assert out["lipinski_compliant"] is True


def test_invalid_smiles_marked_invalid():
    if not _HAS_RDKIT:
        return  # skip — depends on RDKit
    out = validate_candidate({
        "candidate_smiles": "ZZ-not-smiles",
        "lipinski_compliant": True,
        "pains_clean": True,
    })
    assert out["chemistry_gate"]["status"] == "invalid_smiles"
    assert out["lipinski_compliant"] is False


def test_filter_drops_suppressed():
    candidates = [
        {"candidate_smiles": "", "lipinski_compliant": True},
        {"candidate_smiles": "CCO", "lipinski_compliant": True},
    ]
    out = filter_candidates_for_brief(candidates)
    if not _HAS_RDKIT:
        # Both get suppressed (one empty, one unverified)
        assert len(out) == 0
    else:
        # CCO (ethanol) passes
        assert len(out) == 1


def test_no_silent_pass_policy():
    """Per memory:feedback_no_offline_only — gate must NEVER silently
    accept LLM-reported flags. Either RDKit verifies, or flags are nulled."""
    candidate = {
        "candidate_smiles": "CCO",
        "lipinski_compliant": True,  # LLM claim
        "pains_clean": True,  # LLM claim
    }
    out = validate_candidate(candidate)
    if _HAS_RDKIT:
        # Flag must be re-derived mechanically — value may match LLM by
        # coincidence but it's now mechanically verified
        assert out["chemistry_gate"]["status"] == "verified"
    else:
        # Without RDKit, LLM flag is destroyed (set to None), not preserved
        assert out["lipinski_compliant"] is None
        assert out["pains_clean"] is None
