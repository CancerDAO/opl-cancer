"""C2/ADR-0032 — G49 forecast_pre_registration is LIVE-WIRED into run_delivery_gates.

Predict-before-you-look only trains taste if the forecast is locked BEFORE the
Wave-3 data and not rewritten afterwards. G49 verifies that per hypothesis; this
proves the delivery sweep now fires it per top-k hypothesis in
wave2_hypotheses.json, deriving wave3_data_at from the run-local wave3 artifact,
and that it neither misfires on a forecast-less hypothesis nor on the common
non-Docker path where Wave 3 never ran.
"""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.glue.delivery_gate_runner import run_delivery_gates
from opl_cancer.validators.gates.g49_forecast_pre_registration import forecast_payload_hash

_EXP = {"predicted_wave3_result": "cluster X enriched", "confidence_0_1": 0.7}


def _run_root(tmp_path: Path) -> Path:
    r = tmp_path / "patient" / "triggers" / "r1"
    r.mkdir(parents=True)
    return r


def _wave2_hyp(r: Path, hyp: dict) -> None:
    (r / "wave2_hypotheses.json").write_text(
        json.dumps({"hypotheses": [hyp]}), encoding="utf-8"
    )


def test_g49_live_wired_blocks_hindsight_forecast(tmp_path: Path) -> None:
    r = _run_root(tmp_path)
    _wave2_hyp(r, {
        "id": "h1", "prior_expectation": _EXP,
        "forecast_locked_at": "2099-01-01T00:00:00+00:00",  # AFTER the data below
        "forecast_hash": forecast_payload_hash(_EXP),
    })
    (r / "wave3_data_evidence.json").write_text("{}", encoding="utf-8")  # data lands ~now
    verdict = run_delivery_gates(run_root=r, write_attestation=False)
    assert "G49_forecast_pre_registration" in verdict["blocked_by"], verdict["blocked_by"]


def test_g49_live_wired_passes_forecast_before_data(tmp_path: Path) -> None:
    r = _run_root(tmp_path)
    _wave2_hyp(r, {
        "id": "h1", "prior_expectation": _EXP,
        "forecast_locked_at": "2000-01-01T00:00:00+00:00",  # before the data below
        "forecast_hash": forecast_payload_hash(_EXP),
    })
    (r / "wave3_data_evidence.json").write_text("{}", encoding="utf-8")
    verdict = run_delivery_gates(run_root=r, write_attestation=False)
    assert "G49_forecast_pre_registration" not in verdict["blocked_by"], verdict["blocked_by"]


def test_g49_live_wired_passes_when_no_wave3_yet(tmp_path: Path) -> None:
    """Non-Docker path: a locked forecast with no Wave-3 data must NOT block."""
    r = _run_root(tmp_path)
    _wave2_hyp(r, {
        "id": "h1", "prior_expectation": _EXP,
        "forecast_locked_at": "2026-06-01T00:00:00+00:00",
        "forecast_hash": forecast_payload_hash(_EXP),
    })
    verdict = run_delivery_gates(run_root=r, write_attestation=False)
    assert "G49_forecast_pre_registration" not in verdict["blocked_by"], verdict["blocked_by"]


def test_g49_does_not_misfire_without_forecast(tmp_path: Path) -> None:
    r = _run_root(tmp_path)
    _wave2_hyp(r, {"id": "h1"})  # carries no prior_expectation → G49 SKIPs
    verdict = run_delivery_gates(run_root=r, write_attestation=False)
    assert "G49_forecast_pre_registration" not in verdict["blocked_by"], verdict["blocked_by"]
