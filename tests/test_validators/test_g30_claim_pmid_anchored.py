"""G30 — claim_pmid_anchored unit tests."""
from __future__ import annotations

from pathlib import Path

from opl_cancer.validators.gates import G30ClaimPMIDAnchoredGate
from opl_cancer.validators.mechanical_gates import GateStatus


GATE = G30ClaimPMIDAnchoredGate()


GOOD_MS = """\
# Manuscript

## Introduction

[BACKGROUND] N=1 case reports have grown in importance for rare cancers.

Pembrolizumab demonstrates tissue-agnostic efficacy in MSI-H tumors [PMID:32179615].

KRAS G12C inhibitors show durable response in lung cancer [PMID:34161704].

## Methods

The patient's MSI status was computed via MSIsensor-pro [integrator:msisensor_pro run_id:abc123def].
"""

BAD_MS = """\
# Manuscript

## Results

Olaparib produced an objective response in this patient.

This finding mirrors the PROfound trial cohort [PMID:32343890].
"""


def test_g30_pass_all_anchored() -> None:
    res = GATE.check({"manuscript_text": GOOD_MS, "run_stage": "wave6"})
    assert res.status == GateStatus.PASS, res.message
    assert res.evidence["sentence_count"] >= 3


def test_g30_fail_one_unanchored() -> None:
    res = GATE.check({"manuscript_text": BAD_MS, "run_stage": "wave6"})
    assert res.status == GateStatus.FAIL
    assert res.block
    assert res.evidence["unanchored_count"] == 1


def test_g30_background_tag_exempts() -> None:
    text = "[BACKGROUND] Pembrolizumab acts on PD-1.\nThe patient responded [PMID:32179615]."
    res = GATE.check({"manuscript_text": text, "run_stage": "wave6"})
    assert res.status == GateStatus.PASS


def test_g30_integrator_anchor_accepted() -> None:
    text = "MSI score was 22.5 [integrator:msisensor_pro run_id:abc123def]."
    res = GATE.check({"manuscript_text": text, "run_stage": "wave6"})
    assert res.status == GateStatus.PASS


def test_g30_skip_non_wave6_stage() -> None:
    res = GATE.check({"manuscript_text": BAD_MS, "run_stage": "wave3"})
    assert res.status == GateStatus.SKIP


def test_g30_skip_no_claim_sentences() -> None:
    res = GATE.check({"manuscript_text": "# Empty\n", "run_stage": "wave6"})
    assert res.status == GateStatus.SKIP


def test_g30_table_rows_not_counted_as_claims() -> None:
    text = (
        "## Results\n\n"
        "| Variant | Effect |\n"
        "| --- | --- |\n"
        "| KRAS G12C | Activating |\n\n"
        "The variant is targetable with sotorasib [PMID:34161704].\n"
    )
    res = GATE.check({"manuscript_text": text, "run_stage": "wave6"})
    assert res.status == GateStatus.PASS


def test_g30_reads_from_bundle_root(tmp_path: Path) -> None:
    (tmp_path / "manuscript.md").write_text(GOOD_MS, encoding="utf-8")
    res = GATE.check({"bundle_root": str(tmp_path), "run_stage": "wave6"})
    assert res.status == GateStatus.PASS
