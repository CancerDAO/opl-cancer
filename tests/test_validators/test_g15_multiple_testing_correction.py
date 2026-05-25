"""Test G15 multiple-testing-correction gate."""
import json
from pathlib import Path

from opl_cancer.validators.gates.g15_multiple_testing_correction import (
    G15MultipleTestingCorrectionGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


def _write_nb(tmp_path: Path, source: str, name: str = "nb.ipynb") -> Path:
    nb = {
        "cells": [{"cell_type": "code", "source": source}],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p = tmp_path / name
    p.write_text(json.dumps(nb), encoding="utf-8")
    return p


def test_g15_skip_no_notebooks() -> None:
    gate = G15MultipleTestingCorrectionGate()
    r = gate.check({})
    assert r.status == GateStatus.SKIP


def test_g15_pass_with_bh(tmp_path: Path) -> None:
    nb = _write_nb(tmp_path, "from statsmodels.stats.multitest import multipletests\nadj = multipletests(p, method='fdr_bh')")
    gate = G15MultipleTestingCorrectionGate()
    r = gate.check({"notebooks": [str(nb)]})
    assert r.status == GateStatus.PASS


def test_g15_pass_with_bonferroni(tmp_path: Path) -> None:
    nb = _write_nb(tmp_path, "p_adj = p * n_tests  # Bonferroni")
    gate = G15MultipleTestingCorrectionGate()
    r = gate.check({"notebooks": [str(nb)]})
    assert r.status == GateStatus.PASS


def test_g15_fail_no_correction(tmp_path: Path) -> None:
    nb = _write_nb(tmp_path, "p_value = stats.ttest_ind(a, b).pvalue\nprint(p_value)")
    gate = G15MultipleTestingCorrectionGate()
    r = gate.check({"notebooks": [str(nb)]})
    assert r.status == GateStatus.FAIL
    assert r.block is True
