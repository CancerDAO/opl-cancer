"""VarSome / ACMG 2015 germline classifier wrapper. v2.2 ADR-0022 — F_BIO.

source_skill: BioTender-max/awesome-bio-agent-skills/bio-acmg-classification
original_license: CC0-1.0

ACMG 2015 (Richards et al. PMID 25741868) defines:

* Very-strong pathogenic: PVS1
* Strong pathogenic:      PS1-PS4
* Moderate pathogenic:    PM1-PM6
* Supporting pathogenic:  PP1-PP5
* Stand-alone benign:     BA1
* Strong benign:          BS1-BS4
* Supporting benign:      BP1-BP7

Decision table (simplified rules per Richards 2015 Table 5):

* Pathogenic if:
  - 1 PVS1 + (≥1 PS OR ≥2 PM OR (1 PM + 1 PP) OR ≥2 PP)
  - ≥2 PS
  - 1 PS + (≥3 PM OR (2 PM + ≥2 PP) OR (1 PM + ≥4 PP))
* Likely Pathogenic if:
  - 1 PVS1 + 1 PM
  - 1 PS + (1-2 PM OR ≥2 PP)
  - ≥3 PM
  - 2 PM + ≥2 PP
  - 1 PM + ≥4 PP
* Benign if:
  - 1 BA1
  - ≥2 BS
* Likely Benign if:
  - 1 BS + 1 BP
  - ≥2 BP
* Conflict (both pathogenic AND benign criteria) → VUS, flag conflict
* Otherwise → VUS

Key format: ``variant:<gene>:<hgvs_c>``
"""
from __future__ import annotations

from typing import Any

from .base import Integrator, IntegratorError
from .cache import IntegratorCache


ACMG_CATEGORIES: list[str] = [
    "Pathogenic",
    "Likely Pathogenic",
    "VUS",
    "Likely Benign",
    "Benign",
]


_VALID_CRITERIA: set[str] = {
    # Pathogenic
    "PVS1",
    "PS1", "PS2", "PS3", "PS4",
    "PM1", "PM2", "PM3", "PM4", "PM5", "PM6",
    "PP1", "PP2", "PP3", "PP4", "PP5",
    # Benign
    "BA1",
    "BS1", "BS2", "BS3", "BS4",
    "BP1", "BP2", "BP3", "BP4", "BP5", "BP6", "BP7",
}


def _bucket(criteria: list[str]) -> dict[str, int]:
    """Tally each criterion into its strength bucket."""
    pvs = sum(1 for c in criteria if c == "PVS1")
    ps = sum(1 for c in criteria if c.startswith("PS") and c != "PVS1")
    pm = sum(1 for c in criteria if c.startswith("PM"))
    pp = sum(1 for c in criteria if c.startswith("PP"))
    ba = sum(1 for c in criteria if c == "BA1")
    bs = sum(1 for c in criteria if c.startswith("BS"))
    bp = sum(1 for c in criteria if c.startswith("BP"))
    return {"PVS": pvs, "PS": ps, "PM": pm, "PP": pp, "BA": ba, "BS": bs, "BP": bp}


def _classify_pathogenic_side(b: dict[str, int]) -> str | None:
    """Return Pathogenic / Likely Pathogenic / None per ACMG 2015 rules."""
    pvs, ps, pm, pp = b["PVS"], b["PS"], b["PM"], b["PP"]
    # Pathogenic rules
    if pvs >= 1 and (ps >= 1 or pm >= 2 or (pm >= 1 and pp >= 1) or pp >= 2):
        return "Pathogenic"
    if ps >= 2:
        return "Pathogenic"
    if ps >= 1 and (pm >= 3 or (pm >= 2 and pp >= 2) or (pm >= 1 and pp >= 4)):
        return "Pathogenic"
    # Likely Pathogenic rules
    if pvs >= 1 and pm >= 1:
        return "Likely Pathogenic"
    if ps >= 1 and (pm >= 1 or pp >= 2):
        return "Likely Pathogenic"
    if pm >= 3:
        return "Likely Pathogenic"
    if pm >= 2 and pp >= 2:
        return "Likely Pathogenic"
    if pm >= 1 and pp >= 4:
        return "Likely Pathogenic"
    return None


