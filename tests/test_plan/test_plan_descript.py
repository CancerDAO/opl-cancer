"""De-script (ADR-0040): `opl-cancer plan` no longer hardcodes a 9-task skeleton.

The expert team + task DAG come from the host-LLM-composed agenda (--agenda,
produced by goal_backward_planner.md). Python only adds the deterministic comorbid
red-line FLOOR on top and records floor_required for G55 to verify the agenda
covers it. Without --agenda the plan is floor-only.
"""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from opl_cancer.cli import main


def _patient(tmp_path: Path, code: str, profile: dict) -> Path:
    p = tmp_path / "patients" / code
    p.mkdir(parents=True)
    (p / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
    return p


def test_plan_with_agenda_uses_host_team(tmp_path: Path) -> None:
    patient = _patient(tmp_path, "PT-A", {"patient_id_hash": "x"})
    agenda = tmp_path / "agenda.json"
    agenda.write_text(json.dumps({"tasks": [
        {"id": "t1", "expert": "rosa", "task_package": "pathology_interpretation",
         "sub_goal": "read path", "wave": 1},
        {"id": "t2", "expert": "bert", "task_package": "molecular_ngs_interpretation",
         "sub_goal": "ngs", "wave": 1},
        {"id": "t3", "expert": "aviv", "task_package": "hypothesis_generation",
         "sub_goal": "hyp", "dependencies": ["t1", "t2"], "wave": 2},
    ]}), encoding="utf-8")
    r = CliRunner().invoke(main, [
        "plan", "--patient", str(patient), "--goal", "next line",
        "--run-id", "r1", "--agenda", str(agenda), "--json",
    ])
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert payload["ok"] is True
    assert set(payload["planned_experts"]) >= {"rosa", "bert", "aviv"}
    plan = json.loads((patient / "triggers" / "r1" / "plan.json").read_text(encoding="utf-8"))
    assert {t["id"] for t in plan["tasks"]} >= {"t1", "t2", "t3"}
    # waves are contiguous 1..N (host wave hints remapped)
    wave_nums = sorted(w["wave_number"] for w in plan["waves"])
    assert wave_nums == list(range(1, len(wave_nums) + 1))


def test_plan_without_agenda_is_floor_only(tmp_path: Path) -> None:
    # active irAE → the comorbid red-line fires Mark; no hardcoded base team.
    patient = _patient(tmp_path, "PT-B", {
        "patient_id_hash": "x",
        "toxicity_history": {"active_immune_related": True},
    })
    r = CliRunner().invoke(main, [
        "plan", "--patient", str(patient), "--goal", "g", "--run-id", "r1", "--json",
    ])
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert payload["ok"] is True
    # the comorbid red-line is present; the old skeleton experts are NOT auto-added
    assert "mark" in payload["planned_experts"]
    assert "rosa" not in payload["planned_experts"]
    fired_experts = {t["expert"] for t in payload["comorbid_expansion_triggers_fired"]}
    assert "mark" in fired_experts


def test_plan_records_floor_required_subset_of_planned(tmp_path: Path) -> None:
    """G55 invariant: floor_required (comorbid red-line) is recorded and is a
    subset of planned_experts (the floor is added by construction, never dropped)."""
    patient = _patient(tmp_path, "PT-C", {
        "patient_id_hash": "x",
        "toxicity_history": {"active_immune_related": True},
    })
    agenda = tmp_path / "agenda.json"
    agenda.write_text(json.dumps({"tasks": [
        {"id": "t1", "expert": "bert", "task_package": "molecular_ngs_interpretation",
         "sub_goal": "ngs", "wave": 1},
    ]}), encoding="utf-8")
    r = CliRunner().invoke(main, [
        "plan", "--patient", str(patient), "--goal", "g",
        "--run-id", "r1", "--agenda", str(agenda), "--json",
    ])
    assert r.exit_code == 0, r.output
    plan = json.loads((patient / "triggers" / "r1" / "plan.json").read_text(encoding="utf-8"))
    assert plan["floor_required"], "comorbid red-line must populate floor_required"
    assert "mark" in plan["floor_required"]
    assert set(plan["floor_required"]) <= set(plan["planned_experts"])
