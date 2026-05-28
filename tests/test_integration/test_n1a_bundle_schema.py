"""v2.3 ADR-0023 — `.n1a` bundle writer + schema validation tests.

Validates the bundle writer end-to-end on synthetic Wave 6 trigger
directories. Per spec §5.6: at least three sample bundles must validate
against `schemas/n1a_bundle.v0.1.schema.json`.
"""
from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from opl_cancer.delivery.n1a_bundle_writer import (
    BANNER_METHODOLOGY_DEMO,
    BANNER_REFERENCE_CASE,
    BANNER_SYNTHETIC,
    BundleWriteError,
    N1ABundleWriter,
    write_bundle,
)


GOOD_AUTHORSHIP = """\
# AI Authorship Disclosure

No human author beyond the patient and supervising clinician was involved.

## Contributions

| Expert | Role |
| --- | --- |
| Iain | Wave 1 retrieval |
"""

GOOD_REPRO = """\
# Reproducibility

## Data sources

- TCGA-LUAD, tier: public
- 007-zhiqiang EHR, tier: patient-private

## Software

- opl-cancer v2.3.0
"""

GOOD_MANUSCRIPT = """\
# Manuscript

## Introduction

[BACKGROUND] N=1 case reports for rare cancers are increasingly relevant.

Pembrolizumab is approved for MSI-H tumors [PMID:32179615].

## Methods

This is a single-subject (N=1) case report.

## Results

The patient's MSI status was MSI-H [integrator:msisensor_pro run_id:abc123].
"""

GOOD_HENRY = json.dumps({"audit_version": "v2.3", "gates_run": 33, "status": "pass"})


def _seed_trigger(trigger_dir: Path) -> None:
    """Populate trigger_dir with the minimum required Wave 6 artifacts."""
    trigger_dir.mkdir(parents=True, exist_ok=True)
    (trigger_dir / "manuscript.md").write_text(GOOD_MANUSCRIPT, encoding="utf-8")
    (trigger_dir / "ai_authorship_disclosure.md").write_text(
        GOOD_AUTHORSHIP, encoding="utf-8"
    )
    (trigger_dir / "reproducibility.md").write_text(GOOD_REPRO, encoding="utf-8")
    (trigger_dir / "HENRY_AUDIT.json").write_text(GOOD_HENRY, encoding="utf-8")
    # Optional: extras
    (trigger_dir / "ethics_declaration.md").write_text(
        "# Ethics\n\nFounder mode; patient consent on file.\n", encoding="utf-8"
    )
    (trigger_dir / "world_unknown_appendix.md").write_text(
        "# Speculative candidates\n\nRedacted — see HENRY_AUDIT.\n", encoding="utf-8"
    )
    (trigger_dir / "references.bib").write_text(
        "@article{kim2020,\n  title = {Pembrolizumab MSI},\n  year = {2020}\n}\n",
        encoding="utf-8",
    )
    (trigger_dir / "provenance.jsonl").write_text(
        '{"claim": "MSI-H", "wave": 3, "pmid": "32179615"}\n', encoding="utf-8"
    )
    # Add a figure pair so the bundle exercises figures/
    figures = trigger_dir / "figures"
    figures.mkdir(exist_ok=True)
    (figures / "fig_1.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (figures / "fig_1.py").write_text(
        "# reproducer\nrandom_seed = 42\nprint('fig 1')\n", encoding="utf-8"
    )


def test_bundle_writes_real_patient(tmp_path: Path) -> None:
    trigger = tmp_path / "patients" / "007" / "triggers" / "abc"
    _seed_trigger(trigger)

    res = write_bundle(
        trigger_dir=trigger,
        patient_code="007-zhiqiang",
        data_source="real_patient",
        opl_version="2.3.0",
        run_id="abc",
    )
    assert res.zip_path.is_file()
    assert res.manifest_path.is_file()
    manifest = res.manifest
    assert manifest["schema_version"] == "0.1"
    assert manifest["data_source"] == "real_patient"
    assert manifest["patient_id_hash"]  # non-empty
    # banner is None / absent for real_patient
    assert "banner" not in manifest or manifest["banner"] is None
    # All sha256 entries are 64 hex chars
    for h in manifest["sha256s"].values():
        assert len(h) == 64

    # Zip contains the manifest + every file in file_index
    with zipfile.ZipFile(res.zip_path) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        for f in manifest["file_index"]:
            assert f in names


