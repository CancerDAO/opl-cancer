"""C1/ADR-0031 — G50/G51 are LIVE-WIRED into run_delivery_gates.

The gates existed + were tested in isolation, but the delivery sweep never
invoked them (the orphan tell: registered but not on the path the agent runs).
Founder decision A (keep the tournament in the patient path) unblocks the
wiring. These tests prove the run-level sweep now fires G50 (a >=4-candidate
tournament must record kills) and G51 (a rendered leaderboard must be scored
or badged) — and that neither misfires on a run with no tournament/leaderboard.
"""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.glue.delivery_gate_runner import run_delivery_gates


def _run_root(tmp_path: Path) -> Path:
    r = tmp_path / "patient" / "triggers" / "r1"
    r.mkdir(parents=True)
    return r


def _wave2(r: Path, n: int) -> None:
    (r / "wave2_hypotheses.json").write_text(
        json.dumps({"hypotheses": [{"id": f"h{i}"} for i in range(n)]}),
        encoding="utf-8",
    )


def test_g50_live_wired_blocks_unkilled_tournament(tmp_path: Path) -> None:
    r = _run_root(tmp_path)
    _wave2(r, 6)  # >=4 candidates, no kill record, no all-survived justification
    verdict = run_delivery_gates(run_root=r, write_attestation=False)
    assert "G50_tournament_kill_recorded" in verdict["blocked_by"], verdict["blocked_by"]


def test_g50_live_wired_passes_with_kill_record(tmp_path: Path) -> None:
    r = _run_root(tmp_path)
    _wave2(r, 6)
    (r / "killed_candidates.jsonl").write_text(
        '{"hyp_id":"h5","final_elo":1180,"kill_reason":"dominated"}\n', encoding="utf-8"
    )
    verdict = run_delivery_gates(run_root=r, write_attestation=False)
    assert "G50_tournament_kill_recorded" not in verdict["blocked_by"], verdict["blocked_by"]


def test_g51_live_wired_blocks_rendered_unscored_unbadged(tmp_path: Path) -> None:
    r = _run_root(tmp_path)
    _wave2(r, 1)  # tournament ran (leaderboard exists)
    (r / "delivery").mkdir()
    (r / "delivery" / "patient_brief.md").write_text("leaderboard rendered", encoding="utf-8")
    verdict = run_delivery_gates(run_root=r, write_attestation=False)
    assert "G51_unfalsified_ranking" in verdict["blocked_by"], verdict["blocked_by"]


def test_g51_live_wired_passes_with_unfalsified_badge(tmp_path: Path) -> None:
    r = _run_root(tmp_path)
    (r / "wave2_hypotheses.json").write_text(
        json.dumps({"hypotheses": [{"id": "h0", "validation_status": "unfalsified"}]}),
        encoding="utf-8",
    )
    (r / "delivery").mkdir()
    (r / "delivery" / "patient_brief.md").write_text("leaderboard (unfalsified)", encoding="utf-8")
    verdict = run_delivery_gates(run_root=r, write_attestation=False)
    assert "G51_unfalsified_ranking" not in verdict["blocked_by"], verdict["blocked_by"]


def test_g50_g51_do_not_misfire_without_tournament(tmp_path: Path) -> None:
    """A run that carries no wave2 evidence and no rendered leaderboard must not
    be blocked by either C1 gate — both SKIP (the regression the old inline
    comment warned about)."""
    r = _run_root(tmp_path)  # no wave2_hypotheses.json, no leaderboard
    verdict = run_delivery_gates(run_root=r, write_attestation=False)
    assert "G50_tournament_kill_recorded" not in verdict["blocked_by"], verdict["blocked_by"]
    assert "G51_unfalsified_ranking" not in verdict["blocked_by"], verdict["blocked_by"]
