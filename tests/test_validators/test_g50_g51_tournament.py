"""G50 + G51 — an honest tournament: it must KILL, and an unscored leaderboard
must not read as validated.

C1 / ADR-0031. The live tournament generates candidates and kills 0 (prune_below
was dead code), and in the common non-Docker path (Wave 3/4 skipped) the ranked
Elo leaderboard is rendered to the patient but never falsified — a ranked 'best
bet' reads as validated when it is merely unfalsified. Two verifiable gates:
G50 (a tournament with >=4 candidates must record kills) and G51 (a rendered
leaderboard needs a Wave-4 score OR an explicit 'unfalsified' badge).
"""
from __future__ import annotations

import json

from opl_cancer.validators.gates.g50_tournament_kill_recorded import (
    G50TournamentKillRecordedGate,
)
from opl_cancer.validators.gates.g51_unfalsified_ranking import (
    G51UnfalsifiedRankingGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


def _run(tmp_path):
    r = tmp_path / "triggers" / "run-1"
    r.mkdir(parents=True)
    return r


def _wave2(r, n):
    (r / "wave2_hypotheses.json").write_text(
        json.dumps({"hypotheses": [{"id": f"h{i}"} for i in range(n)]}), encoding="utf-8"
    )


# ---- G50 ----

def test_g50_skip_small_tournament(tmp_path):
    r = _run(tmp_path)
    _wave2(r, 3)  # < 4 candidates → kill not required
    assert G50TournamentKillRecordedGate().check({"run_root": str(r)}).status == GateStatus.SKIP


def test_g50_block_when_no_kills_recorded(tmp_path):
    r = _run(tmp_path)
    _wave2(r, 6)  # 6 candidates, none killed
    res = G50TournamentKillRecordedGate().check({"run_root": str(r)})
    assert res.status == GateStatus.FAIL and res.block is True


def test_g50_pass_when_kills_recorded(tmp_path):
    r = _run(tmp_path)
    _wave2(r, 6)
    (r / "killed_candidates.jsonl").write_text(
        '{"hyp_id":"h5","round":1,"final_elo":1180,"kill_reason":"dominated"}\n',
        encoding="utf-8",
    )
    assert G50TournamentKillRecordedGate().check({"run_root": str(r)}).status == GateStatus.PASS


def test_g50_pass_when_all_survived_justified(tmp_path):
    r = _run(tmp_path)
    _wave2(r, 6)
    (r / "tournament_all_survived.json").write_text(
        json.dumps({"justification": "all 6 cleared the SoC seed; none dominated"}),
        encoding="utf-8",
    )
    assert G50TournamentKillRecordedGate().check({"run_root": str(r)}).status == GateStatus.PASS


# ---- G51 ----

def test_g51_skip_when_no_leaderboard_rendered(tmp_path):
    r = _run(tmp_path)
    _wave2(r, 5)  # tournament ran but no delivered brief yet
    assert G51UnfalsifiedRankingGate().check({"run_root": str(r)}).status == GateStatus.SKIP


def test_g51_pass_when_wave4_scored(tmp_path):
    r = _run(tmp_path)
    _wave2(r, 5)
    (r / "delivery").mkdir()
    (r / "delivery" / "patient_brief.md").write_text("leaderboard", encoding="utf-8")
    (r / "wave4_validation.json").write_text(json.dumps({"validations": [{"id": "h0"}]}), encoding="utf-8")
    assert G51UnfalsifiedRankingGate().check({"run_root": str(r)}).status == GateStatus.PASS


def test_g51_block_when_rendered_unscored_and_unbadged(tmp_path):
    r = _run(tmp_path)
    _wave2(r, 5)
    (r / "delivery").mkdir()
    (r / "delivery" / "patient_brief.md").write_text("leaderboard rendered", encoding="utf-8")
    res = G51UnfalsifiedRankingGate().check({"run_root": str(r)})
    assert res.status == GateStatus.FAIL and res.block is True


def test_g51_pass_when_unfalsified_badge_present(tmp_path):
    r = _run(tmp_path)
    (r / "wave2_hypotheses.json").write_text(
        json.dumps({"hypotheses": [{"id": "h0", "validation_status": "unfalsified"}]}),
        encoding="utf-8",
    )
    (r / "delivery").mkdir()
    (r / "delivery" / "patient_brief.md").write_text("leaderboard (unfalsified badge)", encoding="utf-8")
    assert G51UnfalsifiedRankingGate().check({"run_root": str(r)}).status == GateStatus.PASS
