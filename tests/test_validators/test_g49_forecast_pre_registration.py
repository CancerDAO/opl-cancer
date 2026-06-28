"""G49 — predict-before-you-look: the forecast must be locked BEFORE the data.

C2 / ADR-0032. Taste is a calibrated model trained by forecast+correction — but
only if the prediction is recorded BEFORE the result, because hindsight silently
overwrites it. G49 verifies, for a forecasted hypothesis, that forecast_locked_at
precedes the earliest Wave-3 data artifact AND that forecast_hash matches the
locked payload (tamper-evidence). Machine-verifiable; BLOCKS. (Cross-run Brier is
deliberately out of scope — noise at current run volume.)
"""
from __future__ import annotations

from opl_cancer.validators.gates.g49_forecast_pre_registration import (
    G49ForecastPreRegistrationGate,
    forecast_payload_hash,
)
from opl_cancer.validators.mechanical_gates import GateStatus

_EXP = {"predicted_wave3_result": "cluster X enriched", "confidence_0_1": 0.7}


def test_skip_when_no_forecast():
    res = G49ForecastPreRegistrationGate().check({"hypothesis_id": "H1"})
    assert res.status == GateStatus.SKIP


def test_block_when_forecast_not_locked():
    res = G49ForecastPreRegistrationGate().check(
        {"hypothesis_id": "H1", "prior_expectation": _EXP}  # no forecast_locked_at
    )
    assert res.status == GateStatus.FAIL
    assert res.block is True


def test_block_when_forecast_locked_after_data_hindsight():
    res = G49ForecastPreRegistrationGate().check({
        "hypothesis_id": "H1", "prior_expectation": _EXP,
        "forecast_locked_at": "2026-06-02T10:00:00+00:00",
        "forecast_hash": forecast_payload_hash(_EXP),
        "wave3_data_at": "2026-06-01T10:00:00+00:00",  # data PRECEDES the forecast
    })
    assert res.status == GateStatus.FAIL
    assert res.block is True


def test_block_when_hash_mismatch_tampered():
    res = G49ForecastPreRegistrationGate().check({
        "hypothesis_id": "H1",
        "prior_expectation": {"predicted_wave3_result": "DIFFERENT now", "confidence_0_1": 0.9},
        "forecast_locked_at": "2026-06-01T10:00:00+00:00",
        "forecast_hash": forecast_payload_hash(_EXP),  # hash of the OLD payload
        "wave3_data_at": "2026-06-02T10:00:00+00:00",
    })
    assert res.status == GateStatus.FAIL
    assert res.block is True


def test_pass_when_locked_before_data_and_hash_matches():
    res = G49ForecastPreRegistrationGate().check({
        "hypothesis_id": "H1", "prior_expectation": _EXP,
        "forecast_locked_at": "2026-06-01T10:00:00+00:00",
        "forecast_hash": forecast_payload_hash(_EXP),
        "wave3_data_at": "2026-06-02T10:00:00+00:00",
    })
    assert res.status == GateStatus.PASS
