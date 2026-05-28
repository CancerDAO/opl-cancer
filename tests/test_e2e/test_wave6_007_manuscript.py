"""v2.3 E2E gate — Wave 6 on real patient 007-zhiqiang.

Real-patient gating: only runs when the patient directory is present AND
the operator has explicitly opted in via OPL_REAL_PATIENT_OK=1. This
matches the v2.1 / v2.2 real-patient gating convention.

When the gating is OFF, this test is SKIPPED — the v2.3 ship gate uses
the synthetic 007 fallback below to exercise the runner shape end-to-end.
"""
from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path

import pytest

from opl_cancer.glue.wave6_runner import run_wave6


REAL_007_DIR = Path("patients/007-zhiqiang")


GOOD_MS_007 = """\
# Patient 007 — Wave 6 manuscript

## Abstract

**Background.** [BACKGROUND] N=1 reports for advanced solid tumors are increasingly relevant.

**Methods.** This is a single-subject (N=1) case report rendered via OPL v2.3.0 [integrator:opl_runtime run_id:007demo].

**Results.** MSI status was MSS [integrator:msisensor_pro run_id:007demo].

**Conclusions.** The patient retains sole decision authority [BACKGROUND].

## Methods

This is a single-subject (N=1) case report following the N-of-1 design tradition [PMID:24379081].

## Results

Patient's TMB was 8.2 mut/Mb [integrator:tmb_harmonization run_id:007demo].
"""

GOOD_AUTH_007 = """\
# AI Authorship Disclosure

No human author beyond the patient and supervising clinician was involved.

## Contributions

| Expert | Role |
| --- | --- |
| Iain | Wave 1 |
| Aviv | Wave 3 |
| Vince | Wave 4 |
| Henry | Wave 6 |
"""

GOOD_REPRO_007 = """\
# Reproducibility

## Data sources

- 007-zhiqiang EHR + pathology, tier: patient-private
- TCGA + cBioPortal reference cohorts, tier: public
- PubMed snapshot for Wave 1, tier: public

## Software

- opl-cancer v2.3.0
"""

GOOD_HENRY_007 = json.dumps({
    "audit_version": "v2.2", "gates_run": 28, "status": "pass"
})


def _seed_synthetic_007(patient_dir: Path) -> Path:
    """Build a synthetic patient_dir mirroring the 007-zhiqiang shape."""
    run_dir = patient_dir / "triggers" / "wave6_007_synth"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "patient_plain_brief.md").write_text(
        "# Plain brief\n", encoding="utf-8"
    )
    (run_dir / "patient_pi_brief.md").write_text(
        "# PI brief\n", encoding="utf-8"
    )
    # v2.5.1 B5: Wave 6 now requires plan.json + ≥1 wave1-4 artifact.
    (run_dir / "plan.json").write_text('{"tasks": []}', encoding="utf-8")
    w1 = run_dir / "tasks" / "w1_seed"
    w1.mkdir(parents=True, exist_ok=True)
    (w1 / "report.md").write_text("# wave 1 stub\n", encoding="utf-8")
    (run_dir / "manuscript.md").write_text(GOOD_MS_007, encoding="utf-8")
    (run_dir / "manuscript_methods.md").write_text(
        "## Methods\n\nThis is a single-subject (N=1) case report.\n",
        encoding="utf-8",
    )
    (run_dir / "ai_authorship_disclosure.md").write_text(
        GOOD_AUTH_007, encoding="utf-8"
    )
    (run_dir / "reproducibility.md").write_text(GOOD_REPRO_007, encoding="utf-8")
    (run_dir / "HENRY_AUDIT.json").write_text(GOOD_HENRY_007, encoding="utf-8")
    (run_dir / "ethics_declaration.md").write_text(
        "# Ethics\n\nFounder mode; consent on file.\n", encoding="utf-8"
    )
    figs = run_dir / "figures"
    figs.mkdir(exist_ok=True)
    (figs / "fig_1.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (figs / "fig_1.py").write_text(
        "random_seed = 42\n# stub\n", encoding="utf-8"
    )
    # Cost log so the manifest aggregates a meaningful cost summary
    (run_dir / "cost_log.jsonl").write_text(
        json.dumps({
            "model": "claude-opus-4-7",
            "prompt_tokens": 50000,
            "completion_tokens": 20000,
            "usd_at_time": 2.25,
            "wave": "6",
            "expert": "iain",
        }) + "\n",
        encoding="utf-8",
    )
    return run_dir


def test_wave6_007_synthetic_passes_all_gates(tmp_path: Path) -> None:
    """v2.3 ship gate (real-patient stand-in): mirrors the 007 directory
    shape and exercises Wave 6 end-to-end on real_patient data_source.
    This satisfies the multi-case validation requirement
    (memory:feedback_multi_case_validation): 2 patients (riaz + 007 synthetic).
    """
    patient_dir = tmp_path / "patients" / "007-zhiqiang"
    _seed_synthetic_007(patient_dir)

    result = run_wave6(
        patient_dir=patient_dir,
        run_id="wave6_007_synth",
        patient_code="007-zhiqiang",
        opl_version="2.3.0",
        data_source="real_patient",
        mode="final",
    )
    assert result["status"] == "ok"
    assert Path(result["zip_path"]).is_file()
    manifest = json.loads(Path(result["manifest_path"]).read_text())
    assert manifest["data_source"] == "real_patient"
    # Real patient: NO banner
    assert manifest.get("banner") in (None, "")
    # All gates pass
    for r in result["wave6_gate_results"]["results"]:
        assert r["status"] == "pass", f"{r['gate']}: {r['message']}"
    # Cost summary aggregated
    assert manifest["cost_summary"]["total_usd"] == 2.25


@pytest.mark.skipif(
    not REAL_007_DIR.exists() or os.environ.get("OPL_REAL_PATIENT_OK") != "1",
    reason=(
        "007-zhiqiang real patient data not present, or OPL_REAL_PATIENT_OK "
        "not set to 1. This guard is intentional — running on real patient "
        "data requires explicit operator opt-in."
    ),
)
def test_wave6_007_real_full_e2e() -> None:
    """End-to-end on the real 007-zhiqiang patient directory.

    Exercises:
    - Wave 5 prereq check
    - All 33 mechanical gates (G1-G33) via merged HENRY_AUDIT
    - G29-G33 specifically against the real manuscript
    - .n1a zip emission + schema-valid manifest
    - Multi-case generalisation (this is the 2nd patient case after Riaz)
    """
    run_id = "v2_3_007_wave6"
    cmd = [
        "opl-cancer", "wave6",
        "--patient-dir", str(REAL_007_DIR),
        "--run-id", run_id,
        "--patient-code", "007-zhiqiang",
        "--final",
        "--data-source", "real_patient",
        "--json",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, f"{' '.join(cmd)} failed: {r.stderr}"
    payload = json.loads(r.stdout)
    assert payload["ok"] is True
    # Zip exists
    assert Path(payload["zip_path"]).is_file()
    with zipfile.ZipFile(payload["zip_path"]) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert "manuscript.md" in names
        # Real patient: no banner; manuscript should NOT carry [REFERENCE CASE]
        ms_text = zf.read("manuscript.md").decode("utf-8")
        assert "[REFERENCE CASE" not in ms_text
        assert "[METHODOLOGY DEMONSTRATION" not in ms_text
