"""v2.3 E2E gate — Wave 6 manuscript + .n1a bundle on Riaz reference.

The Riaz reference dataset is the public methodology-demonstration patient.
The actual patient data is NOT shipped in this repository (data is curated
separately for size + licensing reasons). When the directory is not present
locally, this test is SKIPPED — same convention as v2.1 / v2.2.

Without Riaz data, an in-memory synthetic-Riaz fallback variant exercises
the Wave 6 runner shape end-to-end so the gate count + bundle structure +
G29-G33 pass on a reference-case data_source. The synthetic variant runs
unconditionally so v2.3 ship gates surface any structural regression.
"""
from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path

import pytest

from opl_cancer.glue.wave6_runner import run_wave6


RIAZ_DIR = Path("patients/riaz_reference")


GOOD_MS = """\
# Riaz Reference — Wave 6 manuscript (methodology demonstration)

## Abstract

**Background.** [BACKGROUND] N=1 case reports for melanoma have grown rapidly.

**Methods.** This is a single-subject (N=1) case report rendered via OPL v2.3.0 [integrator:opl_runtime run_id:riaz1].

**Results.** ICI response biomarkers were re-analysed for the reference patient [PMID:32179615].

**Conclusions.** Reference case for methodology demonstration only [BACKGROUND].

## Methods

This is a single-subject (N=1) case report following the N-of-1 design tradition [PMID:24379081].

## Results

The reference patient's TMB was elevated [integrator:tmb_harmonization run_id:riaz1].
"""

GOOD_AUTH = """\
# AI Authorship Disclosure

No human author beyond the patient and supervising clinician was involved.

## Contributions

| Expert | Role |
| --- | --- |
| Iain | Wave 1 retrieval |
| Aviv | Wave 3 statistics |
| Vince | Wave 4 reasoning |
| Henry | Wave 6 audit |
"""

GOOD_REPRO = """\
# Reproducibility

## Data sources

- TCGA-SKCM reference cohort, tier: public
- Riaz et al. 2017 melanoma cohort (PMID:29033130), tier: public
- (Reference) patient demonstration profile, tier: patient-private

## Software

- opl-cancer v2.3.0
"""

GOOD_HENRY = json.dumps({"audit_version": "v2.2", "gates_run": 28, "status": "pass"})


def _seed_synthetic_riaz(patient_dir: Path) -> Path:
    """Build a synthetic-Riaz patient_dir with Wave 5 + Wave 6 artifacts."""
    run_dir = patient_dir / "triggers" / "wave6_riaz_smoke"
    run_dir.mkdir(parents=True, exist_ok=True)
    # Wave 5 outputs
    (run_dir / "patient_plain_brief.md").write_text(
        "# Riaz reference — plain brief\n\nMethodology demonstration.\n",
        encoding="utf-8",
    )
    (run_dir / "patient_pi_brief.md").write_text(
        "# Riaz reference — PI brief\n\nMethodology demonstration.\n",
        encoding="utf-8",
    )
    # v2.5.1 B5: Wave 6 now requires plan.json + ≥1 wave1-4 artifact.
    (run_dir / "plan.json").write_text('{"tasks": []}', encoding="utf-8")
    w1 = run_dir / "tasks" / "w1_seed"
    w1.mkdir(parents=True, exist_ok=True)
    (w1 / "report.md").write_text("# wave 1 stub\n", encoding="utf-8")
    # Wave 6 artifacts
    (run_dir / "manuscript.md").write_text(GOOD_MS, encoding="utf-8")
    (run_dir / "manuscript_methods.md").write_text(
        "## Methods\n\nThis is a single-subject (N=1) case report.\n",
        encoding="utf-8",
    )
    (run_dir / "ai_authorship_disclosure.md").write_text(
        GOOD_AUTH, encoding="utf-8"
    )
    (run_dir / "reproducibility.md").write_text(GOOD_REPRO, encoding="utf-8")
    (run_dir / "HENRY_AUDIT.json").write_text(GOOD_HENRY, encoding="utf-8")
    (run_dir / "ethics_declaration.md").write_text(
        "# Ethics\n\nReference case; methodology demonstration only.\n",
        encoding="utf-8",
    )
    (run_dir / "world_unknown_appendix.md").write_text(
        "# Speculative candidates\n\nDrug-class redacted per G24 + N1Arxiv ethics.\n",
        encoding="utf-8",
    )
    figs = run_dir / "figures"
    figs.mkdir(exist_ok=True)
    (figs / "fig_1.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (figs / "fig_1.py").write_text(
        "random_seed = 42\nimport matplotlib.pyplot as plt\n# stub reproducer\n",
        encoding="utf-8",
    )
    return run_dir


def test_wave6_riaz_synthetic_passes_all_gates(tmp_path: Path) -> None:
    """v2.3 ship gate: Riaz synthetic must end-to-end through Wave 6.

    Covers: Wave 5 prereq, G29-G33 all PASS, manifest schema valid,
    zip exists, reference_case banner injected.
    """
    patient_dir = tmp_path / "patients" / "riaz_reference"
    _seed_synthetic_riaz(patient_dir)

    result = run_wave6(
        patient_dir=patient_dir,
        run_id="wave6_riaz_smoke",
        patient_code="riaz-melanoma-ref",
        opl_version="2.3.0",
        data_source="reference_case",
        mode="final",
    )
    assert result["status"] == "ok"
    # Bundle on disk
    zip_path = Path(result["zip_path"])
    assert zip_path.is_file()
    # Manifest schema-valid (writer already checks; double-check here)
    manifest = json.loads(Path(result["manifest_path"]).read_text())
    assert manifest["data_source"] == "reference_case"
    assert "REFERENCE CASE" in manifest["banner"]
    # G29-G33 all PASS
    for r in result["wave6_gate_results"]["results"]:
        assert r["status"] == "pass", f"gate {r['gate']} non-pass: {r['message']}"
    # Manuscript banner injected
    ms_text = (patient_dir / "triggers" / "wave6_riaz_smoke" / "manuscript.md").read_text()
    assert "REFERENCE CASE" in ms_text


@pytest.mark.skipif(
    not RIAZ_DIR.exists() or not os.environ.get("OPL_RUN_E2E"),
    reason="Riaz reference data not present locally; set OPL_RUN_E2E=1 to run.",
)
def test_wave6_riaz_full_data_e2e() -> None:
    """When the Riaz reference data IS local, exercise the full CLI surface
    including `opl wave6 --final --data-source reference_case`."""
    run_id = "v2_3_riaz_wave6"
    cmd = [
        "opl-cancer", "wave6",
        "--patient-dir", str(RIAZ_DIR),
        "--run-id", run_id,
        "--patient-code", "riaz-melanoma",
        "--final",
        "--data-source", "reference_case",
        "--json",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, f"{' '.join(cmd)} failed: {r.stderr}"
    payload = json.loads(r.stdout)
    assert payload["ok"] is True
    # Bundle exists
    assert Path(payload["zip_path"]).is_file()
    # Zip contains manifest.json + manuscript.md
    with zipfile.ZipFile(payload["zip_path"]) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert "manuscript.md" in names
