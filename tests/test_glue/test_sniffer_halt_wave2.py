"""v2.5.1 B3 — Wave 2 must run fakery_sniffer + reviewer_hook after each
hypothesis write (same discipline as wave1_runner)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opl_cancer.glue._post_write import SnifferHalt, post_write_safety_check


def test_post_write_safety_check_halts_on_wave2_fakery(tmp_path: Path) -> None:
    """Mirror test_sniffer_halt.test_sniffer_hit_raises_halt for Wave 2."""
    report = tmp_path / "hyp_h1.md"
    report.write_text("Hypothesis: ORR approximately 30% in this cohort.")
    with pytest.raises(SnifferHalt):
        post_write_safety_check(report, run_root=tmp_path)
    assert (tmp_path / "SNIFFER_HALT.md").exists()


def test_wave2_runner_imports_post_write_safety_check() -> None:
    """B3 — Wave 2 runner must wire the shared sniffer + reviewer hook."""
    import opl_cancer.glue.wave2_runner as w2

    assert hasattr(w2, "post_write_safety_check"), (
        "Wave2Runner must import post_write_safety_check from glue._post_write"
    )
    assert hasattr(w2, "run_reviewer_pairing"), (
        "Wave2Runner must import run_reviewer_pairing from orchestrator.reviewer_hook"
    )


def test_wave2_runner_calls_sniffer_on_hypothesis_json(tmp_path: Path) -> None:
    """End-to-end: planting a fakery-looking payload in the rendered
    hypothesis JSON file makes Wave 2 raise SnifferHalt."""
    from opl_cancer.glue.wave2_runner import Wave2Runner

    # Build a stub runner with monkey-patched scan to force a hit.
    runner = Wave2Runner.__new__(Wave2Runner)  # type: ignore[call-arg]
    runner.out_dir = tmp_path
    run_dir = tmp_path / "run-x"
    run_dir.mkdir()
    bad = run_dir / "wave2_hypotheses.json"
    bad.write_text(
        json.dumps({"text": "Estimated 5000000 deaths per year [BACKGROUND]"})
    )
    # Strip [BACKGROUND] so the sniffer fires.
    bad.write_text(
        json.dumps({"text": "Estimated 5000000 deaths per year and likely between 1 and 5"})
    )
    with pytest.raises(SnifferHalt):
        post_write_safety_check(bad, run_root=run_dir)
    assert (run_dir / "SNIFFER_HALT.md").exists()
