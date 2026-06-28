"""G51: unfalsified_ranking — don't render an unscored leaderboard as validated.

C1 / ADR-0031 (research-team iteration). In the common non-Docker path Wave 3/4
are skipped, so the ranked Elo leaderboard is rendered to the patient but never
falsified — a ranked 'best bet' reads as validated when it is merely unfalsified.
A desperate patient may chase the #1 believing it is proven.

G51: when a leaderboard is rendered (tournament ran AND a delivered brief
exists), require EITHER a Wave-4 scoring artifact OR an explicit per-hypothesis
'unfalsified' badge (validation_status == 'unfalsified' on the hypotheses, or an
unfalsified_ranking_ack.json). Otherwise BLOCK. Machine-verifiable.

Inputs (claim dict): run_root.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


def _brief_rendered(run_root: Path) -> bool:
    d = run_root / "delivery"
    return any((d / n).is_file() for n in ("patient_brief.md", "patient_brief.html",
                                           "patient_pi_brief.md", "patient_plain_brief.md"))


def _has_unfalsified_badge(run_root: Path) -> bool:
    if (run_root / "unfalsified_ranking_ack.json").is_file():
        return True
    p = run_root / "wave2_hypotheses.json"
    if not p.is_file():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    hyps = data.get("hypotheses") if isinstance(data, dict) else data
    if not isinstance(hyps, list) or not hyps:
        return False
    return all(h.get("validation_status") == "unfalsified" for h in hyps if isinstance(h, dict))


class G51UnfalsifiedRankingGate(Gate):
    """A rendered leaderboard must be Wave-4-scored or explicitly badged unfalsified."""

    name = "G51_unfalsified_ranking"
    description = (
        "When a hypothesis leaderboard is rendered to the patient but Wave 4 never "
        "scored it, the ranking must carry an explicit 'unfalsified — not yet "
        "tested against data' badge, not read as validated. BLOCKS a rendered, "
        "unscored, unbadged leaderboard. Machine-verifiable (Wave-4 artifact OR "
        "validation_status badge)."
    )
    failure_mode_code = "C1-UNFALSIFIED-AS-VALIDATED"
    family_id = "safety-disclosure"

    def check(self, claim: dict[str, Any]) -> GateResult:
        run_root_raw = claim.get("run_root")
        if not run_root_raw:
            return GateResult(gate=self.name, status=GateStatus.SKIP, message="G51 SKIP — no run_root.")
        run_root = Path(run_root_raw)
        ran = (run_root / "wave2_hypotheses.json").is_file()
        if not (ran and _brief_rendered(run_root)):
            return GateResult(
                gate=self.name, status=GateStatus.SKIP,
                message="G51 SKIP — no rendered leaderboard (tournament + delivered brief).",
            )
        if (run_root / "wave4_validation.json").is_file():
            return GateResult(
                gate=self.name, status=GateStatus.PASS,
                message="G51 OK — leaderboard backed by a Wave-4 scoring artifact.",
            )
        if _has_unfalsified_badge(run_root):
            return GateResult(
                gate=self.name, status=GateStatus.PASS,
                message="G51 OK — leaderboard rendered with the explicit 'unfalsified' badge.",
            )
        return GateResult(
            gate=self.name, status=GateStatus.FAIL, block=True,
            message=(
                "G51 FAIL — a hypothesis leaderboard is rendered to the patient but "
                "Wave 4 never scored it and it carries no 'unfalsified' badge. A "
                "ranked best-bet that was never tested against data must NOT read as "
                "validated: badge each hypothesis validation_status='unfalsified' or "
                "run Wave 4."
            ),
        )
