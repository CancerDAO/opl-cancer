"""G42: tier_discipline — enforce evidence-tier honesty + functional-evidence floor.

v2.7.0 (ADR-0026 P1/P2, session 0d1017d4 KRAS-G12C/MSS-mCRC findings 3, 4, 7).

The driving incident (cross-model review):

* Finding 3/7 (CRITICAL/MAJOR): the most aggressive novelty — an ATM-gated
  ATRi/PARPi proposal — rode the *weakest* evidence (mechanistic/preclinical,
  breast-cancer-derived) while sitting **adjacent to the FDA-approved headline**,
  so a reader could mistake speculative for established. Evidence tiers were
  conflated: an "established" claim was floated on exploratory/speculative links.
* Finding 4 (MAJOR): "TP53 biallelic loss" was asserted from IHC / expression
  data, not functional (sequencing/zygosity) data — a loss-of-function call
  the underlying modality cannot support, and from the wrong tumour type.

G42 closes that hole. It is a **no-LLM, mechanical** gate. The LLM (via prompt)
makes the clinical call and records it in three structured places on the claim
(``schemas/claim.v2.schema.json``):

  * ``claim.tier``                     — the claim's own overall three-tier label
  * ``claim.evidence[].tier``          — per-link evidence strength
  * ``claim.regimen.is_headline``      — whether this is a headline regimen
  * ``claim.functional_evidence``      — {claim_type, same_tumor_type, modality}
                                         for a loss-of-function / biallelic call

G42 enforces three sub-rules, each of which SKIPs (cannot judge) when its field
is absent, so a field being optional means "gate cannot judge", not "safe":

  (a) TIER-FLOOR  [BLOCK]
      Tier rank: established=3 > exploratory=2 > speculative=1. The claim's own
      ``tier`` rank must be <= min(rank of each ``evidence[].tier``). i.e. you
      cannot launder exploratory/speculative evidence into an established
      headline. An ``established`` claim with a ``speculative`` evidence link
      FAILs and BLOCKs.

  (b) FUNCTIONAL-EVIDENCE  [BLOCK]
      If the claim asserts a biallelic / loss-of-function state
      (``functional_evidence.claim_type`` in {biallelic, loss_of_function}) it
      MUST be backed by same-tumour-type data (``same_tumor_type == True``) AND a
      modality that can actually establish loss of function — i.e.
      ``modality`` NOT in {IHC, expression_only}. Otherwise FAIL + BLOCK. This
      catches both "biallelic from IHC/expression" and "ATM functional data is
      breast-cancer-derived".

  (c) ADJACENCY  [WARN, block=False]
      A ``speculative`` claim presented as headline-adjacent
      (``tier == speculative`` AND ``regimen.is_headline``) is a presentation
      risk — the aggressive novelty sitting next to the approved headline. WARN
      (recorded in attestation; does not fail delivery) per Fork A: SAFETY gates
      hard-block, QUALITY/presentation gates warn.

This is a QUALITY gate; sub-rules (a) and (b) are the safety-floor invariants
that BLOCK, (c) is the presentation WARN.
"""
from __future__ import annotations

from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

# ── three-tier rank ─────────────────────────────────────────────────────────
# established=3 (strongest) > exploratory=2 > speculative=1. Higher rank = the
# claim is asserting MORE certainty, so the claim's rank must not EXCEED the
# weakest (lowest-rank) evidence link.
_TIER_RANK: dict[str, int] = {
    "established": 3,
    "exploratory": 2,
    "speculative": 1,
}

# functional-evidence claim_type values that assert loss-of-function / biallelic
# inactivation — these are the calls that REQUIRE functional (not IHC/expression)
# data from the same tumour type.
_LOF_CLAIM_TYPES = {"biallelic", "loss_of_function"}

# modalities that CANNOT establish loss-of-function / biallelic state. IHC and
# bare expression read-outs are surrogate / protein-level — they do not prove
# biallelic genomic inactivation. (This is established assay-interpretation
# reference, not an LLM clinical judgment.)
_INSUFFICIENT_LOF_MODALITIES = {"ihc", "expression_only"}


def _norm(value: Any) -> str:
    return str(value).strip().lower() if value is not None else ""


