from __future__ import annotations

import tomllib
from pathlib import Path

from opl_cancer.mcp import session_ops
from opl_cancer.mcp.server import TOOL_NAMES


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_session_ops_events_and_checkpoint(tmp_path: Path) -> None:
    patient = tmp_path / "P"
    patient.mkdir()

    emitted = session_ops.events_append(
        patient,
        "r1",
        "operator.note",
        phase="planning",
        payload={"note": "ready"},
    )
    assert emitted["ok"] is True

    events = session_ops.events_list(patient, "r1")
    assert events["summary"]["count"] == 1
    assert events["events"][0]["event_type"] == "operator.note"

    written = session_ops.checkpoint_write(
        patient,
        "r1",
        phase="planning",
        reason="waiting for agenda",
        payload={"next": "plan"},
    )
    assert written["checkpoint"]["payload"]["next"] == "plan"
    read = session_ops.checkpoint_read(patient, "r1")
    assert read["checkpoint"]["reason"] == "waiting for agenda"


def test_session_ops_observe_and_validate(tmp_path: Path) -> None:
    patient = tmp_path / "P"
    patient.mkdir()
    session_ops.events_append(patient, "r1", "operator.note")

    observed = session_ops.observe(patient, "r1")
    assert observed["events"]["count"] == 1

    validated = session_ops.validate(patient, "r1")
    assert validated["run_id"] == "r1"
    assert "problems" in validated


def test_session_ops_recovery_plan(tmp_path: Path) -> None:
    patient = tmp_path / "P"
    patient.mkdir()

    recovered = session_ops.recovery_plan(patient, "r1")
    assert recovered["schema"] == "opl.recovery_plan.v1"
    assert recovered["status"] == "blocked"
    assert recovered["next_actions"][0]["code"] == "check_run_id_or_plan"


def test_mcp_tool_names_are_stable() -> None:
    assert set(TOOL_NAMES) == {
        "observe",
        "validate",
        "events_list",
        "events_append",
        "checkpoint_read",
        "checkpoint_write",
        "recovery_plan",
        "integrator_plugins",
        "task_capabilities",
        "release_eval",
    }


def test_pyproject_registers_optional_mcp_entrypoint() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "mcp" in data["project"]["optional-dependencies"]
    assert data["project"]["scripts"]["opl-cancer-mcp"] == "opl_cancer.mcp.server:run"


def test_session_ops_integrator_plugins_inventory() -> None:
    payload = session_ops.integrator_plugins()
    names = {row["name"] for row in payload["integrators"]}
    assert {"pubmed", "opentargets", "clinicaltrials", "cbioportal", "oncokb"} <= names
    assert payload["entry_point_group"] == "opl_cancer.integrators"


def test_session_ops_task_capabilities_inventory() -> None:
    payload = session_ops.task_capabilities()
    capabilities = {row["task_package"]: row for row in payload["capabilities"]}
    assert payload["ok"] is True
    assert payload["summary"]["count"] == 78
    assert capabilities["target_synergy_emergent"]["owners"] == ["maya"]
    assert capabilities["undrugged_target_design"]["owners"] == ["julius"]


def test_session_ops_release_eval() -> None:
    payload = session_ops.release_eval()
    assert payload["ok"] is True
    assert payload["schema"] == "opl.release_golden_eval.v1"
    assert payload["summary"]["errors"] == 0
