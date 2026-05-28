"""G33 — n1_design_transparent unit tests."""
from __future__ import annotations

from pathlib import Path

from opl_cancer.validators.gates import G33N1DesignTransparentGate
from opl_cancer.validators.mechanical_gates import GateStatus


GATE = G33N1DesignTransparentGate()


GOOD = """\
## Methods

This is a single-subject (N=1) case report following the N-of-1 study
design tradition for individualized oncology. All retrieval and analysis
were performed for one patient only.
"""

GOOD_WITH_COHORT_CAVEAT = """\
## Methods

This is a single-subject (N=1) case report. For reference, the KEYNOTE-189
cohort is referenced as background but not extrapolated.
"""

NO_N1_DECL = """\
## Methods

We applied the OPL pipeline to this patient. Data were extracted from a
prospective study database for context.
"""

UNHEDGED_COHORT = """\
## Methods

This single-subject (N=1) report applied OPL.

We compared treatment response in our patient population with prior cohort
data; the cohort retrospective study found similar response rates.
"""


def test_g33_pass_good() -> None:
    res = GATE.check({"manuscript_methods_text": GOOD, "run_stage": "wave6"})
    assert res.status == GateStatus.PASS, res.message


def test_g33_pass_with_cohort_caveat() -> None:
    res = GATE.check({"manuscript_methods_text": GOOD_WITH_COHORT_CAVEAT, "run_stage": "wave6"})
    assert res.status == GateStatus.PASS


def test_g33_fail_no_n1_declaration() -> None:
    res = GATE.check({"manuscript_methods_text": NO_N1_DECL, "run_stage": "wave6"})
    assert res.status == GateStatus.FAIL
    assert res.block


def test_g33_fail_unhedged_cohort() -> None:
    res = GATE.check({"manuscript_methods_text": UNHEDGED_COHORT, "run_stage": "wave6"})
    assert res.status == GateStatus.FAIL
    assert res.block


def test_g33_skip_non_wave6() -> None:
    res = GATE.check({"manuscript_methods_text": GOOD, "run_stage": "wave3"})
    assert res.status == GateStatus.SKIP


def test_g33_resolves_from_bundle_root_standalone(tmp_path: Path) -> None:
    (tmp_path / "manuscript_methods.md").write_text(GOOD, encoding="utf-8")
    res = GATE.check({"bundle_root": str(tmp_path), "run_stage": "wave6"})
    assert res.status == GateStatus.PASS


def test_g33_resolves_methods_from_manuscript(tmp_path: Path) -> None:
    (tmp_path / "manuscript.md").write_text(
        "# Manuscript\n\n## Introduction\n\nLorem.\n\n" + GOOD + "\n\n## Results\n\nFoo.\n",
        encoding="utf-8",
    )
    res = GATE.check({"bundle_root": str(tmp_path), "run_stage": "wave6"})
    assert res.status == GateStatus.PASS


def test_g33_fail_missing_methods_file(tmp_path: Path) -> None:
    res = GATE.check({"bundle_root": str(tmp_path), "run_stage": "wave6"})
    assert res.status == GateStatus.FAIL
    assert res.block
