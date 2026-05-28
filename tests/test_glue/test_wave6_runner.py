"""v2.3 ADR-0023 — Wave 6 runner unit + integration tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opl_cancer.glue.wave6_runner import (
    Wave6Failure,
    Wave6PrerequisiteError,
    Wave6Runner,
    run_wave6,
)


# ── fixtures ──────────────────────────────────────────────────────────


GOOD_MS = """\
# Manuscript

## Abstract

**Background.** [BACKGROUND] N=1 case reports are increasingly relevant for rare cancers.

**Methods.** This is a single-subject (N=1) case report run via OPL v2.3.0 [integrator:opl_runtime run_id:abc].

**Results.** Pembrolizumab demonstrates tissue-agnostic efficacy in MSI-H tumors [PMID:32179615].

**Conclusions.** The patient and clinician retain sole decision authority [BACKGROUND].

## Methods

This is a single-subject (N=1) case report. Patient consent on file [integrator:consent run_id:abc].

## Results

The patient's MSI status was MSI-H [integrator:msisensor_pro run_id:abc].
"""

GOOD_AUTHORSHIP = """\
# AI Authorship Disclosure

No human author beyond the patient and supervising clinician was involved.

## Contributions

| Expert | Role |
| --- | --- |
| Iain | Wave 1 retrieval |
| Aviv | Wave 3 statistics |
| Henry | Wave 6 audit |
"""

GOOD_REPRO = """\
# Reproducibility

## Data sources

- TCGA-LUAD, tier: public
- 007-zhiqiang EHR, tier: patient-private

## Software

- opl-cancer v2.3.0
"""

GOOD_HENRY_PRE = json.dumps({
    "audit_version": "v2.2",
    "gates_run": 28,
    "status": "pass",
})


def _seed_wave5(patient_dir: Path, run_id: str) -> Path:
    run_dir = patient_dir / "triggers" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "patient_plain_brief.md").write_text(
        "# Plain brief\n\nFor the patient.\n", encoding="utf-8"
    )
    (run_dir / "patient_pi_brief.md").write_text(
        "# PI brief\n\nFor the clinician.\n", encoding="utf-8"
    )
    return run_dir


def _seed_full_artifacts(run_dir: Path) -> None:
    (run_dir / "manuscript.md").write_text(GOOD_MS, encoding="utf-8")
    (run_dir / "manuscript_methods.md").write_text(
        "## Methods\n\nThis is a single-subject (N=1) case report.\n",
        encoding="utf-8",
    )
    (run_dir / "ai_authorship_disclosure.md").write_text(
        GOOD_AUTHORSHIP, encoding="utf-8"
    )
    (run_dir / "reproducibility.md").write_text(GOOD_REPRO, encoding="utf-8")
    (run_dir / "HENRY_AUDIT.json").write_text(GOOD_HENRY_PRE, encoding="utf-8")
    # figures + reproducer for G31
    figs = run_dir / "figures"
    figs.mkdir(exist_ok=True)
    (figs / "fig_1.png").write_bytes(b"\x89PNG\r\nfake")
    (figs / "fig_1.py").write_text(
        "random_seed = 42\nprint('fig 1')\n", encoding="utf-8"
    )


# ── tests ─────────────────────────────────────────────────────────────


def test_wave6_refuses_when_wave5_missing(tmp_path: Path) -> None:
    """Wave 6 must refuse if Wave 5 has not shipped both briefs."""
    patient_dir = tmp_path / "patients" / "007"
    run_dir = patient_dir / "triggers" / "abc"
    run_dir.mkdir(parents=True)
    # Only one of the two required Wave 5 outputs
    (run_dir / "patient_plain_brief.md").write_text("stub", encoding="utf-8")

    with pytest.raises(Wave6PrerequisiteError):
        run_wave6(
            patient_dir=patient_dir,
            run_id="abc",
            patient_code="007-test",
            mode="final",
        )


def test_wave6_dry_run_returns_plan(tmp_path: Path) -> None:
    patient_dir = tmp_path / "patients" / "007"
    _seed_wave5(patient_dir, "abc")
    res = run_wave6(
        patient_dir=patient_dir,
        run_id="abc",
        patient_code="007-test",
        mode="dry_run",
    )
    assert res["status"] == "dry_run"
    assert res["mode"] == "dry_run"
    assert any("scaffold" in s for s in res["planned_steps"])


def test_wave6_final_passes_with_full_artifacts(tmp_path: Path) -> None:
    """Happy path: Wave 5 done, all required Wave 6 artifacts present, all
    gates pass, bundle written."""
    patient_dir = tmp_path / "patients" / "007"
    run_dir = _seed_wave5(patient_dir, "abc")
    _seed_full_artifacts(run_dir)

    res = run_wave6(
        patient_dir=patient_dir,
        run_id="abc",
        patient_code="007-test",
        mode="final",
        data_source="real_patient",
    )
    assert res["status"] == "ok"
    assert Path(res["zip_path"]).is_file()
    assert Path(res["manifest_path"]).is_file()
    # Henry audit was updated
    audit = json.loads(Path(res["henry_audit_path"]).read_text())
    assert audit["audit_version"] == "v2.3"
    assert audit["gates_run"] == 33
    assert audit["status"] == "pass"
    assert audit["wave6_any_block"] is False


def test_wave6_final_blocks_on_gate_failure(tmp_path: Path) -> None:
    """G33 will fail if methods text omits N=1 — bundle must NOT ship."""
    patient_dir = tmp_path / "patients" / "007"
    run_dir = _seed_wave5(patient_dir, "abc")
    _seed_full_artifacts(run_dir)
    # Corrupt the methods file by removing the N=1 declaration
    (run_dir / "manuscript_methods.md").write_text(
        "## Methods\n\nWe ran the OPL pipeline.\n", encoding="utf-8"
    )
    # Also corrupt manuscript.md so its embedded methods doesn't save us
    (run_dir / "manuscript.md").write_text(
        "# Manuscript\n\n## Methods\n\nWe ran OPL on a cohort retrospective study.\n"
        "\n## Results\n\nFoo [PMID:32179615].\n",
        encoding="utf-8",
    )

    with pytest.raises(Wave6Failure):
        run_wave6(
            patient_dir=patient_dir,
            run_id="abc",
            patient_code="007-test",
            mode="final",
        )


def test_wave6_draft_mode_scaffolds_missing(tmp_path: Path) -> None:
    """Draft mode scaffolds stubs for missing artifacts; gates may fail
    but bundle still emits."""
    patient_dir = tmp_path / "patients" / "draft"
    _seed_wave5(patient_dir, "x")
    # NO Wave 6 artifacts — draft mode must create stubs
    res = run_wave6(
        patient_dir=patient_dir,
        run_id="x",
        patient_code="draft-001",
        mode="draft",
        data_source="methodology_demo",
    )
    assert res["status"] == "ok"
    # The scaffolded files include the required ones at minimum
    assert "manuscript.md" in res["scaffolded_in_draft"]
    assert "ai_authorship_disclosure.md" in res["scaffolded_in_draft"]
    # Bundle was written
    assert Path(res["zip_path"]).is_file()


def test_wave6_extends_prior_run_auto_detect(tmp_path: Path) -> None:
    """P2-#17: prior chair_final_report.md under runs/ is auto-detected."""
    patient_dir = tmp_path / "patients" / "p"
    run_dir = _seed_wave5(patient_dir, "abc")
    _seed_full_artifacts(run_dir)
    # Plant a prior run
    prior_runs = patient_dir / "runs" / "prior-2024-12"
    prior_runs.mkdir(parents=True)
    (prior_runs / "chair_final_report.md").write_text(
        "# prior MTB final report\n", encoding="utf-8"
    )

    res = run_wave6(
        patient_dir=patient_dir,
        run_id="abc",
        patient_code="p",
        mode="final",
    )
    assert res["extends_prior_run"] == "prior-2024-12"


