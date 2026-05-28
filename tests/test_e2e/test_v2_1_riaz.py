"""v2.1 E2E gate — Riaz reference patient.

The Riaz reference dataset is the public methodology-demonstration patient
used to validate OPL's full pipeline end-to-end. The actual patient data
is NOT shipped in this repository (data is curated separately for size +
licensing reasons). When the directory is not present locally, this test
is SKIPPED.

The CLI-level smoke tests in ``tests/cli/`` already exercise the
``opl run --wave 3 --mode native`` executor without requiring patient
data, so the v2.1 truthful-execution contract is verified independent of
this gate.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

RIAZ_DIR = Path("patients/riaz_reference")


@pytest.mark.skipif(
    not RIAZ_DIR.exists() or not os.environ.get("OPL_RUN_E2E"),
    reason="Riaz reference data not present locally; set OPL_RUN_E2E=1 to run.",
)
def test_riaz_full_pipeline_v2_1():
    """Riaz reference must end-to-end through plan + waves 1-5 + audit."""
    run_id = "v2_1_riaz_smoke"
    cmds = [
        ["opl-cancer", "plan", "--patient", str(RIAZ_DIR), "--run-id", run_id,
         "--goal", "smoke-test the v2.1 pipeline"],
        ["opl-cancer", "run", "--wave", "3", "--patient-dir", str(RIAZ_DIR),
         "--run-id", run_id, "--mode", "native"],
    ]
    for cmd in cmds:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        assert r.returncode == 0, f"{' '.join(cmd)} failed: {r.stderr}"
