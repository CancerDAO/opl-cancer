"""G60: insight_abstraction_written — the run must distill its lessons upward.

ADR-0042 (Arbor/HTR insight propagation). Arbor's ablation showed that
*abstracting* a result into a reusable prior (leaf -> direction -> global) is the
DOMINANT driver of cumulative research quality — a tree that only persists raw
results, without abstraction, performed worse than no tree at all. G54 already
makes the run *write* the ledger; it does not check that the run *abstracted*
anything. G60 closes that: a run that did research must produce at least one
abstracted cross-run prior (``triggers/<run_id>/abstraction.json``, authored by
the PI subagent ``prompts/pi/insight_abstraction.md``).

Block policy: **WARN (block=False)** — a QUALITY gate, not a SAFETY gate. The
patient's brief is NEVER withheld because the lab-memory step was skipped; the
skip is recorded in attestation and surfaced as *owed* by ``opl-cancer observe``
so the host re-grounds and does it. (Mirrors G43's WARN policy.)

This is the forcing-function half of the prompt/script boundary: the *judgment*
(the abstracted lesson) is authored by the LLM; G60 only checks, structurally,
that it exists, is grounded in real leaves, and is not an auto-filled verbatim
copy of a source hypothesis — never re-judges the lesson's content.

Inputs (claim dict):
    run_root : the ``triggers/<run_id>/`` directory
    run_id   : the run identifier (falls back to run_root dir name)
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


def _norm(s: str) -> str:
    """Normalise text for the anti-auto-fill verbatim comparison."""
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _source_hypothesis_texts(run_root: Path) -> set[str]:
    f = run_root / "wave2_hypotheses.json"
    if not f.is_file():
        return set()
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return set()
    return {_norm(h.get("text", "")) for h in (data.get("hypotheses") or []) if h.get("text")}


def _source_hypothesis_ids(run_root: Path) -> set[str]:
    f = run_root / "wave2_hypotheses.json"
    if not f.is_file():
        return set()
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return set()
    return {str(h.get("id")) for h in (data.get("hypotheses") or []) if h.get("id")}


class G60InsightAbstractionWrittenGate(Gate):
    """A run that did research must distill >=1 grounded, non-auto-filled prior."""

    name = "G60_insight_abstraction_written"
    description = (
        "Arbor/HTR's dominant gain driver is abstracting results into reusable "
        "priors. A run that produced hypotheses but wrote no abstracted prior "
        "(or an auto-filled verbatim copy of a source hypothesis) did not compound "
        "its learning upward. WARN-only: surfaced + recorded, never blocks the "
        "patient's brief."
    )
    failure_mode_code = "ADR0042-NO-ABSTRACTION"
    family_id = "reasoning-quality"

    def check(self, claim: dict[str, Any]) -> GateResult:
        run_root_raw = claim.get("run_root")
        if not run_root_raw:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP,
                message="G60 SKIP — no run_root provided.",
            )
        run_root = Path(run_root_raw)
        run_id = str(claim.get("run_id") or run_root.name)

        # Nothing to abstract until the run actually generated hypotheses.
        if not (run_root / "wave2_hypotheses.json").is_file():
            return GateResult(
                gate=self.name, status=GateStatus.SKIP,
                message="G60 SKIP — no hypotheses generated yet; nothing to abstract.",
                evidence={"run_id": run_id},
            )

        abs_file = run_root / "abstraction.json"
        if not abs_file.is_file():
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=False,
                message=(
                    "G60 WARN — run produced hypotheses but no abstraction.json. The "
                    "abstraction beat (the dominant gain driver) is OWED: dispatch "
                    "prompts/pi/insight_abstraction.md, then `opl-cancer abstract "
                    "--finalize`. The brief is not withheld, but the run did not "
                    "compound its lessons into cross-run priors."
                ),
                evidence={"run_id": run_id},
            )

        try:
            priors = (json.loads(abs_file.read_text(encoding="utf-8")) or {}).get("abstracted_priors") or []
        except Exception as exc:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=False,
                message=f"G60 WARN — abstraction.json unreadable ({exc}).",
                evidence={"run_id": run_id},
            )

        if not priors:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=False,
                message="G60 WARN — abstraction.json has zero abstracted_priors.",
                evidence={"run_id": run_id},
            )

        src_texts = _source_hypothesis_texts(run_root)
        src_ids = _source_hypothesis_ids(run_root)
        problems: list[str] = []
        for p in priors:
            pid = str(p.get("id") or "?")
            lesson = _norm(p.get("lesson", ""))
            leaves = [str(x) for x in (p.get("source_leaf_ids") or [])]
            if not lesson:
                problems.append(f"{pid}: empty lesson")
            elif lesson in src_texts:
                problems.append(f"{pid}: lesson is a VERBATIM copy of a source hypothesis (auto-fill)")
            if not leaves:
                problems.append(f"{pid}: no source_leaf_ids (ungrounded)")
            elif not (set(leaves) & src_ids):  # empty src_ids → reject, never skip (mirror cli.py)
                problems.append(f"{pid}: source_leaf_ids reference no real hypothesis in this run")

        if problems:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=False,
                message=(
                    "G60 WARN — abstraction present but not a real abstraction: "
                    + "; ".join(problems)
                    + ". Re-author per prompts/pi/insight_abstraction.md (generalize "
                    "across grounded leaves; do not restate one hypothesis)."
                ),
                evidence={"run_id": run_id, "problems": problems},
            )

        return GateResult(
            gate=self.name, status=GateStatus.PASS,
            message=(
                f"G60 OK — run {run_id} distilled {len(priors)} grounded cross-run "
                "prior(s); learning compounds upward."
            ),
            evidence={"run_id": run_id, "n_priors": len(priors)},
        )
