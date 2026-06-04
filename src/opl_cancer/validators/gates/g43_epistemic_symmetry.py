"""G43: epistemic_symmetry — catch motivated reasoning (asymmetric skepticism +
flattened cross-agent pooling).

v2.7.0 (ADR-0026 P1/P2 reasoning-quality layer, session 0d1017d4 KRAS-G12C/
MSS-mCRC cross-model review). Two findings drive this gate:

* Finding 2 (CRITICAL) — **asymmetric skepticism / motivated reasoning**: the
  brief *trusted* a favourable cohort (n=981) while *dismissing* a contradicting
  signal (n=30) as "small sample" — applying a methodological bar to inconvenient
  evidence that it did NOT apply to the evidence it relied on. Dataset-selection
  and OS-from-sequencing bias in the relied-upon source went unmentioned.
* Finding 8 (MINOR) — **flattened pooling**: a pooled HR 0.68 with I²=0% was
  presented as a clean signal across agents that are not clinically equivalent;
  the low statistical I² hid clinical heterogeneity that was never flagged.

CONTRACT (no-hardcoded-keyword-list policy): the LLM (via the
claim_audit prompt) makes the clinical/epistemic call — which refs it dismissed
vs. relied on, on what ground, and whether the same bar was applied symmetrically.
G43 is **MECHANICAL**: it only checks that the producer SELF-RECORDED its
skepticism in the structured fields and that those self-declarations are
internally coherent. It never re-judges the clinical content, never owns a
keyword list of "weak evidence" terms.

Block policy (Fork A — founder decision): **WARN (block=False)**. This is a
QUALITY gate, not a SAFETY gate. A violation is recorded in the attestation and
surfaced to the reader but does NOT fail delivery.

Structured fields read (schemas/claim.v2.schema.json):

    claim.skepticism = {
        "dismissed": [{"ref": str, "ground": str}, ...],
        "relied":    [{"ref": str}, ...],
        "symmetric": bool,
        "rationale": str,
    }
    claim.pooled_estimate = {
        "agents": [str, ...],            # ≥2 distinct ⇒ pooling occurred
        "i2": float,                     # 0.0-1.0 OR 0-100 (we normalise)
        "heterogeneity_flagged": bool,
    }

Logic:
  (a) skepticism present and symmetric is explicitly False with no (non-empty)
      rationale ⇒ FAIL (warn): a self-declared asymmetry with no explanation.
  (b) dismissed non-empty AND relied non-empty AND symmetric NOT explicitly True
      ⇒ FAIL (warn) "asymmetric skepticism not reconciled": the producer set
      evidence aside while relying on other evidence but never affirmed it held
      both to the same bar (and gave no rationale for an asymmetry). Also flags
      any dismissed ref that carries no `ground`.
  (c) pooled_estimate with >1 DISTINCT agent AND normalised I² < 25 AND
      heterogeneity_flagged is not True ⇒ FAIL (warn) "low-I² pooled estimate
      across non-equivalent agents must flag clinical heterogeneity".
  SKIP (block=False) when neither skepticism nor pooled_estimate is present —
      the field being absent means 'gate cannot judge', not 'safe'.
"""
from __future__ import annotations

from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

# I² low-heterogeneity ceiling. The schema lets the producer write I² on either
# the 0.0-1.0 or the 0-100 scale; we normalise to 0-100 before comparing. "Low"
# per the finding (I²=0%) and the spec is < 25.
_I2_LOW_CEILING = 25.0


def _normalise_i2(raw: Any) -> float | None:
    """Normalise an I² value to the 0-100 scale. Returns None if not numeric.

    Accepts 0.0-1.0 (fraction) or 0-100 (percent). Values in [0, 1] are treated
    as a fraction and scaled ×100; values > 1 are treated as already-percent.
    """
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    val = float(raw)
    if val < 0:
        return None
    if val <= 1.0:
        return val * 100.0
    return val


def _nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and v.strip() != ""


