"""v2.5.1 B5 — verify_upstream_artifacts precondition + opl deliver CLI wiring."""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from opl_cancer.cli import main
from opl_cancer.glue.delivery_runner import verify_upstream_artifacts


def test_verify_upstream_artifacts_reports_all_missing(tmp_path: Path) -> None:
    missing = verify_upstream_artifacts(tmp_path)
    # Empty dir — plan + wave1 + wave2/3/4 evidence ALL flagged.
    text = "\n".join(missing)
    assert "plan" in text
    assert "wave1_expert_reports" in text
    assert "wave2_hypotheses.json" in text or "wave2/3/4 evidence" in text


def test_verify_upstream_artifacts_passes_when_corpus_present(tmp_path: Path) -> None:
    (tmp_path / "plan.json").write_text("{}", encoding="utf-8")
    w1 = tmp_path / "tasks" / "w1_demo"
    w1.mkdir(parents=True)
    (w1 / "report.md").write_text("# r\n", encoding="utf-8")
    (tmp_path / "wave2_hypotheses.json").write_text("{}", encoding="utf-8")
    assert verify_upstream_artifacts(tmp_path) == []


def test_cli_deliver_refuses_when_upstream_missing(tmp_path: Path) -> None:
    """opl deliver must exit non-zero with structured payload when Wave 1-5
    artifacts are absent (B5)."""
    patient_dir = tmp_path / "patients" / "demo"
    (patient_dir / "triggers" / "run-1").mkdir(parents=True)
    runner = CliRunner()
    res = runner.invoke(
        main,
        [
            "deliver",
            "--patient",
            str(patient_dir),
            "--run-id",
            "run-1",
            "--json",
        ],
    )
    assert res.exit_code != 0, res.output
    payload = json.loads(res.output)
    assert payload["ok"] is False
    assert payload["error"] == "upstream_artifacts_missing"
    assert payload["missing"]


def test_cli_deliver_allow_missing_upstream_proceeds(tmp_path: Path) -> None:
    """--allow-missing-upstream is the documented debug escape hatch."""
    patient_dir = tmp_path / "patients" / "demo"
    (patient_dir / "triggers" / "run-2").mkdir(parents=True)
    runner = CliRunner()
    res = runner.invoke(
        main,
        [
            "deliver",
            "--patient",
            str(patient_dir),
            "--run-id",
            "run-2",
            "--allow-missing-upstream",
            "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["ok"] is True
    # The runner should still have surfaced the missing list so the
    # caller knows the proceed-anyway was used.
    assert isinstance(payload.get("upstream_missing"), list)
    assert payload["upstream_missing"], "should still surface what was missing"