class G42TierDisciplineGate(Gate):
    """Evidence-tier honesty: tier-floor, functional-evidence, headline adjacency."""

    name = "G42_tier_discipline"
    description = (
        "Enforces evidence-tier discipline on a structured claim: (a) a claim's "
        "own tier cannot exceed the weakest tier in its evidence links "
        "(no laundering exploratory evidence into an established headline) — "
        "BLOCK; (b) a biallelic / loss-of-function assertion must rest on "
        "same-tumour-type functional data, never IHC / expression-only — BLOCK; "
        "(c) a speculative claim presented adjacent to the headline is flagged — "
        "WARN. Catches the KRAS-G12C/MSS findings 3/4/7 (ATM-gated ATRi/PARPi "
        "novelty on the weakest evidence next to the approved headline; "
        "'TP53 biallelic loss' from IHC)."
    )
    failure_mode_code = "Q42-TIER-CONFLATION"
    family_id = "reasoning-quality"

    def check(self, claim: dict[str, Any]) -> GateResult:
        sub_results: list[dict[str, Any]] = []
        blocking: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []

        any_judged = False

        # ── (a) TIER-FLOOR ──────────────────────────────────────────────────
        claim_tier = _norm(claim.get("tier"))
        evidence = claim.get("evidence")
        if claim_tier in _TIER_RANK and isinstance(evidence, list):
            link_tiers = [
                _norm(link.get("tier"))
                for link in evidence
                if isinstance(link, dict) and _norm(link.get("tier")) in _TIER_RANK
            ]
            if link_tiers:
                any_judged = True
                claim_rank = _TIER_RANK[claim_tier]
                weakest_tier = min(link_tiers, key=lambda t: _TIER_RANK[t])
                weakest_rank = _TIER_RANK[weakest_tier]
                if claim_rank > weakest_rank:
                    blocking.append({
                        "rule": "tier_floor",
                        "claim_tier": claim_tier,
                        "weakest_evidence_tier": weakest_tier,
                        "evidence_tiers": link_tiers,
                        "reason": (
                            f"claim.tier '{claim_tier}' (rank {claim_rank}) exceeds the "
                            f"weakest evidence tier '{weakest_tier}' (rank {weakest_rank}); "
                            "an established/exploratory claim cannot be floated on a weaker "
                            "evidence link (tier laundering)."
                        ),
                    })
                else:
                    sub_results.append({"rule": "tier_floor", "status": "pass",
                                        "claim_tier": claim_tier, "weakest_evidence_tier": weakest_tier})

        # ── (b) FUNCTIONAL-EVIDENCE ─────────────────────────────────────────
        fe = claim.get("functional_evidence")
        if isinstance(fe, dict):
            claim_type = _norm(fe.get("claim_type"))
            if claim_type in _LOF_CLAIM_TYPES:
                any_judged = True
                same_tumor = fe.get("same_tumor_type")
                modality = _norm(fe.get("modality"))
                problems: list[str] = []
                if same_tumor is not True:
                    problems.append(
                        f"same_tumor_type is {same_tumor!r}, not True "
                        "(functional data must be from the patient's tumour type, "
                        "not a different lineage)"
                    )
                if modality in _INSUFFICIENT_LOF_MODALITIES:
                    problems.append(
                        f"modality '{modality}' cannot establish "
                        f"{claim_type} (IHC / expression-only is a surrogate, "
                        "not functional / genomic zygosity evidence)"
                    )
                if problems:
                    blocking.append({
                        "rule": "functional_evidence",
                        "claim_type": claim_type,
                        "same_tumor_type": same_tumor,
                        "modality": modality or None,
                        "reason": "; ".join(problems),
                    })
                else:
                    sub_results.append({"rule": "functional_evidence", "status": "pass",
                                        "claim_type": claim_type, "modality": modality or None})

        # ── (c) ADJACENCY (WARN) ────────────────────────────────────────────
        regimen = claim.get("regimen")
        if claim_tier in _TIER_RANK and isinstance(regimen, dict):
            is_headline = regimen.get("is_headline")
            if isinstance(is_headline, bool):
                any_judged = True
                if claim_tier == "speculative" and is_headline:
                    warnings.append({
                        "rule": "adjacency",
                        "claim_tier": claim_tier,
                        "is_headline": True,
                        "reason": (
                            "a speculative claim is presented as headline-adjacent "
                            "(regimen.is_headline=True); a reader may mistake the most "
                            "aggressive novelty for an established option."
                        ),
                    })
                else:
                    sub_results.append({"rule": "adjacency", "status": "pass",
                                        "claim_tier": claim_tier, "is_headline": is_headline})

        # ── verdict ─────────────────────────────────────────────────────────
        if not any_judged:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=(
                    "G42 SKIP — no tier / evidence-tier / functional_evidence / "
                    "regimen.is_headline fields present to judge."
                ),
                evidence={"claim_id": claim.get("claim_id")},
            )

        if blocking:
            sample = "; ".join(f"[{v['rule']}] {v['reason']}" for v in blocking)
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G42 FAIL — {len(blocking)} tier-discipline violation(s). {sample}"
                ),
                evidence={
                    "claim_id": claim.get("claim_id"),
                    "blocking_violations": blocking,
                    "warnings": warnings,
                    "passed_subrules": sub_results,
                },
            )

        if warnings:
            sample = "; ".join(f"[{w['rule']}] {w['reason']}" for w in warnings)
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=False,  # WARN — Fork A: presentation/quality gate does not block
                message=(
                    f"G42 WARN — {len(warnings)} headline-adjacency presentation "
                    f"concern(s) (non-blocking). {sample}"
                ),
                evidence={
                    "claim_id": claim.get("claim_id"),
                    "warnings": warnings,
                    "passed_subrules": sub_results,
                },
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                f"G42 OK — {len(sub_results)} tier-discipline sub-rule(s) passed "
                "(tier-floor / functional-evidence / adjacency)."
            ),
            evidence={"claim_id": claim.get("claim_id"), "passed_subrules": sub_results},
        )