class G43EpistemicSymmetryGate(Gate):
    """The producer's self-recorded skepticism must be symmetric + coherent, and
    a low-I² cross-agent pooled estimate must flag clinical heterogeneity."""

    name = "G43_epistemic_symmetry"
    description = (
        "Mechanical check that the producer self-recorded SYMMETRIC skepticism "
        "(it did not dismiss inconvenient evidence on a ground it tolerated for "
        "relied-upon evidence) and that a pooled estimate across >1 non-equivalent "
        "agent with low statistical I² explicitly flags clinical heterogeneity. "
        "Catches the KRAS-G12C/MSS motivated-reasoning + flattened-pooling "
        "findings. WARN-only quality gate (does not block delivery)."
    )
    failure_mode_code = "Q3-ASYMMETRIC-SKEPTICISM"
    family_id = "reasoning-quality"

    def check(self, claim: dict[str, Any]) -> GateResult:
        skepticism = claim.get("skepticism")
        pooled = claim.get("pooled_estimate")

        has_skepticism = isinstance(skepticism, dict)
        has_pooled = isinstance(pooled, dict)

        if not has_skepticism and not has_pooled:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=(
                    "G43 SKIP — neither claim.skepticism nor claim.pooled_estimate "
                    "present; cannot judge epistemic symmetry."
                ),
            )

        violations: list[dict[str, Any]] = []

        # ── skepticism symmetry ────────────────────────────────────────────
        if isinstance(skepticism, dict):
            dismissed = skepticism.get("dismissed") or []
            relied = skepticism.get("relied") or []
            symmetric = skepticism.get("symmetric")
            rationale = skepticism.get("rationale")
            symmetric_true = symmetric is True
            has_rationale = _nonempty_str(rationale)

            dismissed = dismissed if isinstance(dismissed, list) else []
            relied = relied if isinstance(relied, list) else []

            # Every dismissed ref must carry a (non-empty) ground — a dismissal
            # with no methodological ground is exactly the motivated-reasoning
            # smell the finding describes.
            for entry in dismissed:
                if not isinstance(entry, dict):
                    continue
                if not _nonempty_str(entry.get("ground")):
                    violations.append({
                        "kind": "dismissed_without_ground",
                        "ref": entry.get("ref"),
                        "detail": (
                            "evidence dismissed with no methodological ground; "
                            "a ground is required to justify down-weighting."
                        ),
                    })

            # (a) explicit asymmetry with no rationale.
            if symmetric is False and not has_rationale:
                violations.append({
                    "kind": "asymmetric_no_rationale",
                    "detail": (
                        "skepticism.symmetric is explicitly false but no rationale "
                        "was given to justify applying a different bar to dismissed "
                        "vs. relied-upon evidence."
                    ),
                })

            # (b) dismissed AND relied present, symmetry not explicitly affirmed.
            if dismissed and relied and not symmetric_true:
                violations.append({
                    "kind": "asymmetry_not_reconciled",
                    "n_dismissed": len(dismissed),
                    "n_relied": len(relied),
                    "symmetric": symmetric,
                    "detail": (
                        "asymmetric skepticism not reconciled: the producer set "
                        f"{len(dismissed)} source(s) aside while relying on "
                        f"{len(relied)} other(s) but did not set symmetric=true "
                        "(nor give a rationale for the asymmetry). The same "
                        "methodological bar must apply to dismissed and relied-"
                        "upon evidence, or the asymmetry must be explained."
                    ),
                })

        # ── pooled-estimate clinical-heterogeneity flag ────────────────────
        if isinstance(pooled, dict):
            agents = pooled.get("agents") or []
            agents = agents if isinstance(agents, list) else []
            distinct_agents = {str(a).strip() for a in agents if _nonempty_str(a) or a is not None}
            distinct_agents = {a for a in distinct_agents if a != ""}
            i2_norm = _normalise_i2(pooled.get("i2"))
            heterogeneity_flagged = pooled.get("heterogeneity_flagged") is True

            if (
                len(distinct_agents) > 1
                and i2_norm is not None
                and i2_norm < _I2_LOW_CEILING
                and not heterogeneity_flagged
            ):
                violations.append({
                    "kind": "flattened_pooling",
                    "n_distinct_agents": len(distinct_agents),
                    "i2_normalised_pct": i2_norm,
                    "heterogeneity_flagged": pooled.get("heterogeneity_flagged"),
                    "detail": (
                        "low-I² pooled estimate across non-equivalent agents must "
                        f"flag clinical heterogeneity: I²={i2_norm:.0f}% pooled "
                        f"over {len(distinct_agents)} distinct agents but "
                        "heterogeneity_flagged is not true. A low statistical I² "
                        "does not mean the agents are clinically equivalent."
                    ),
                })

        if violations:
            kinds = sorted({v["kind"] for v in violations})
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=False,  # WARN-only quality gate (Fork A).
                message=(
                    f"G43 WARN — {len(violations)} epistemic-symmetry issue(s): "
                    f"{', '.join(kinds)}. The producer's self-recorded skepticism "
                    "is asymmetric/unreconciled, or a low-I² cross-agent pooled "
                    "estimate did not flag clinical heterogeneity. Quality warning "
                    "(does not block delivery)."
                ),
                evidence={"violations": violations},
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                "G43 OK — recorded skepticism is symmetric/reconciled and any "
                "cross-agent pooled estimate flags clinical heterogeneity as needed."
            ),
            evidence={
                "checked_skepticism": has_skepticism,
                "checked_pooled_estimate": has_pooled,
            },
        )
