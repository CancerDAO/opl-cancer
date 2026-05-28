"""v2.5.1 B3 — Wave 4 must run fakery_sniffer + reviewer_hook after each
validation write (same discipline as wave1_runner)."""
from __future__ import annotations

from pathlib import Path

import pytest

from opl_cancer.glue._post_write import SnifferHalt, post_write_safety_check


def test_post_write_safety_check_halts_on_wave4_fakery(tmp_path: Path) -> None:
    report = tmp_path / "validation.md"
    report.write_text("Estimated 7 fold reduction in disease progression.")
    with pytest.raises(SnifferHalt):
        post_write_safety_check(report, run_root=tmp_path)
    assert (tmp_path / "SNIFFER_HALT.md").exists()


def test_wave4_runner_imports_post_write_safety_check() -> None:
    """B3 — Wave 4 runner must wire the shared sniffer + reviewer hook."""
    import opl_cancer.glue.wave4_runner as w4

    assert hasattr(w4, "post_write_safety_check")
    assert hasattr(w4, "run_reviewer_pairing")
