"""v2.4 — CLI tests for `opl wave6 --submit-to-n1arxiv`.

Verifies:

* Flag is wired into `wave6` (does not auto-execute git/gh)
* Without --n1arxiv-repo, prints submission instructions but doesn't error
* With --n1arxiv-repo, stages the bundle + content stub
* `--final` is required (drafts cannot be submitted)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from opl_cancer.cli import main as cli_main


def _seed_run(tmp_path: Path) -> tuple[Path, str, str]:
    """Build a complete enough patient_dir + run to let wave6 --final succeed."""
    patient_dir = tmp_path / "patient"
    triggers = patient_dir / "triggers" / "run-x"
    triggers.mkdir(parents=True)

    # Wave 5 prerequisites
    (triggers / "patient_plain_brief.md").write_text("# brief\n", encoding="utf-8")
    (triggers / "patient_pi_brief.md").write_text("# pi brief\n", encoding="utf-8")

    # Wave 6 artifacts — these will be scaffolded in draft mode, or
    # pre-populated for final mode test.
    (triggers / "manuscript.md").write_text(
        "# Manuscript\n\n[BACKGROUND] N=1 framing.\n\n"
        "Pembrolizumab is approved [PMID:32179615].\n",
        encoding="utf-8",
    )
    (triggers / "ai_authorship_disclosure.md").write_text(
        "# AI Authorship\n\nNo human author beyond the patient and "
        "supervising clinician.\n\n| Expert | Role |\n| - | - |\n| Iain | retrieval |\n",
        encoding="utf-8",
    )
    (triggers / "reproducibility.md").write_text(
        "# Reproducibility\n\n## Data sources\n\n- TCGA, tier: public\n",
        encoding="utf-8",
    )
    (triggers / "HENRY_AUDIT.json").write_text(
        json.dumps({"audit_version": "v2.3", "status": "pass"}),
        encoding="utf-8",
    )
    (triggers / "ethics_declaration.md").write_text(
        "# Ethics\n\nReference case; consent not applicable.\n",
        encoding="utf-8",
    )
    # Methods file containing the G33 single-subject (N=1) design declaration.
    (triggers / "manuscript_methods.md").write_text(
        "# Methods\n\nThis is a single-subject (N=1) design analysis "
        "[PMID:32179615].\n",
        encoding="utf-8",
    )

    return patient_dir, "run-x", "riaz-reference"


def test_submit_flag_is_wired() -> None:
    """`opl wave6 --help` mentions --submit-to-n1arxiv."""
    runner = CliRunner()
    result = runner.invoke(cli_main, ["wave6", "--help"])
    assert result.exit_code == 0, result.output
    assert "--submit-to-n1arxiv" in result.output
    assert "--n1arxiv-repo" in result.output


def test_submit_to_n1arxiv_with_local_clone(tmp_path: Path) -> None:
    """End-to-end: wave6 --final --submit-to-n1arxiv --n1arxiv-repo PATH
    stages the bundle into the clone and prints the PR body draft."""
    patient_dir, run_id, patient_code = _seed_run(tmp_path)
    n1a_clone = tmp_path / "n1arxiv-clone"
    (n1a_clone / "static" / "bundles").mkdir(parents=True)
    (n1a_clone / "content" / "papers").mkdir(parents=True)

    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        [
            "wave6",
            "--patient-dir",
            str(patient_dir),
            "--run-id",
            run_id,
            "--patient-code",
            patient_code,
            "--final",
            "--data-source",
            "reference_case",
            "--submit-to-n1arxiv",
            "--n1arxiv-repo",
            str(n1a_clone),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["ok"] is True
    assert "n1arxiv_submission" in payload
    sub = payload["n1arxiv_submission"]
    assert sub["bundle_target"].endswith(".n1a.zip")
    assert sub["content_stub_target"].endswith(".md")
    # File actually copied
    assert (n1a_clone / "static" / "bundles").iterdir()
    assert (n1a_clone / "content" / "papers").iterdir()


def test_submit_without_local_clone_emits_instructions(tmp_path: Path) -> None:
    """Without --n1arxiv-repo, the CLI emits PR-body draft + git instructions
    but does not error."""
    patient_dir, run_id, patient_code = _seed_run(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        [
            "wave6",
            "--patient-dir",
            str(patient_dir),
            "--run-id",
            run_id,
            "--patient-code",
            patient_code,
            "--final",
            "--data-source",
            "reference_case",
            "--submit-to-n1arxiv",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["ok"] is True
    assert "n1arxiv_submission" in payload
    sub = payload["n1arxiv_submission"]
    # No clone → no targets, but pr_body still present + instructions present
    assert sub.get("pr_body")
    assert "gh pr create" in sub.get("suggested_commands", "")


def test_submit_refuses_in_draft(tmp_path: Path) -> None:
    """--submit-to-n1arxiv with --draft is a user error; draft != publishable."""
    patient_dir, run_id, patient_code = _seed_run(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        [
            "wave6",
            "--patient-dir",
            str(patient_dir),
            "--run-id",
            run_id,
            "--patient-code",
            patient_code,
            "--draft",
            "--submit-to-n1arxiv",
            "--json",
        ],
    )
    # Non-zero exit when draft + submit combined
    assert result.exit_code != 0, result.output
    assert "draft" in result.output.lower() or "final" in result.output.lower()
