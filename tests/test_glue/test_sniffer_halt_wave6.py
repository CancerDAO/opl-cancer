"""v2.5.1 B3 — Wave 6 must run fakery_sniffer + reviewer_hook after each
manuscript write (same discipline as wave1_runner; v2.3 advertised PMID
anchoring discipline so this is the most important wave for the sniffer)."""
from __future__ import annotations

from pathlib import Path

import pytest

from opl_cancer.glue._post_write import SnifferHalt, post_write_safety_check


def test_post_write_safety_check_halts_on_wave6_fakery(tmp_path: Path) -> None:
    """A manuscript section with '<insert PMID>' should trigger halt."""
    report = tmp_path / "manuscript_results.md"
    report.write_text(
        "Per Awad et al. <insert PMID>, ORR was approximately 23.2% in n=142."
    )
    with pytest.raises(SnifferHalt):
        post_write_safety_check(report, run_root=tmp_path)
    assert (tmp_path / "SNIFFER_HALT.md").exists()


def test_wave6_runner_imports_post_write_safety_check() -> None:
    """B3 — Wave 6 runner must wire the shared sniffer + reviewer hook."""
    import opl_cancer.glue.wave6_runner as w6

    assert hasattr(w6, "post_write_safety_check")
    assert hasattr(w6, "run_reviewer_pairing")


def test_wave6_runner_scans_scaffolded_manuscript_files(tmp_path: Path) -> None:
    """B3 end-to-end: when the manuscript files written by Wave 6 carry
    fakery markers, the runner short-circuits via SnifferHalt."""
    from opl_cancer.glue.wave6_runner import Wave6Runner, Wave6Failure

    patient_dir = tmp_path / "patients" / "demo"
    run_dir = patient_dir / "triggers" / "rid"
    run_dir.mkdir(parents=True)

    # Wave 5 + B5 prereqs.
    (run_dir / "patient_plain_brief.md").write_text("# plain\n")
    (run_dir / "patient_pi_brief.md").write_text("# pi\n")
    (run_dir / "plan.json").write_text('{"tasks": []}')
    (run_dir / "wave2_hypotheses.json").write_text("{}")
    # Manuscript file with fakery.
    (run_dir / "manuscript.md").write_text(
        "# Manuscript\n\n<insert PMID> for cohort.\n"
    )
    # Scaffold the others as empty.
    (run_dir / "ai_authorship_disclosure.md").write_text("# AI Authorship\n")
    (run_dir / "reproducibility.md").write_text("# Repro\n")
    (run_dir / "HENRY_AUDIT.json").write_text("{}")

    runner = Wave6Runner(
        patient_dir=patient_dir,
        run_id="rid",
        patient_code="demo",
        mode="draft",
    )
    with pytest.raises((SnifferHalt, Wave6Failure)):
        runner.run()
    assert (run_dir / "SNIFFER_HALT.md").exists()
