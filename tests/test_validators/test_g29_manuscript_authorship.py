"""G29 — manuscript_authorship_disclosed unit tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from opl_cancer.validators.gates import G29ManuscriptAuthorshipDisclosedGate
from opl_cancer.validators.mechanical_gates import GateStatus


GATE = G29ManuscriptAuthorshipDisclosedGate()

GOOD_DISCLOSURE = """\
# AI Authorship Disclosure (CRediT-style)

This manuscript was prepared via the OPL for Cancer multi-expert pipeline.
No human author beyond the patient and supervising clinician was involved.

## Contributions

| Expert | Role | Contribution |
| --- | --- | --- |
| Iain | Lit synth | Wave 1 retrieval and intro draft |
| Aviv | Stats | Wave 3 KM curves, methods |
| Vince | Clinical reasoning | Discussion |
| Henry | Auditor | Limitations + G29-G33 gate validation |
"""

NO_ATTESTATION = """\
# AI Authorship Disclosure

## Contributions

| Expert | Role |
| --- | --- |
| Iain | Wave 1 |
"""

NO_CONTRIB_TABLE = """\
# AI Authorship Disclosure

No human author beyond the patient and supervising clinician was involved.
"""


def test_g29_pass_inline_good_disclosure() -> None:
    res = GATE.check(
        {"ai_authorship_disclosure": GOOD_DISCLOSURE, "run_stage": "wave6"}
    )
    assert res.status == GateStatus.PASS, res.message
    assert "iain" in res.evidence["experts_found"]
    assert "henry" in res.evidence["experts_found"]


def test_g29_fail_missing_attestation() -> None:
    res = GATE.check(
        {"ai_authorship_disclosure": NO_ATTESTATION, "run_stage": "wave6"}
    )
    assert res.status == GateStatus.FAIL
    assert res.block
    assert "attestation" in res.message.lower()


def test_g29_fail_no_contrib_table() -> None:
    res = GATE.check(
        {"ai_authorship_disclosure": NO_CONTRIB_TABLE, "run_stage": "wave6"}
    )
    assert res.status == GateStatus.FAIL
    assert res.block
    assert "contribution" in res.message.lower() or "credit" in res.message.lower()


def test_g29_fail_missing_file(tmp_path: Path) -> None:
    res = GATE.check(
        {"ai_authorship_disclosure_path": str(tmp_path / "missing.md"),
         "run_stage": "wave6"}
    )
    assert res.status == GateStatus.FAIL
    assert res.block


def test_g29_skip_non_wave6_stage() -> None:
    res = GATE.check(
        {"ai_authorship_disclosure": "", "run_stage": "wave3"}
    )
    assert res.status == GateStatus.SKIP


def test_g29_reads_from_bundle_root(tmp_path: Path) -> None:
    (tmp_path / "ai_authorship_disclosure.md").write_text(
        GOOD_DISCLOSURE, encoding="utf-8"
    )
    res = GATE.check({"bundle_root": str(tmp_path), "run_stage": "wave6"})
    assert res.status == GateStatus.PASS


def test_g29_fail_no_field_at_all() -> None:
    res = GATE.check({"run_stage": "wave6"})
    assert res.status == GateStatus.FAIL
    assert res.block
