"""v2.6.0 — B5 must check upstream CONTENT, not just file existence.

Review (2026-05-29): README/What-this-does claims "Refuses to ship when upstream
waves haven't produced real evidence (v2.5.1 B5)", but verify_upstream_artifacts
only globbed for file presence/count — an empty `{}` plan + `{"hypotheses": []}`
wave file passed the gate, so a hollow run shipped a brief. The fix makes the
gate semantic: empty plan / empty wave arrays / trivial wave-1 report are
reported as hollow and refused.

Failing-first tests.
"""
from __future__ import annotations

from pathlib import Path

from opl_cancer.glue.delivery_runner import verify_upstream_artifacts


def _files(run_root: Path, *, plan: str, report: str, wave2: str) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    w1 = run_root / "tasks" / "w1_bert"
    w1.mkdir(parents=True, exist_ok=True)
    (w1 / "report.md").write_text(report, encoding="utf-8")
    (run_root / "plan.json").write_text(plan, encoding="utf-8")
    (run_root / "wave2_hypotheses.json").write_text(wave2, encoding="utf-8")


def test_hollow_empty_plan_and_empty_hypotheses_is_refused(tmp_path: Path) -> None:
    rr = tmp_path / "triggers" / "r1"
    _files(rr, plan="{}", report="# bert\n", wave2='{"hypotheses": [], "top_k": []}')
    missing = verify_upstream_artifacts(rr)
    assert missing, "hollow upstream (empty plan + empty hypotheses) must be refused"
    assert any("hollow" in m.lower() or "empty" in m.lower() for m in missing), missing


def test_real_content_passes(tmp_path: Path) -> None:
    rr = tmp_path / "triggers" / "r1"
    _files(
        rr,
        plan='{"goal": "3rd-line options", "tasks": ["t1"]}',
        report="# bert\nPer Awad et al. (PMID:34750504), ORR 23.2% (n=142).\n",
        wave2='{"hypotheses": [{"id": "h1", "text": "x"}], "top_k": ["h1"]}',
    )
    assert verify_upstream_artifacts(rr) == []