def test_wave6_extends_prior_run_explicit_overrides(tmp_path: Path) -> None:
    """Explicit extends_prior_run wins over auto-detect."""
    patient_dir = tmp_path / "patients" / "p"
    run_dir = _seed_wave5(patient_dir, "abc")
    _seed_full_artifacts(run_dir)
    prior_runs = patient_dir / "runs" / "auto-detected"
    prior_runs.mkdir(parents=True)
    (prior_runs / "chair_final_report.md").write_text("p", encoding="utf-8")

    res = run_wave6(
        patient_dir=patient_dir,
        run_id="abc",
        patient_code="p",
        mode="final",
        extends_prior_run="explicit-run-id",
    )
    assert res["extends_prior_run"] == "explicit-run-id"


def test_wave6_cost_summary_included(tmp_path: Path) -> None:
    """P2-#20: cost_log.jsonl aggregated into manifest cost_summary."""
    patient_dir = tmp_path / "patients" / "p"
    run_dir = _seed_wave5(patient_dir, "abc")
    _seed_full_artifacts(run_dir)
    (run_dir / "cost_log.jsonl").write_text(
        json.dumps({
            "model": "claude-opus-4-7",
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "usd_at_time": 0.05,
            "wave": "6",
            "expert": "iain",
        }) + "\n",
        encoding="utf-8",
    )

    res = run_wave6(
        patient_dir=patient_dir,
        run_id="abc",
        patient_code="p",
        mode="final",
    )
    assert res["cost_summary"] is not None
    assert res["cost_summary"]["total_usd"] == 0.05


def test_wave6_reference_case_data_source(tmp_path: Path) -> None:
    """Reference case forces banner injection into manuscript.md."""
    patient_dir = tmp_path / "patients" / "riaz"
    run_dir = _seed_wave5(patient_dir, "ref")
    _seed_full_artifacts(run_dir)

    res = run_wave6(
        patient_dir=patient_dir,
        run_id="ref",
        patient_code="riaz-melanoma",
        mode="final",
        data_source="reference_case",
    )
    assert res["status"] == "ok"
    # Banner present in manifest
    manifest = json.loads(Path(res["manifest_path"]).read_text())
    assert "REFERENCE CASE" in manifest["banner"]
    # Banner present in manuscript.md
    ms = (run_dir / "manuscript.md").read_text(encoding="utf-8")
    assert "REFERENCE CASE" in ms


def test_wave6_rollback_on_bundle_failure(tmp_path: Path) -> None:
    """If bundle writer fails (e.g. missing required file), rollback fires."""
    patient_dir = tmp_path / "patients" / "fail"
    run_dir = _seed_wave5(patient_dir, "x")
    # Provide manuscript.md + auth disclosure but NOT reproducibility.md.
    (run_dir / "manuscript.md").write_text(GOOD_MS, encoding="utf-8")
    (run_dir / "ai_authorship_disclosure.md").write_text(
        GOOD_AUTHORSHIP, encoding="utf-8"
    )
    (run_dir / "HENRY_AUDIT.json").write_text(GOOD_HENRY_PRE, encoding="utf-8")

    with pytest.raises(Exception):  # noqa: PT011 — multiple subtypes possible
        run_wave6(
            patient_dir=patient_dir,
            run_id="x",
            patient_code="fail-test",
            mode="final",
        )
