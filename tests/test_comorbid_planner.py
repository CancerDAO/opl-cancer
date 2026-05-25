"""Tests for v1.5 P0-6 comorbid planner expansion.

Covers the trigger logic that auto-adds Mark / Mary / Frances / Riad /
Dennis / Heddy when the patient's phenotype matches multi-comorbid /
L4+ / cross-border / active-irAE / cardiac / CKD / polypharmacy
criteria.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from opl_cancer.cli import main
from opl_cancer.plan.comorbid_planner import (
    compute_expansion_triggers,
    maybe_expand_for_comorbid,
)
from opl_cancer.plan.schemas import Task


def _base_skeleton() -> list[Task]:
    return [
        Task(id="t1", expert="rosa", task_package="pathology_interpretation", sub_goal="x"),
        Task(id="t2", expert="bert", task_package="molecular_ngs_interpretation", sub_goal="x"),
        Task(id="t3", expert="rick", task_package="trial_matching", sub_goal="x"),
    ]


def test_empty_profile_fires_no_triggers() -> None:
    tasks, fired = maybe_expand_for_comorbid(_base_skeleton(), {})
    assert len(tasks) == 3
    assert fired == []


def test_active_irae_fires_mark() -> None:
    profile = {"toxicity_history": {"active_immune_related": True}}
    tasks, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    assert any(t.task.expert == "mark" for t in fired)
    assert any(t.name == "active_irae" for t in fired)


def test_text_pattern_active_thyroiditis_fires_mark() -> None:
    profile = {"active_problems": ["active thyroiditis grade 2"]}
    tasks, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    assert any(t.task.expert == "mark" for t in fired)


def test_prior_lines_threshold_fires_frances() -> None:
    profile = {"prior_therapy_lines": 4}
    _, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    assert any(t.task.expert == "frances" for t in fired)


def test_prior_lines_as_list() -> None:
    profile = {"prior_therapy_lines": ["FOLFOX", "FOLFIRI", "irinotecan", "regorafenib"]}
    _, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    assert any(t.task.expert == "frances" for t in fired)


def test_prior_lines_text_pattern_l4() -> None:
    profile = {"concise_summary": "post-L4 mCRC patient"}
    _, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    assert any(t.task.expert == "frances" for t in fired)


def test_polypharmacy_fires_mary() -> None:
    profile = {
        "concurrent_medications": [
            "metformin",
            "irbesartan",
            "clopidogrel",
            "atorvastatin",
        ]
    }
    _, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    assert any(t.task.expert == "mary" and t.name == "polypharmacy" for t in fired)


def test_cardiac_comorbidity_fires_mary() -> None:
    profile = {"comorbidities": ["CAD-PCI 2019", "T2DM"]}
    _, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    assert any(t.task.expert == "mary" and t.name == "cardiac_comorbidity" for t in fired)


def test_lvef_below_threshold_fires_mary() -> None:
    profile = {"lvef_pct": 43}
    _, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    assert any(t.task.expert == "mary" and t.name == "cardiac_comorbidity" for t in fired)


def test_ckd_fires_mary() -> None:
    profile = {"comorbidities": ["CKD stage 3b"]}
    _, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    assert any(t.task.expert == "mary" and t.name == "ckd" for t in fired)


def test_egfr_below_threshold_fires_mary() -> None:
    profile = {"egfr_ml_min": 40}
    _, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    assert any(t.task.expert == "mary" and t.name == "ckd" for t in fired)


def test_china_patient_fires_riad_and_dennis() -> None:
    profile = {"country": "CN"}
    _, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    fired_experts = {f.task.expert for f in fired}
    assert "riad" in fired_experts
    assert "dennis" in fired_experts


def test_beijing_patient_fires_dennis() -> None:
    profile = {"city": "Beijing 朝阳区"}
    _, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    fired_experts = {f.task.expert for f in fired}
    assert "dennis" in fired_experts


def test_imaging_gap_fires_heddy() -> None:
    profile = {"imaging_gaps": ["no post-H3 CT"]}
    _, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    assert any(t.task.expert == "heddy" for t in fired)


def test_elderly_patient_fires_heddy() -> None:
    profile = {"age_years": 75}
    _, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    assert any(t.task.expert == "heddy" for t in fired)


def test_pt_ee62321353_phenotype_fires_full_battery() -> None:
    """The canonical case: 69yo mCRC L4+, KRAS G12C MSS, CKD3b + CAD-PCI
    + active thyroiditis, Beijing-based, with imaging gap.

    The v1.4 silently expanded planner from t1-t9 to t1-t14. This test
    asserts the v1.5 deterministic expansion gets to the same place
    automatically (no silent assistant override).
    """
    profile = {
        "age_years": 69,
        "country": "CN",
        "city": "Beijing 朝阳",
        "prior_therapy_lines": 4,
        "concurrent_medications": ["metformin", "irbesartan", "atorvastatin", "clopidogrel"],
        "comorbidities": ["CAD-PCI 2019", "T2DM", "HTN3", "CKD stage 3b"],
        "lvef_pct": 43,
        "egfr_ml_min": 40,
        "toxicity_history": {"active_immune_related": True},
        "imaging_gaps": ["no post-H3 CT", "no brain baseline MRI"],
    }
    tasks, fired = maybe_expand_for_comorbid(_base_skeleton(), profile)
    fired_experts = {f.task.expert for f in fired}
    for required in ("mark", "mary", "frances", "riad", "dennis", "heddy"):
        assert required in fired_experts, f"missing required trigger expert: {required}"
    # Each fired trigger has a rationale
    for f in fired:
        assert f.rationale, f"trigger {f.name} has empty rationale"


def test_no_duplicate_task_combos() -> None:
    """If baseline already covers (expert, package), expansion skips it."""
    base = [
        Task(id="t1", expert="mark", task_package="irae_rechallenge", sub_goal="x"),
    ]
    profile = {"toxicity_history": {"active_immune_related": True}}
    tasks, fired = maybe_expand_for_comorbid(base, profile)
    # baseline already had mark+irae — expansion should not duplicate
    mark_irae_tasks = [
        t for t in tasks if t.expert == "mark" and t.task_package == "irae_rechallenge"
    ]
    assert len(mark_irae_tasks) == 1


def test_new_task_ids_continue_numbering() -> None:
    """Expansion allocates t10, t11, ... after t9 baseline."""
    base = [
        Task(id=f"t{i}", expert="rosa", task_package="pathology_interpretation", sub_goal=f"task{i}")
        for i in range(1, 10)
    ]
    profile = {"toxicity_history": {"active_immune_related": True}, "country": "CN"}
    tasks, fired = maybe_expand_for_comorbid(base, profile)
    new_ids = [t.id for t in tasks if t.id not in {b.id for b in base}]
    # New IDs should start at t10
    assert new_ids[0] == "t10"


def test_plan_cli_emits_triggers_fired(tmp_path: Path) -> None:
    """End-to-end: plan CLI surfaces the expansion in JSON output."""
    runner = CliRunner()
    patient_dir = tmp_path / "PT_TEST"
    patient_dir.mkdir()
    (patient_dir / "profile.json").write_text(
        json.dumps(
            {
                "country": "CN",
                "prior_therapy_lines": 4,
                "toxicity_history": {"active_immune_related": True},
            }
        ),
        encoding="utf-8",
    )
    r = runner.invoke(
        main,
        [
            "plan",
            "--patient",
            str(patient_dir),
            "--goal",
            "test goal",
            "--run-id",
            "test_run_1",
            "--json",
        ],
    )
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert "comorbid_expansion_triggers_fired" in payload
    fired = payload["comorbid_expansion_triggers_fired"]
    # CN + L4+ + active-irAE → at least mark + frances + riad + dennis fire
    fired_experts = {t["expert"] for t in fired}
    assert "mark" in fired_experts
    assert "frances" in fired_experts
    assert "riad" in fired_experts
    assert "dennis" in fired_experts


def test_plan_cli_handles_missing_profile(tmp_path: Path) -> None:
    """Missing profile.json should not crash — just no triggers fire."""
    runner = CliRunner()
    patient_dir = tmp_path / "PT_TEST"
    patient_dir.mkdir()
    r = runner.invoke(
        main,
        [
            "plan",
            "--patient",
            str(patient_dir),
            "--goal",
            "test goal",
            "--run-id",
            "test_run_2",
            "--json",
        ],
    )
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert payload["comorbid_expansion_triggers_fired"] == []
