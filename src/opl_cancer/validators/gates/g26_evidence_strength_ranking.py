"""G26: evidence-strength → ranking demotion gate. v1.5 P0-5.

Failure mode F-NEW-2 (introduced v1.5): a regimen ranking is boosted on
evidence that has a known weakness (subgroup-size < threshold of patient's
stratum OR I² > 60% in the justifying pool), AND the rendered output
does not demote the ranking accordingly. In v1.4 H02 sotorasib+pani
jumped +25 Elo to take #1 — Henry G14 explicitly flagged "patient L4+ is
evidence-thin window" but did not feed that caveat back into the
ranking. Caveats decoupled from rank adjustments (AP-3).

Rules:
  * If ``claim.elo_boost > 0`` AND ``claim.evidence_anchor`` references a
    pool where:
      - ``subgroup_match_fraction < 0.5`` (the patient's line-of-therapy
        / molecular / age stratum is < 50% of the pool), OR
      - ``i_squared > 60`` (substantial heterogeneity)
    THEN ``claim.elo_boost`` must be capped at ``max_allowed_boost``
    (default 15) AND a ``demotion_disclosed`` marker must appear in
    the rendered narrative.
  * If either fails: BLOCK with the specific demotion-rule violated.

This gate fires on Wave-2 / Wave-4 ranking claims that carry the
``elo_boost`` + ``evidence_anchor`` fields. The auditor (Henry)
runs it after the standard meta gates so that the demotion is wired
into the same artifact.
"""
from __future__ import annotations

from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_DEFAULT_MAX_BOOST_WHEN_WEAK = 15.0
_SUBGROUP_FRACTION_THRESHOLD = 0.5
_I_SQUARED_THRESHOLD_PCT = 60.0
_DEMOTION_MARKERS = ("demotion_disclosed", "rank_demoted_for_evidence_weakness")


def _normalise_i2(value: Any) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v < 0:
        return None
    return v if v > 1.0 else v * 100.0


class G26EvidenceStrengthRankingGate(Gate):
    name = "G26_evidence_strength_ranking"
    description = (
        "Cap ranking boost when evidence anchor has subgroup-mismatch or "
        "high I²; require demotion disclosure in render."
    )
    failure_mode_code = "F-NEW-2"

    def __init__(
        self,
        *,
        max_allowed_boost: float = _DEFAULT_MAX_BOOST_WHEN_WEAK,
        subgroup_fraction_threshold: float = _SUBGROUP_FRACTION_THRESHOLD,
        i_squared_threshold_pct: float = _I_SQUARED_THRESHOLD_PCT,
    ) -> None:
        self.max_allowed_boost = max_allowed_boost
        self.subgroup_fraction_threshold = subgroup_fraction_threshold
        self.i_squared_threshold_pct = i_squared_threshold_pct

    def check(self, claim: dict[str, Any]) -> GateResult:
        elo_boost = claim.get("elo_boost")
        if elo_boost is None:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="no elo_boost on claim; gate not applicable",
            )
        try:
            elo_boost = float(elo_boost)
        except (TypeError, ValueError):
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=f"elo_boost not numeric: {claim.get('elo_boost')!r}",
            )
        if elo_boost <= 0:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=f"elo_boost {elo_boost} ≤ 0; no demotion needed",
            )

        anchor = claim.get("evidence_anchor") or {}
        subgroup_match = anchor.get("subgroup_match_fraction")
        i2 = _normalise_i2(anchor.get("i_squared") or anchor.get("i2"))

        weak_subgroup = (
            subgroup_match is not None
            and float(subgroup_match) < self.subgroup_fraction_threshold
        )
        weak_heterogeneity = (
            i2 is not None and i2 > self.i_squared_threshold_pct
        )
        if not (weak_subgroup or weak_heterogeneity):
            return GateResult(
                gate=self.name,
                status=GateStatus.PASS,
                message="evidence anchor strong enough for boost",
                evidence={
                    "elo_boost": elo_boost,
                    "subgroup_match_fraction": subgroup_match,
                    "i_squared_pct": i2,
                },
            )

        problems: list[str] = []
        if elo_boost > self.max_allowed_boost:
            problems.append(
                f"elo_boost={elo_boost} > max_allowed_boost={self.max_allowed_boost} "
                f"despite weak evidence"
            )
        markers_text = " ".join(
            str(claim.get(k, "")) for k in ("notes", "narrative", "summary", "verdict")
        )
        flags = claim.get("flags") or []
        flag_list = [str(f).lower() for f in flags] if isinstance(flags, list) else []
        has_demotion_marker = any(
            m in markers_text.lower() or m in flag_list for m in _DEMOTION_MARKERS
        )
        if not has_demotion_marker:
            problems.append(
                "no demotion_disclosed marker in narrative / flags despite weak evidence"
            )

        if problems:
            reason_bits = []
            if weak_subgroup:
                reason_bits.append(
                    f"subgroup_match_fraction={subgroup_match} "
                    f"< {self.subgroup_fraction_threshold}"
                )
            if weak_heterogeneity:
                reason_bits.append(
                    f"i_squared={i2}% > {self.i_squared_threshold_pct}%"
                )
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "Evidence weakness must demote ranking: "
                    + "; ".join(reason_bits)
                    + ". Problems: "
                    + "; ".join(problems)
                ),
                evidence={
                    "elo_boost": elo_boost,
                    "max_allowed_boost": self.max_allowed_boost,
                    "subgroup_match_fraction": subgroup_match,
                    "i_squared_pct": i2,
                    "problems": problems,
                },
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                "evidence-weak but elo_boost is capped + demotion disclosed"
            ),
            evidence={
                "elo_boost": elo_boost,
                "max_allowed_boost": self.max_allowed_boost,
                "subgroup_match_fraction": subgroup_match,
                "i_squared_pct": i2,
            },
        )
