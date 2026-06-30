from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from opl_cancer.cli import main
from opl_cancer.evaluation.release_golden import (
    SCHEMA,
    run_release_golden_eval,
    write_release_golden_eval,
)


def test_release_golden_eval_passes_current_golden_set() -> None:
    report = run_release_golden_eval()

    assert report["schema"] == SCHEMA
    assert report["ok"] is True
    assert report["summary"]["synthetic_patients"]["count"] >= 4
    assert report["summary"]["failure_mode_inputs"]["distinct_gates"] >= 5
    assert report["summary"]["errors"] == 0


def test_release_golden_eval_fails_missing_root(tmp_path: Path) -> None:
    report = run_release_golden_eval(tmp_path / "missing")

    assert report["ok"] is False
    assert report["summary"]["errors"] == 1
    assert report["checks"][0]["name"] == "golden_root_exists"


def test_write_release_golden_eval_report(tmp_path: Path) -> None:
    report = run_release_golden_eval()
    out = write_release_golden_eval(report, tmp_path / "release" / "report.json")

    assert out.is_file()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["schema"] == SCHEMA


def test_cli_release_eval_json() -> None:
    result = CliRunner().invoke(main, ["release-eval", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == SCHEMA
    assert payload["ok"] is True


def test_cli_release_eval_writes_report(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    result = CliRunner().invoke(main, ["release-eval", "--json", "--out", str(out)])

    assert result.exit_code == 0, result.output
    assert out.is_file()
    payload = json.loads(result.output)
    assert payload["report_path"] == str(out)

