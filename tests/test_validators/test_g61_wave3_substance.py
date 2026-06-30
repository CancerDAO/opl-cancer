"""G61 wave3_substance_executed — block delivery when Wave-3 analysis ran
dry-run-only (un-computed numbers presented as measured evidence).

The substance gap: a dry-run NativeAnalysisRunner/BixbenchRunner writes
non-empty metadata into wave3_data_evidence.json, so the existing hollow-run
detector (which checks emptiness) passes — but no actual computation happened.
A patient brief must not present un-computed quantitative predictions
(HR/CI/Cox/KM) as measured evidence. G61 makes the harness DETECT this.
"""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.validators.gates import G61Wave3SubstanceGate


def _write_w3(run_dir: Path, modes: list[str]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    runs = [
        {"hyp_id": f"h{i}", "bixbench_result": {"mode": m, "executed": m.endswith("live")}}
        for i, m in enumerate(modes)
    ]
    (run_dir / "wave3_data_evidence.json").write_text(
        json.dumps({"run_id": "r1", "analysis_runs": runs, "validations": []}),
        encoding="utf-8",
    )


def test_all_dry_run_blocks(tmp_path: Path) -> None:
    _write_w3(tmp_path, ["dry-run", "native-dry-run"])
    r = G61Wave3SubstanceGate().check({"run_dir": str(tmp_path)})
    assert r.status.value == "fail"
    assert r.block is True
    assert "dry-run" in r.message.lower()


def test_at_least_one_live_passes(tmp_path: Path) -> None:
    _write_w3(tmp_path, ["native-dry-run", "live"])
    r = G61Wave3SubstanceGate().check({"run_dir": str(tmp_path)})
    assert r.status.value == "pass"
    assert r.block is False


def test_no_wave3_evidence_skips(tmp_path: Path) -> None:
    # absent file → other gates (G25/delivery_runner) own the "no evidence" case
    r = G61Wave3SubstanceGate().check({"run_dir": str(tmp_path)})
    assert r.status.value == "skip"
    assert r.block is False


def test_empty_analysis_runs_skips(tmp_path: Path) -> None:
    # a run that materialised NO analysis runs has nothing to judge here
    (tmp_path / "wave3_data_evidence.json").write_text(
        json.dumps({"run_id": "r1", "analysis_runs": [], "validations": []}),
        encoding="utf-8",
    )
    r = G61Wave3SubstanceGate().check({"run_dir": str(tmp_path)})
    assert r.status.value == "skip"


def test_top_level_analysis_mode_field_respected(tmp_path: Path) -> None:
    # forward-compat: a top-level analysis_mode summary is honoured if present
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "wave3_data_evidence.json").write_text(
        json.dumps({"run_id": "r1", "analysis_mode": "live",
                    "analysis_runs": [{"hyp_id": "h0", "bixbench_result": {"mode": "dry-run"}}]}),
        encoding="utf-8",
    )
    r = G61Wave3SubstanceGate().check({"run_dir": str(tmp_path)})
    # top-level live overrides per-run dry-run (e.g. native path executed, bix skipped)
    assert r.status.value == "pass"
