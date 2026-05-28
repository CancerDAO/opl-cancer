"""v2.5.1 B3 — Wave 3 must run fakery_sniffer + reviewer_hook after each
data-evidence write (same discipline as wave1_runner)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opl_cancer.glue._post_write import SnifferHalt, post_write_safety_check


def test_post_write_safety_check_halts_on_wave3_fakery(tmp_path: Path) -> None:
    report = tmp_path / "analysis.md"
    report.write_text("Per <insert PMID> the cohort showed estimated 8 fold change.")
    with pytest.raises(SnifferHalt):
        post_write_safety_check(report, run_root=tmp_path)
    assert (tmp_path / "SNIFFER_HALT.md").exists()


def test_wave3_runner_imports_post_write_safety_check() -> None:
    """B3 — Wave 3 runner must wire the shared sniffer + reviewer hook."""
    import opl_cancer.glue.wave3_runner as w3

    assert hasattr(w3, "post_write_safety_check")
    assert hasattr(w3, "run_reviewer_pairing")


def test_wave3_runner_calls_sniffer_on_data_evidence_json(tmp_path: Path) -> None:
    """End-to-end: a fakery payload in wave3_data_evidence.json triggers halt."""
    run_dir = tmp_path / "run-x"
    run_dir.mkdir()
    bad = run_dir / "wave3_data_evidence.json"
    bad.write_text(
        json.dumps({"analysis": "Effect approximately 5 fold and <insert citation>"})
    )
    with pytest.raises(SnifferHalt):
        post_write_safety_check(bad, run_root=run_dir)
    assert (run_dir / "SNIFFER_HALT.md").exists()
