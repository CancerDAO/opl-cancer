"""G14: dataset-patient match score floor. Spec §7 G14 / §6.5 F1.

Failure mode F1 — irrelevant dataset (e.g. pulling lung-adeno cohort to
support a HCC claim, or pooling overall NSCLC cohort to predict a LM-positive
subset, or fitting a 70%-white MSK-IMPACT cohort to a Chinese patient
without surfacing the ethnicity skew).

The dataset_acquisition producer must emit a ``match_score`` describing how
well the chosen dataset fits the patient along these axes:

  Mandatory:
    - cancer_type        (HCC ≠ NSCLC ≠ TNBC)
    - stage              (early-stage ≠ stage IV)
    - platform           (NGS panel ≠ WES ≠ RNA-seq ≠ scRNA)
    - sample_size        (adequate power for the comparison)
  Conditional (axis applied only when the patient profile carries the field):
    - metastatic_site    (LM-positive ≠ liver-only ≠ bone-only — when patient
                          has site-specific metastasis that affects prognosis)
    - cns_involvement    (CNS+ ≠ CNS- — neuroimaging-relevant queries)
    - ethnicity          (Asian ≠ White ≠ Black — when cohort skews and the
                          biomarker frequency or drug PK differs by ancestry,
                          e.g. EGFR-mut frequency, TPMT/UGT1A1 PGx)
    - sex                (when biology is sex-dimorphic, e.g. HCC, RCC, urothelial)
    - age_bracket        (pediatric ≠ adult ≠ elderly when adverse-event
                          frequency or dosing differs materially)

G14 flags Reviewer-reselect whenever overall match_score < 0.6 OR whenever
any APPLICABLE conditional axis is < 0.4 (signalling a dimension that may
make the prediction non-generalisable for this specific patient). It does
NOT block hard — Reviewer is asked to validate or swap dataset; if Reviewer
endorses the choice anyway, the run continues with a permanent warning in
evidence so the patient brief carries the caveat.
"""
from __future__ import annotations

from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_REQUIRED_AXES = ("cancer_type", "stage", "platform", "sample_size")
_CONDITIONAL_AXES = (
    "metastatic_site", "cns_involvement", "ethnicity", "sex", "age_bracket",
)
_CONDITIONAL_FLOOR = 0.4


class G14DatasetPatientMatchGate(Gate):
    name = "G14_dataset_patient_match"
    description = "Dataset match_score must be ≥ 0.6 across cancer-type/stage/platform/sample-size."
    failure_mode_code = "F1"

    def __init__(self, threshold: float = 0.6) -> None:
        self.threshold = threshold

    def check(self, claim: dict[str, Any]) -> GateResult:
        ds = claim.get("dataset_acquisition") or claim.get("dataset") or {}
        if not ds:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="no dataset_acquisition output on claim",
            )
        score = ds.get("match_score")
        if score is None:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message="dataset_acquisition missing match_score field",
            )
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=f"match_score not parseable as float: {score!r}",
            )
        # Per-axis sub-scores expected (informational)
        axis_scores = {k: ds.get(f"{k}_score") for k in _REQUIRED_AXES}
        # Conditional axes are only enforced when the dataset_acquisition
        # producer explicitly emits them (i.e. the patient profile actually
        # carries that dimension). Missing conditional → axis ignored.
        conditional_scores = {
            k: ds.get(f"{k}_score") for k in _CONDITIONAL_AXES
            if ds.get(f"{k}_score") is not None
        }

        violations: list[str] = []
        if score_f < self.threshold:
            violations.append(
                f"overall match_score={score_f:.2f} < {self.threshold:.2f}"
            )
        for axis, axis_score in conditional_scores.items():
            try:
                v = float(axis_score)
            except (TypeError, ValueError):
                continue
            if v < _CONDITIONAL_FLOOR:
                violations.append(
                    f"conditional axis {axis}={v:.2f} < {_CONDITIONAL_FLOOR:.2f} "
                    f"(prediction may not generalise to this patient on this dimension)"
                )

        if violations:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=False,  # WARN — reviewer-reselect, not hard block
                message=(
                    "G14 dataset/patient match weak — " + "; ".join(violations) + "; "
                    "Reviewer should reselect dataset OR widen patient brief caveats"
                ),
                evidence={
                    "match_score": score_f,
                    "threshold": self.threshold,
                    "axis_scores": axis_scores,
                    "conditional_axis_scores": conditional_scores,
                    "conditional_floor": _CONDITIONAL_FLOOR,
                    "reviewer_action": "reselect_dataset_or_widen_caveats",
                },
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"dataset match_score={score_f:.2f} ≥ {self.threshold:.2f}",
            evidence={
                "match_score": score_f,
                "axis_scores": axis_scores,
                "conditional_axis_scores": conditional_scores,
            },
        )
