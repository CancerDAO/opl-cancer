"""G49: forecast_pre_registration — the forecast must precede the data.

C2 / ADR-0032 (research-team iteration). Taste is the one genuinely-new research
capability worth adding: a calibrated model of what an experiment will yield,
trained by forecast+correction. But each Wave2→Wave4 cycle is a labelled training
example ONLY if the prediction was recorded BEFORE the data — hindsight silently
overwrites it otherwise (the exact mechanism the principle warns about).

G49 enforces the two machine-verifiable halves of that discipline for any
forecasted hypothesis:
  1. ``forecast_locked_at`` exists and PRECEDES the earliest Wave-3 data artifact
     (``wave3_data_at``, supplied by the runner) — the forecast came first;
  2. ``forecast_hash`` matches the locked ``prior_expectation`` payload — the
     forecast was not rewritten after seeing the data.

BLOCKS on violation. A hypothesis with no ``prior_expectation`` SKIPs (not every
hypothesis carries a forecast). The cross-run Brier/hit-rate layer is explicitly
deferred (noise at current run volume); this is the within-run substrate only.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


def forecast_payload_hash(prior_expectation: dict[str, Any]) -> str:
    """Canonical sha256 of the locked forecast payload (tamper-evidence)."""
    canon = json.dumps(prior_expectation, sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


class G49ForecastPreRegistrationGate(Gate):
    """A forecasted hypothesis must have locked its forecast before the Wave-3 data."""

    name = "G49_forecast_pre_registration"
    description = (
        "For a hypothesis carrying a pre-data forecast (prior_expectation), verify "
        "forecast_locked_at precedes the earliest Wave-3 data artifact and "
        "forecast_hash matches the locked payload — so the forecast came first and "
        "was not overwritten by hindsight. Makes each Wave2→Wave4 cycle a scoreable "
        "labelled example (the taste-training substrate). Machine-verifiable; BLOCKS."
    )
    failure_mode_code = "C2-HINDSIGHT-FORECAST"
    family_id = "reasoning-quality"

    def check(self, claim: dict[str, Any]) -> GateResult:
        exp = claim.get("prior_expectation")
        if not isinstance(exp, dict) or not exp:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP,
                message="G49 SKIP — hypothesis carries no pre-data forecast.",
            )
        hid = claim.get("hypothesis_id", "?")
        locked_at = claim.get("forecast_locked_at")
        if not locked_at:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message=(
                    f"G49 FAIL — hypothesis {hid!r} has a forecast but no "
                    "forecast_locked_at. A forecast that was never locked before the "
                    "data is not a forecast; lock it at Wave 2, before the Wave-3 pull."
                ),
                evidence={"hypothesis_id": hid},
            )
        wave3_at = claim.get("wave3_data_at")
        if wave3_at and str(locked_at) >= str(wave3_at):
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message=(
                    f"G49 FAIL — hypothesis {hid!r} forecast_locked_at "
                    f"({locked_at}) is NOT before the Wave-3 data ({wave3_at}). A "
                    "forecast recorded after seeing the data is hindsight, not taste."
                ),
                evidence={"hypothesis_id": hid, "forecast_locked_at": locked_at,
                          "wave3_data_at": wave3_at},
            )
        expected = forecast_payload_hash(exp)
        if claim.get("forecast_hash") != expected:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message=(
                    f"G49 FAIL — hypothesis {hid!r} forecast_hash does not match the "
                    "locked prior_expectation payload: the forecast was rewritten "
                    "after locking (hindsight tampering)."
                ),
                evidence={"hypothesis_id": hid, "expected": expected,
                          "got": claim.get("forecast_hash")},
            )
        return GateResult(
            gate=self.name, status=GateStatus.PASS,
            message=(
                f"G49 OK — hypothesis {hid!r} forecast locked before the data and "
                "unmodified; this Wave2→Wave4 cycle is a scoreable forecast."
            ),
            evidence={"hypothesis_id": hid, "forecast_locked_at": locked_at},
        )
