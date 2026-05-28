"""G32 — data_availability_declared unit tests."""
from __future__ import annotations

from pathlib import Path

from opl_cancer.validators.gates import G32DataAvailabilityDeclaredGate
from opl_cancer.validators.mechanical_gates import GateStatus


GATE = G32DataAvailabilityDeclaredGate()


GOOD = """\
# Reproducibility

## Data sources

- TCGA-LUAD RNA-seq, tier: public
- cBioPortal MSK Lung 2023 cohort, tier: public
- 007-zhiqiang EHR records, tier: patient-private
- ICGC PCAWG genomics, tier: DUA

## Software

- OPL v2.3.0
"""

UNTAGGED_PATIENT = """\
# Reproducibility

## Data sources

- TCGA-LUAD RNA-seq, tier: public
- The patient's EHR records and pathology reports
"""

UNKNOWN_TIER = """\
# Reproducibility

## Data sources

- TCGA-LUAD, tier: maybe-public
"""

NO_SECTION = """\
# Reproducibility

OPL v2.3.0 was used. Some data came from the patient.
"""

EMPTY_SECTION = """\
# Reproducibility

## Data sources

## Software
"""


def test_g32_pass_good(tmp_path: Path) -> None:
    res = GATE.check({"reproducibility_text": GOOD, "run_stage": "wave6"})
    assert res.status == GateStatus.PASS, res.message
    assert res.evidence["tiered_count"] >= 3


def test_g32_fail_untagged_patient() -> None:
    res = GATE.check({"reproducibility_text": UNTAGGED_PATIENT, "run_stage": "wave6"})
    assert res.status == GateStatus.FAIL
    assert res.block


def test_g32_fail_unknown_tier() -> None:
    res = GATE.check({"reproducibility_text": UNKNOWN_TIER, "run_stage": "wave6"})
    assert res.status == GateStatus.FAIL
    assert res.block


def test_g32_fail_no_section() -> None:
    res = GATE.check({"reproducibility_text": NO_SECTION, "run_stage": "wave6"})
    assert res.status == GateStatus.FAIL
    assert res.block


def test_g32_fail_empty_section() -> None:
    res = GATE.check({"reproducibility_text": EMPTY_SECTION, "run_stage": "wave6"})
    assert res.status == GateStatus.FAIL


def test_g32_skip_non_wave6() -> None:
    res = GATE.check({"reproducibility_text": GOOD, "run_stage": "wave3"})
    assert res.status == GateStatus.SKIP


def test_g32_bundle_root(tmp_path: Path) -> None:
    (tmp_path / "reproducibility.md").write_text(GOOD, encoding="utf-8")
    res = GATE.check({"bundle_root": str(tmp_path), "run_stage": "wave6"})
    assert res.status == GateStatus.PASS
