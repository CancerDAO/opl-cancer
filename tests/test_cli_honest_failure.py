"""P0-CRIT-A + P1-F — CLI wave commands must be HONEST state-readers.

Through v1.5.6 `cli.py wave1/wave2/wave3/wave4` ran `mkdir -p` then returned
`{"ok": true}` regardless of whether real expert reports, tournament rounds,
or data artifacts existed. That false-positive ok let the v1.4 run claim
"complete" while Wave 3 had been skipped — the user had to ask "是否真的做了
数据分析" to surface the gap.

These tests pin the new behaviour: a wave is `ok` ONLY when the artifacts
that real execution leaves behind are actually on disk. Empty run-root →
non-zero exit + `requires_main_thread_dispatch: true`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_cli(args: list[str], cwd: Path | None = None) -> tuple[int, dict]:
    """Invoke `python -m opl_cancer.cli ...` and parse JSON output."""
    proc = subprocess.run(
        [sys.executable, "-m", "opl_cancer.cli", *args, "--json"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        payload = {"raw_stdout": proc.stdout, "raw_stderr": proc.stderr}
    return proc.returncode, payload


def _setup_patient(tmp_path: Path, run_id: str = "run-test-honest") -> tuple[Path, Path, Path]:
    patient = tmp_path / "patients" / "PT-TEST"
    patient.mkdir(parents=True, exist_ok=True)
    run_root = patient / "triggers" / run_id
    plan_path = patient / "plan.json"
    plan_path.write_text('{"tasks": []}')
    return patient, run_root, plan_path


def test_wave1_empty_run_root_exits_nonzero(tmp_path: Path) -> None:
    """Wave 1 with no expert reports → ok=false, exit ≠ 0, action says dispatch."""
    patient, run_root, plan_path = _setup_patient(tmp_path)
    rc, payload = _run_cli([
        "wave1",
        "--patient", str(patient),
        "--run-id", "run-test-honest",
        "--plan", str(plan_path),
    ])
    assert rc != 0, f"empty wave1 must exit non-zero, got rc={rc} payload={payload}"
    assert payload["ok"] is False
    assert payload["requires_main_thread_dispatch"] is True
    assert payload["artifacts_found"] == 0
    assert "dispatch" in payload["action"].lower()


def test_wave3_empty_run_root_exits_nonzero(tmp_path: Path) -> None:
    """Wave 3 — the highest-stakes false-completion vector — MUST refuse to claim ok
    without real artifacts. This is the central failure from the v1.4 run."""
    patient, run_root, plan_path = _setup_patient(tmp_path)
    rc, payload = _run_cli([
        "wave3",
        "--patient", str(patient),
        "--run-id", "run-test-honest",
    ])
    assert rc != 0
    assert payload["ok"] is False
    assert payload["wave"] == 3
    assert "non-skippable" in payload["expected"].lower() or "wave 3" in payload["expected"].lower()


def test_wave3_with_real_artifact_returns_ok(tmp_path: Path) -> None:
    """If a real cohort CSV / meta JSON / GEPIA3 result exists, wave3 returns ok=true."""
    patient, run_root, _ = _setup_patient(tmp_path)
    data_dir = run_root / "data" / "cohorts"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "kras_g12c_crc.csv").write_text("sample_id,os_months\nP001,18.2\nP002,22.4\n")

    rc, payload = _run_cli([
        "wave3",
        "--patient", str(patient),
        "--run-id", "run-test-honest",
    ])
    assert rc == 0
    assert payload["ok"] is True
    assert payload["artifacts_found"] >= 1
    assert any("kras_g12c_crc.csv" in f for f in payload["artifacts_sample"])


def test_wave2_with_tournament_artifact_returns_ok(tmp_path: Path) -> None:
    patient, run_root, _ = _setup_patient(tmp_path)
    tournament_dir = run_root / "tournament"
    tournament_dir.mkdir(parents=True, exist_ok=True)
    (tournament_dir / "round_001.json").write_text('{"round": 1, "outcomes": []}')

    rc, payload = _run_cli([
        "wave2",
        "--patient", str(patient),
        "--run-id", "run-test-honest",
    ])
    assert rc == 0
    assert payload["ok"] is True
    assert payload["wave"] == 2


def test_wave4_empty_run_root_exits_nonzero(tmp_path: Path) -> None:
    patient, run_root, _ = _setup_patient(tmp_path)
    rc, payload = _run_cli([
        "wave4",
        "--patient", str(patient),
        "--run-id", "run-test-honest",
    ])
    assert rc != 0
    assert payload["ok"] is False
