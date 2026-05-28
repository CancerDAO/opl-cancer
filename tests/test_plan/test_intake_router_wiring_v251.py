"""v2.5.1 B2 — route_intake must be invoked by cli.py plan + wave1_runner.

Through v2.5.0 ``route_intake`` was defined but never called by any wave
runner, planner, or CLI command. This test pair confirms the wiring:
the literal session-c3195b66 question, when fed through ``opl plan``,
must produce a plan.json that:

1. Includes ``unknown_task_intake`` as one of the task packages, AND
2. Surfaces the composed method-DAG nodes (``kaplan_meier`` +
   ``conformal_prediction``) under the plan's ``method_dag`` field.
"""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from opl_cancer.cli import main as cli_main

C3195B66_QUESTION = (
    "你会自动下载相关的公共数据库，并进行机器学习建模，"
    "找到最优的模型和参数，然后预测我的预后么"
)


def _make_patient(tmp_path: Path) -> Path:
    pdir = tmp_path / "patients" / "p1"
    pdir.mkdir(parents=True)
    # Minimal profile — schema_validator runs only if patient_id_hash present.
    (pdir / "profile.json").write_text("{}", encoding="utf-8")
    return pdir


def test_cli_plan_routes_c3195b66_through_intake_router(tmp_path: Path) -> None:
    """RELEASE-GATING (B2): the literal c3195b66 AutoML question must
    surface unknown_task_intake + the composed method DAG in plan.json."""
    pdir = _make_patient(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        [
            "plan",
            "--patient",
            str(pdir),
            "--goal",
            C3195B66_QUESTION,
            "--run-id",
            "r1",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    plan_path = pdir / "triggers" / "r1" / "plan.json"
    assert plan_path.exists()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    # B2 first assertion: unknown_task_intake is in the task-package list.
    pkgs = [t["task_package"] for t in plan["tasks"]]
    assert "unknown_task_intake" in pkgs, pkgs

    # B2 second assertion: method_dag carries kaplan_meier + conformal_prediction.
    method_dag = plan.get("method_dag", [])
    method_ids = {node["id"] for node in method_dag}
    assert "kaplan_meier" in method_ids, method_ids
    assert "conformal_prediction" in method_ids, method_ids


def test_cli_plan_records_intake_route_in_emit_payload(tmp_path: Path) -> None:
    """B2 — the CLI's emitted JSON surfaces the route summary so the
    SKILL main thread can render the acknowledgement + decline reasons."""
    pdir = _make_patient(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        [
            "plan",
            "--patient",
            str(pdir),
            "--goal",
            C3195B66_QUESTION,
            "--run-id",
            "r2",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    intake = payload.get("intake_route")
    assert intake is not None, payload
    assert intake["matched_task_package"] == "unknown_task_intake"
    assert intake.get("acknowledgement")
    assert intake.get("decline_reasons")


def test_cli_plan_known_question_goes_to_known_package(tmp_path: Path) -> None:
    """Counter-test: a question that maps to a known package should NOT
    pollute the plan with unknown_task_intake."""
    pdir = _make_patient(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        [
            "plan",
            "--patient",
            str(pdir),
            "--goal",
            "please run an ACMG classification on the germline BRCA2 variant",
            "--run-id",
            "r3",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    plan = json.loads((pdir / "triggers" / "r3" / "plan.json").read_text())
    pkgs = [t["task_package"] for t in plan["tasks"]]
    # ACMG matched as a known task package, so the synthetic
    # `unknown_task_intake` task is NOT injected into the skeleton.
    assert "unknown_task_intake" not in pkgs, pkgs
    # The intake route on the plan payload should still surface ACMG.
    intake = plan.get("intake_route", {})
    assert intake.get("matched_task_package") == "acmg_germline_classification"


def test_wave1_runner_invokes_route_intake_on_build_plan() -> None:
    """B2 — Wave1Runner._build_plan must consult route_intake; for the
    c3195b66 question, the resulting plan_dict must include
    unknown_task_intake AND the composed method DAG."""
    from opl_cancer.glue.wave1_runner import Wave1Runner

    # Patch-friendly: the production planner is async + needs an LLM client.
    # We exercise the public `_apply_intake_router` helper directly.
    plan_dict = {
        "experts": ["aviv", "bert", "iain"],
        "tasks": [
            {
                "id": "t1",
                "expert": "aviv",
                "task_package": "hypothesis_generation",
                "sub_goal": "baseline",
            }
        ],
    }
    merged = Wave1Runner._apply_intake_router(plan_dict, C3195B66_QUESTION)
    pkgs = [t["task_package"] for t in merged["tasks"]]
    assert "unknown_task_intake" in pkgs, pkgs
    method_dag = merged.get("method_dag", [])
    ids = {n["id"] for n in method_dag}
    assert "kaplan_meier" in ids
    assert "conformal_prediction" in ids
