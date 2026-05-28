"""v2.1 E2E gate — 007-zhiqiang real patient (gated on consent flag).

Requires:

* ``OPL_REAL_PATIENT_OK=1`` (explicit patient-consent flag).
* The actual 007 patient directory at the canonical path. This data is
  curated outside the repo for privacy reasons; when absent the test is
  skipped.

See ``feedback_multi_case_validation`` — at least one real patient must
exercise the full pipeline before any release ships, but in this CI
context we may run with the data absent.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

# Canonical curated location is outside the repo (privacy).
_CURATED_007 = Path.home() / "cancerdao" / "patients" / "007-zhiqiang-CRC2022-G12C"
_REPO_007 = Path("patients/007-zhiqiang")
P007_DIR = _CURATED_007 if _CURATED_007.exists() else _REPO_007


@pytest.mark.skipif(
    not P007_DIR.exists() or not os.environ.get("OPL_REAL_PATIENT_OK"),
    reason="007 patient data not present OR OPL_REAL_PATIENT_OK consent flag unset.",
)
def test_007_full_pipeline_v2_1():
    run_id = "v2_1_007_smoke"
    cmds = [
        ["opl-cancer", "plan", "--patient", str(P007_DIR), "--run-id", run_id,
         "--goal", "evaluate vaccine + TCR-T options after L4 progression"],
        ["opl-cancer", "run", "--wave", "3", "--patient-dir", str(P007_DIR),
         "--run-id", run_id, "--mode", "native"],
    ]
    for cmd in cmds:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        assert r.returncode == 0, f"{' '.join(cmd)} failed: {r.stderr}"
