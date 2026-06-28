"""G52: failure_ledger — a run must read its own failures, not only its successes.

C3 / ADR-0033 (research-team iteration). Andrew Ng's decade-old move: pull every
failure into one place, read them, sort into root-cause piles, attack the
biggest. OPL has strong per-claim gates but never aggregates this run's failures
(failed retrievals, falsified/weakened hypotheses, low subgroup-match cohorts,
single-source data points, reviewer fails) into one pile to read — so a top-3
conclusion can rest on the biggest failure pile while every gate is green. The
only thing that aggregates failures today (observe.py) merely COUNTS them: a
reassuring dashboard nobody reads ("a descending loss curve is not analysis").

G52 makes the error-analysis step non-bypassable: if a run reached validation
(so failures exist to analyze) but produced no ``failure_ledger.json``, delivery
BLOCKS. The ledger is produced by the host per prompts/tasks/error_analysis.md;
G52 only verifies it exists and is structured (a ``piles`` list — possibly empty
for a genuinely clean run, which is honest, not absent). Machine-verifiable.

Inputs (claim dict): run_root.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


def _validation_ran(run_root: Path) -> bool:
    if (run_root / "wave4_validation.json").is_file():
        return True
    return bool(list(run_root.glob("tasks/*/review.json")))


class G52FailureLedgerGate(Gate):
    """A run that reached validation must produce a structured failure ledger."""

    name = "G52_failure_ledger"
    description = (
        "If a run reached validation (failures exist to analyze) but produced no "
        "failure_ledger.json, the team never read its own failures — a top-3 "
        "conclusion can rest on the biggest failure pile all-gates-green. BLOCKS. "
        "The host produces the ledger (error_analysis.md); the gate verifies it "
        "exists and is structured (a piles list). Ng's 'read 100 failures, sort, "
        "attack the biggest' made mechanical."
    )
    failure_mode_code = "C3-NO-ERROR-ANALYSIS"
    family_id = "reasoning-quality"

    def check(self, claim: dict[str, Any]) -> GateResult:
        run_root_raw = claim.get("run_root")
        if not run_root_raw:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP,
                message="G52 SKIP — no run_root to verify against.",
            )
        run_root = Path(run_root_raw)
        if not _validation_ran(run_root):
            return GateResult(
                gate=self.name, status=GateStatus.SKIP,
                message=(
                    "G52 SKIP — run has not reached validation (no wave4_validation "
                    "/ reviewer outputs); no failures to aggregate yet."
                ),
            )
        ledger_p = run_root / "failure_ledger.json"
        if not ledger_p.is_file():
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message=(
                    "G52 FAIL — run reached validation but produced no "
                    "failure_ledger.json. Run prompts/tasks/error_analysis.md: pull "
                    "every failure into one place, sort into root-cause piles, name "
                    "the biggest, and flag any top-3 conclusion that rests on it. "
                    "Reading your own failures is not optional."
                ),
                evidence={"expected": str(ledger_p)},
            )
        try:
            data = json.loads(ledger_p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message=f"G52 FAIL — failure_ledger.json unreadable: {exc}.",
                evidence={"ledger": str(ledger_p)},
            )
        if not isinstance(data, dict) or not isinstance(data.get("piles"), list):
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message=(
                    "G52 FAIL — failure_ledger.json is malformed: it must be an "
                    "object with a 'piles' list (root-cause piles; empty list is "
                    "fine for a genuinely clean run, but the key must be present)."
                ),
                evidence={"ledger_keys": list(data) if isinstance(data, dict) else None},
            )
        piles = data["piles"]
        return GateResult(
            gate=self.name, status=GateStatus.PASS,
            message=(
                f"G52 OK — failure ledger present: {len(piles)} root-cause pile(s); "
                f"biggest = {data.get('biggest_pile')!r}. The team read its failures."
            ),
            evidence={"pile_count": len(piles), "biggest_pile": data.get("biggest_pile")},
        )
