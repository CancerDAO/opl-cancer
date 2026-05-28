"""v2.3 P2-#17 / P2-#21 — prior run ingestion + patient value hierarchy."""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.plan.prior_run_ingestion import (
    ingest_prior_runs,
    latest_prior_run_id,
    patient_value_hierarchy_weights,
)


def _seed_prior_run(patient_dir: Path, run_id: str, text: str) -> None:
    d = patient_dir / "runs" / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "chair_final_report.md").write_text(text, encoding="utf-8")


def test_ingest_empty_when_no_runs_dir(tmp_path: Path) -> None:
    assert ingest_prior_runs(tmp_path) == []


def test_ingest_collects_one_prior_run(tmp_path: Path) -> None:
    _seed_prior_run(
        tmp_path,
        "2024-12-mtb",
        "# Chair report\n\n## Summary\n\nMSI-H tumor [PMID:32179615].\n",
    )
    summaries = ingest_prior_runs(tmp_path)
    assert len(summaries) == 1
    s = summaries[0]
    assert s.run_id == "2024-12-mtb"
    assert "Summary" in s.headings
    assert "32179615" in s.cited_pmids


def test_ingest_excludes_current_run(tmp_path: Path) -> None:
    _seed_prior_run(tmp_path, "prior-1", "# r1\n")
    _seed_prior_run(tmp_path, "current", "# r2\n")
    summaries = ingest_prior_runs(tmp_path, current_run_id="current")
    ids = [s.run_id for s in summaries]
    assert "current" not in ids
    assert "prior-1" in ids


def test_latest_prior_run_id(tmp_path: Path) -> None:
    _seed_prior_run(tmp_path, "2024-12-mtb", "# r1\n")
    _seed_prior_run(tmp_path, "2025-03-mtb", "# r2\n")
    rid = latest_prior_run_id(tmp_path)
    assert rid == "2025-03-mtb"


def test_latest_prior_run_id_none(tmp_path: Path) -> None:
    assert latest_prior_run_id(tmp_path) is None


def test_patient_value_hierarchy_extracted() -> None:
    profile = {
        "patient_value_hierarchy": [
            "survival_extension", "quality_of_life", "minimise_iv"
        ]
    }
    assert patient_value_hierarchy_weights(profile) == [
        "survival_extension", "quality_of_life", "minimise_iv"
    ]


def test_patient_value_hierarchy_legacy_field() -> None:
    profile = {"value_hierarchy": ["a", "b"]}
    assert patient_value_hierarchy_weights(profile) == ["a", "b"]


def test_patient_value_hierarchy_empty_when_missing() -> None:
    assert patient_value_hierarchy_weights({}) == []
    # Wrong type defends:
    assert patient_value_hierarchy_weights({"patient_value_hierarchy": "string"}) == []
