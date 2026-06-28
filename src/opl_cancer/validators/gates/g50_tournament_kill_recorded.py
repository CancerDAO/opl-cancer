"""G50: tournament_kill_recorded — a real tournament discards weak candidates.

C1 / ADR-0031 (research-team iteration). Research speed is the speed at which you
discover you're wrong; the discard-the-wrong-ideas half of that loop was inert —
the live tournament generated candidates and killed 0 (prune_below was dead code,
every node stayed 'alive', the bracket only ranked). A tournament that promotes
strong ideas but never discards weak ones leaks low-evidence speculative
directions to a desperate patient as if they had competed and survived.

G50: if Wave 2 ran >=4 candidates but recorded no kills (no killed_candidates.jsonl)
and offered no explicit all-survived justification, BLOCK. Machine-verifiable
(candidate count vs recorded kills). The LLM/tournament decides WHICH to kill;
the gate only enforces that discarding actually happened (or was justified).

Inputs (claim dict): run_root.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_MIN_FOR_KILL = 4


def _candidate_count(run_root: Path) -> int:
    p = run_root / "wave2_hypotheses.json"
    if not p.is_file():
        return 0
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    hyps = data.get("hypotheses") if isinstance(data, dict) else data
    return len(hyps) if isinstance(hyps, list) else 0


def _kill_count(run_root: Path) -> int:
    p = run_root / "killed_candidates.jsonl"
    if not p.is_file():
        return 0
    try:
        return sum(1 for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip())
    except OSError:
        return 0


class G50TournamentKillRecordedGate(Gate):
    """A >=4-candidate tournament must record kills or an all-survived justification."""

    name = "G50_tournament_kill_recorded"
    description = (
        "A Wave-2 tournament with >=4 candidates must record >=1 kill "
        "(killed_candidates.jsonl) or an explicit all-survived justification "
        "(tournament_all_survived.json). A tournament that discards nothing is a "
        "beauty contest that leaks weak speculative directions as if they had "
        "survived. Machine-verifiable; BLOCKS."
    )
    failure_mode_code = "C1-NO-KILL"
    family_id = "reasoning-quality"

    def check(self, claim: dict[str, Any]) -> GateResult:
        run_root_raw = claim.get("run_root")
        if not run_root_raw:
            return GateResult(gate=self.name, status=GateStatus.SKIP,
                              message="G50 SKIP — no run_root.")
        run_root = Path(run_root_raw)
        n = _candidate_count(run_root)
        if n < _MIN_FOR_KILL:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP,
                message=f"G50 SKIP — only {n} candidate(s) (<{_MIN_FOR_KILL}); kill not required.",
            )
        if _kill_count(run_root) > 0:
            return GateResult(
                gate=self.name, status=GateStatus.PASS,
                message=f"G50 OK — {_kill_count(run_root)} candidate(s) killed of {n}.",
                evidence={"candidates": n, "killed": _kill_count(run_root)},
            )
        if (run_root / "tournament_all_survived.json").is_file():
            return GateResult(
                gate=self.name, status=GateStatus.PASS,
                message="G50 OK — 0 kills but an explicit all-survived justification was recorded.",
                evidence={"candidates": n, "killed": 0, "all_survived_justified": True},
            )
        return GateResult(
            gate=self.name, status=GateStatus.FAIL, block=True,
            message=(
                f"G50 FAIL — tournament ran {n} candidates but killed 0 and gave no "
                "all-survived justification. A tournament must discriminate: record "
                "killed_candidates.jsonl (with a kill reason per discarded candidate) "
                "or tournament_all_survived.json explaining why none was dominated."
            ),
            evidence={"candidates": n, "killed": 0},
        )
