"""Chemistry mechanical gate for Julius SMILES candidates. v2.0.1 (post-review).

Per medical reviewer finding #2: Julius's persona allows the LLM to self-
report ``lipinski_compliant: true`` and ``pains_clean: true`` — a hallucinated
SMILES with hallucinated flags currently passes schema validation and reaches
the patient brief. This module imposes a mechanical floor.

If RDKit is installed:
  - SMILES parses → valid; else mark invalid
  - Lipinski Ro5 checked mechanically (MW≤500, logP≤5, HBD≤5, HBA≤10)
  - PAINS substructure filter (a basic subset; full PAINS requires the
    catalogue file)

If RDKit is NOT installed:
  - All LLM-self-reported flags are downgraded to ``unverified_no_rdkit``
  - Caller may decide whether to surface the candidate at all

Design choice: this gate is intentionally NOT optional silent-pass — when
RDKit absent we explicitly mark the field rather than trust the LLM. See
``no-silent-fallback policy``.
"""
from __future__ import annotations

from typing import Any


try:
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, Lipinski

    _HAS_RDKIT = True
except ImportError:  # pragma: no cover — depends on env
    _HAS_RDKIT = False


def validate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Mechanically verify a Julius candidate.

    Mutates a copy of ``candidate``: overrides LLM-self-reported flags with
    mechanically-derived ones. Adds ``chemistry_gate`` sub-dict explaining
    what was checked.

    Returns the updated candidate. Does NOT raise — the policy is
    surface-or-suppress, not abort.
    """
    out = dict(candidate)
    smiles = str(out.get("candidate_smiles", "")).strip()

    if not smiles:
        out["chemistry_gate"] = {
            "status": "no_smiles",
            "rdkit_available": _HAS_RDKIT,
            "suppress_from_brief": True,
            "reason": "candidate has no SMILES — Julius output incomplete",
        }
        out["lipinski_compliant"] = None
        out["pains_clean"] = None
        return out

    if not _HAS_RDKIT:
        out["chemistry_gate"] = {
            "status": "unverified_no_rdkit",
            "rdkit_available": False,
            "suppress_from_brief": True,
            "reason": (
                "RDKit not installed in this environment. SMILES is "
                "structurally unverifiable; LLM-self-reported lipinski / "
                "PAINS flags are not trustworthy. Install rdkit to surface."
            ),
        }
        # Downgrade LLM-reported booleans
        out["lipinski_compliant"] = None
        out["pains_clean"] = None
        return out

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        out["chemistry_gate"] = {
            "status": "invalid_smiles",
            "rdkit_available": True,
            "suppress_from_brief": True,
            "reason": "RDKit could not parse SMILES — candidate is malformed.",
        }
        out["lipinski_compliant"] = False
        out["pains_clean"] = None
        return out

    # Mechanical Lipinski check
    mw = Descriptors.MolWt(mol)
    logp = Crippen.MolLogP(mol)
    hbd = Lipinski.NumHDonors(mol)
    hba = Lipinski.NumHAcceptors(mol)
    lipinski_pass = mw <= 500 and logp <= 5 and hbd <= 5 and hba <= 10

    # Basic PAINS subset — pure substructure on a handful of well-known
    # promiscuous patterns. Caller is responsible for the full PAINS run
    # in iter/v2-followup-julius-live (ADR-0016).
    pains_substructs = (
        "[#6]=[#6]-[#6]=[#6]-[#6]=[#6]",  # dienes (toy)
        "[#7H]N=N",  # azo
    )
    pains_hit = any(
        mol.HasSubstructMatch(Chem.MolFromSmarts(s))
        for s in pains_substructs
        if Chem.MolFromSmarts(s) is not None
    )
    pains_clean = not pains_hit

    out["chemistry_gate"] = {
        "status": "verified",
        "rdkit_available": True,
        "suppress_from_brief": False,
        "molecular_weight": round(mw, 2),
        "logp": round(logp, 2),
        "hbd": hbd,
        "hba": hba,
        "lipinski_pass": lipinski_pass,
        "pains_hit_subset": pains_hit,
        "note": (
            "PAINS check uses a basic subset (azo + diene). Full PAINS "
            "catalogue scan deferred to iter/v2-followup-julius-live."
        ),
    }
    out["lipinski_compliant"] = lipinski_pass
    out["pains_clean"] = pains_clean
    return out


def filter_candidates_for_brief(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Verify each candidate; drop ones marked ``suppress_from_brief``.

    Intended call site: between Julius output and renderer context build.
    """
    out: list[dict[str, Any]] = []
    for c in candidates:
        verified = validate_candidate(c)
        if not verified.get("chemistry_gate", {}).get("suppress_from_brief"):
            out.append(verified)
    return out
