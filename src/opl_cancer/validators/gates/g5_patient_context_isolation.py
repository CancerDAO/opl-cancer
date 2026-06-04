"""G5: patient-context isolation. Spec §7 G5 / §6.5 B1 + B3.

Failure modes B1 (cross-patient contamination via shared memory) and B3
(stale identity carry-over). G5 BLOCKs whenever the claim's patient_code
does not match the run_id's patient_code prefix — this catches any case
where a producer pulled an evidence cache / memory snippet keyed under
patient_A but is emitting under run_id of patient_B.

CrossPatientContaminationError is raised to make the violation impossible
to silently swallow upstream (see no-silent-fallback policy).
"""
from __future__ import annotations

import re
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


class CrossPatientContaminationError(RuntimeError):
    """G5 hard-failure: claim.patient_code disagrees with run_id."""


# run_id convention: <patient_code>__<task>__<isoZulu>  (memory + spec §3.6)
_RUN_ID_PREFIX = re.compile(r"^([A-Za-z0-9_\-]+?)__")


def _extract_patient_from_run_id(run_id: str) -> str | None:
    m = _RUN_ID_PREFIX.match(run_id)
    return m.group(1) if m else None


class G5PatientContextIsolationGate(Gate):
    name = "G5_patient_context_isolation"
    description = "claim.patient_code must match run_id's patient_code prefix."
    failure_mode_code = "B1"

    def __init__(self, raise_on_violation: bool = False) -> None:
        # When invoked inside the orchestrator we want a hard exception so
        # the downstream cannot silently consume cross-patient evidence.
        self.raise_on_violation = raise_on_violation

    def check(self, claim: dict[str, Any]) -> GateResult:
        claim_patient = claim.get("patient_code")
        run_id = claim.get("run_id") or claim.get("run", {}).get("id")
        if not claim_patient or not run_id:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="claim missing patient_code or run_id; cannot verify isolation",
            )
        run_patient = _extract_patient_from_run_id(str(run_id))
        if run_patient is None:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=f"run_id {run_id!r} does not encode patient_code prefix",
            )
        if run_patient != claim_patient:
            msg = (
                f"cross-patient contamination: claim.patient_code={claim_patient!r} "
                f"but run_id encodes {run_patient!r}"
            )
            if self.raise_on_violation:
                raise CrossPatientContaminationError(msg)
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=msg,
                evidence={"claim_patient": claim_patient, "run_patient": run_patient},
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"patient_code {claim_patient} consistent with run_id",
        )