def _classify_benign_side(b: dict[str, int]) -> str | None:
    ba, bs, bp = b["BA"], b["BS"], b["BP"]
    if ba >= 1 or bs >= 2:
        return "Benign"
    if (bs >= 1 and bp >= 1) or bp >= 2:
        return "Likely Benign"
    return None


def classify_acmg(*, criteria: list[str]) -> dict[str, Any]:
    """Classify a variant from its matched ACMG criteria.

    Returns: {classification, matched_criteria, conflict_flag, bucket_counts, rationale}.
    """
    for c in criteria:
        if c not in _VALID_CRITERIA:
            raise ValueError(
                f"unknown ACMG criterion {c!r}. Valid: {sorted(_VALID_CRITERIA)}"
            )
    bucket = _bucket(criteria)
    path_cls = _classify_pathogenic_side(bucket)
    ben_cls = _classify_benign_side(bucket)

    # Conflict = any pathogenic criterion AND any benign criterion are
    # present (even if neither side meets its full decision-rule quota).
    # ACMG 2015 rule 5: mixed criteria force VUS + explicit conflict flag.
    has_path_criterion = (bucket["PVS"] + bucket["PS"] + bucket["PM"] + bucket["PP"]) > 0
    has_ben_criterion = (bucket["BA"] + bucket["BS"] + bucket["BP"]) > 0
    conflict = bool(has_path_criterion and has_ben_criterion)

    if path_cls and ben_cls:
        cls = "VUS"
        rationale = (
            f"Conflicting criteria: pathogenic-side rule ({path_cls!r}) AND "
            f"benign-side rule ({ben_cls!r}) both fire → ACMG rule 5 → VUS."
        )
    elif path_cls:
        cls = path_cls
        rationale = f"Pathogenic-side decision rule matched: {path_cls}."
        if conflict:
            rationale += " Benign criteria also present — flag for review."
    elif ben_cls:
        cls = ben_cls
        rationale = f"Benign-side decision rule matched: {ben_cls}."
        if conflict:
            rationale += " Pathogenic criteria also present — flag for review."
    else:
        cls = "VUS"
        if conflict:
            rationale = (
                "Both pathogenic and benign criteria present but neither side "
                "meets its full decision-rule quota → VUS + conflict_flag."
            )
        else:
            rationale = (
                "No pathogenic or benign decision rule satisfied → VUS by default."
            )

    return {
        "classification": cls,
        "matched_criteria": list(criteria),
        "bucket_counts": bucket,
        "conflict_flag": conflict,
        "rationale": rationale,
    }


class AcmgGermlineIntegrator(Integrator):
    """ACMG germline classifier — operates on a criteria list assembled
    upstream (from VarSome / InterVar / per-criterion sub-models).

    family = ``F_BIO``. TTL 90 days.
    """

    family = "F_BIO"
    ttl_seconds = 90 * 24 * 3600

    def __init__(
        self,
        cache: IntegratorCache | None = None,
        *,
        mock_mode: bool = False,
        mock_criteria: list[str] | None = None,
    ) -> None:
        super().__init__(cache=cache)
        self.mock_mode = mock_mode
        self.mock_criteria: list[str] = list(mock_criteria or [])

    async def fetch(self, key: str) -> dict[str, Any]:
        parts = key.split(":")
        if len(parts) != 3 or parts[0] != "variant":
            raise IntegratorError(
                f"ACMG: expected variant:<gene>:<hgvs_c>, got {key!r}"
            )
        gene, variant = parts[1], parts[2]

        if self.mock_mode:
            cls = classify_acmg(criteria=self.mock_criteria)
            return {
                **cls,
                "gene": gene,
                "variant": variant,
                "engine": "acmg-mock",
                "provenance": "mock_mode=True; criteria pre-supplied",
            }

        raise IntegratorError(
            "ACMG: live VarSome / InterVar integration requires API key. "
            "Pass mock_mode=True with criteria for unit tests. No silent fallback."
        )


__all__ = [
    "AcmgGermlineIntegrator",
    "ACMG_CATEGORIES",
    "classify_acmg",
]
