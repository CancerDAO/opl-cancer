"""Test G16 batch-effect-declared gate."""
import json
from pathlib import Path

from opl_cancer.validators.gates.g16_batch_effect_declared import (
    G16BatchEffectDeclaredGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


def _write_nb(tmp_path: Path, source: str) -> Path:
    nb = {
        "cells": [{"cell_type": "code", "source": source}],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p = tmp_path / "nb.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")
    return p


def test_g16_skip_non_bioinformatics() -> None:
    gate = G16BatchEffectDeclaredGate()
    r = gate.check({"task_type": "clinical_judgment"})
    assert r.status == GateStatus.SKIP


def test_g16_pass_prompt_and_notebook(tmp_path: Path) -> None:
    nb = _write_nb(tmp_path, "from combat import ComBat\nadj = ComBat(X, batch=meta['batch'])")
    gate = G16BatchEffectDeclaredGate()
    claim = {
        "task_type": "bioinformatics_data_analysis",
        "task_prompt": "Account for the batch variable from each sequencing center.",
        "notebooks": [str(nb)],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g16_fail_both_silent(tmp_path: Path) -> None:
    nb = _write_nb(tmp_path, "X = pd.read_csv('x.csv')\nmodel.fit(X)")
    gate = G16BatchEffectDeclaredGate()
    claim = {
        "task_type": "bioinformatics_data_analysis",
        "task_prompt": "Compute differential expression.",
        "notebooks": [str(nb)],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g16_warn_only_notebook(tmp_path: Path) -> None:
    nb = _write_nb(tmp_path, "removeBatchEffect(X, batch=b)")
    gate = G16BatchEffectDeclaredGate()
    claim = {
        "task_type": "bioinformatics_data_analysis",
        "task_prompt": "Just run DE.",
        "notebooks": [str(nb)],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False