def test_bundle_writes_reference_case_with_banner(tmp_path: Path) -> None:
    trigger = tmp_path / "patients" / "riaz" / "triggers" / "ref"
    _seed_trigger(trigger)

    res = write_bundle(
        trigger_dir=trigger,
        patient_code="riaz-melanoma-ref",
        data_source="reference_case",
        opl_version="2.3.0",
    )
    assert res.manifest["banner"] == BANNER_REFERENCE_CASE
    # The banner must have been injected into manuscript.md
    ms_text = (trigger / "manuscript.md").read_text(encoding="utf-8")
    assert BANNER_REFERENCE_CASE in ms_text


def test_bundle_writes_methodology_demo_banner(tmp_path: Path) -> None:
    trigger = tmp_path / "patients" / "demo" / "triggers" / "x"
    _seed_trigger(trigger)
    res = write_bundle(
        trigger_dir=trigger,
        patient_code="demo-001",
        data_source="methodology_demo",
    )
    assert res.manifest["banner"] == BANNER_METHODOLOGY_DEMO


def test_bundle_writes_synthetic_banner(tmp_path: Path) -> None:
    trigger = tmp_path / "patients" / "synth" / "triggers" / "x"
    _seed_trigger(trigger)
    res = write_bundle(
        trigger_dir=trigger,
        patient_code="synth-001",
        data_source="synthetic",
    )
    assert res.manifest["banner"] == BANNER_SYNTHETIC


def test_bundle_fails_when_required_missing(tmp_path: Path) -> None:
    trigger = tmp_path / "patients" / "missing" / "triggers" / "x"
    trigger.mkdir(parents=True)
    (trigger / "manuscript.md").write_text("stub", encoding="utf-8")
    # missing the other 3 required files
    with pytest.raises(BundleWriteError):
        write_bundle(trigger_dir=trigger, patient_code="missing")


def test_bundle_includes_cost_summary(tmp_path: Path) -> None:
    trigger = tmp_path / "t"
    _seed_trigger(trigger)
    cost = {
        "total_usd": 1.23,
        "tokens_input": 1000,
        "tokens_output": 2000,
        "by_model": [{"model": "claude-opus-4-7", "calls": 3, "usd": 1.23}],
    }
    res = write_bundle(
        trigger_dir=trigger,
        patient_code="p",
        cost_summary=cost,
    )
    assert res.manifest["cost_summary"]["total_usd"] == 1.23


def test_bundle_includes_extends_prior_run(tmp_path: Path) -> None:
    trigger = tmp_path / "t"
    _seed_trigger(trigger)
    res = write_bundle(
        trigger_dir=trigger,
        patient_code="p",
        extends_prior_run="prior-run-1234",
    )
    assert res.manifest["extends_prior_run"] == "prior-run-1234"


def test_bundle_patient_id_hash_stable(tmp_path: Path) -> None:
    trigger = tmp_path / "t"
    _seed_trigger(trigger)
    r1 = write_bundle(trigger_dir=trigger, patient_code="patient-foo")
    r2 = write_bundle(trigger_dir=trigger, patient_code="patient-foo")
    assert r1.manifest["patient_id_hash"] == r2.manifest["patient_id_hash"]
    r3 = write_bundle(trigger_dir=trigger, patient_code="patient-bar")
    assert r3.manifest["patient_id_hash"] != r1.manifest["patient_id_hash"]


def test_three_sample_bundles_all_schema_valid(tmp_path: Path) -> None:
    """Spec §5.6: validate ≥3 sample bundles against schema."""
    # If we got this far without raising BundleWriteError, the writer's
    # internal validation succeeded. But also re-validate externally with
    # jsonschema for belt-and-braces.
    import jsonschema  # type: ignore[import-not-found]

    from opl_cancer.delivery.n1a_bundle_writer import _load_schema  # type: ignore[attr-defined]

    schema = _load_schema()
    samples = [
        ("real_patient", "real-001"),
        ("reference_case", "ref-002"),
        ("methodology_demo", "demo-003"),
        ("synthetic", "synth-004"),
    ]
    for source, pcode in samples:
        trigger = tmp_path / f"trigger-{pcode}"
        _seed_trigger(trigger)
        res = write_bundle(
            trigger_dir=trigger,
            patient_code=pcode,
            data_source=source,
        )
        # Will raise if invalid.
        jsonschema.validate(instance=res.manifest, schema=schema)
