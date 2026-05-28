"""E2E — v2.2 bio-skills on 007-zhiqiang real patient (gated).

Per the task spec, requires:
  * OPL_REAL_PATIENT_OK=1 in the environment
  * The 007-zhiqiang patient directory at either:
      ~/cancerdao/patients/007-zhiqiang-CRC2022-G12C
      ~/cancerdao/patients/007-zhiqiang
      patients/007-zhiqiang-CRC2022-G12C
      patients/007-zhiqiang

The test exercises MSI + TMB + ACMG integrators with mocked inputs
representative of the real patient's NGS report (KRAS G12C, MSI-H,
TMB ≈ 18/Mb on TSO500, BRCA1 c.5266dupC germline). No PHI is hard-coded.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from opl_cancer.integrators.msi_sensor import MSIsensorIntegrator
from opl_cancer.integrators.tmb_harmonization import TMBHarmonizationIntegrator
from opl_cancer.integrators.varsome_acmg import AcmgGermlineIntegrator


_PATIENT_PATH_CANDIDATES = [
    Path.home() / "cancerdao" / "patients" / "007-zhiqiang-CRC2022-G12C",
    Path.home() / "cancerdao" / "patients" / "007-zhiqiang",
    Path("patients") / "007-zhiqiang-CRC2022-G12C",
    Path("patients") / "007-zhiqiang",
]


def _patient_dir() -> Path | None:
    for p in _PATIENT_PATH_CANDIDATES:
        if p.exists() and p.is_dir():
            return p
    return None


pytestmark = pytest.mark.skipif(
    os.environ.get("OPL_REAL_PATIENT_OK") != "1" or _patient_dir() is None,
    reason=(
        "real patient run requires OPL_REAL_PATIENT_OK=1 AND a 007 patient "
        "directory at one of the canonical paths"
    ),
)


def test_007_msi_call_runs() -> None:
    """007 is MSI-H per the real NGS report (CRC + Lynch family history)."""
    integ = MSIsensorIntegrator(mock_mode=True, mock_score=24.3, mock_sites=210)
    out = asyncio.run(integ.fetch("tumor:/tmp/t.bam:normal:/tmp/n.bam"))
    assert out["status"] == "MSI-H"
    assert out["msi_score"] >= 10


def test_007_tmb_harmonization_tso500() -> None:
    """007 TSO500 reports ~18 mut/Mb → TMB-H."""
    integ = TMBHarmonizationIntegrator()
    out = asyncio.run(integ.fetch("panel:TSO500:tmb_per_mb:18.0"))
    assert out["status"] == "TMB-H"
    assert out["panel"] == "TSO500"
    assert out["effective_mb"] == 1.94


def test_007_acmg_germline_brca1_pathogenic() -> None:
    """007 (or representative oncology proband) carries BRCA1 c.5266dupC
    (canonical HBOC pathogenic — PVS1 truncating + PS1 same residue PV +
    PM2 absent gnomAD)."""
    integ = AcmgGermlineIntegrator(
        mock_mode=True,
        mock_criteria=["PVS1", "PS1", "PM2"],
    )
    out = asyncio.run(integ.fetch("variant:BRCA1:c.5266dupC"))
    assert out["classification"] == "Pathogenic"
    assert out["gene"] == "BRCA1"


def test_007_patient_dir_present() -> None:
    """Smoke — when this test runs, the patient directory must be reachable."""
    pdir = _patient_dir()
    assert pdir is not None
    assert pdir.is_dir()
