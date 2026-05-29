"""G37: service_completeness — the full planned team & waves must actually run.

v2.7.0 (ADR-0026 / session 0d1017d4 fix). Two failure modes, one gate:

1. **Under-delivery** (the patient-facing failure the founder named): OPL silently
   shrank the service — it ran 4 generic agents instead of the 20 planned experts
   and skipped Wave 2/3/4 — and only became complete because a *domain-expert*
   user kept pushing. A normal patient would have accepted the partial answer and
   never known to ask. The service must NOT quietly shrink to fit what the agent
   felt like doing.
2. **Expert collapse / theatre**: substituting fewer "general-purpose" agents for
   the named personas is invisible to every other check.

G37 makes completeness *mechanically enforced*, the same way fabrication is. It
reads ``plan.json`` (the planner's full team + warranted waves) and asserts:

* every expert the planner assigned a task produced a ``tasks/w1_<task_id>/report.md``;
* every report's author is a **roster** expert (catches "general-purpose"/collapsed
  authors — see ``KNOWN_EXPERTS``);
* every wave the plan declared (>1) left its artifacts on disk.

Dropping an expert or skipping a wave is allowed ONLY via an explicit, user-confirmed
REPLAN/SKIP record (``<run_root>/replan.json`` with ``confirmed_by_user: true``) —
i.e. the patient chose to narrow scope, the agent did not narrow it silently. Any
unexplained gap FAILs and BLOCKs delivery.

No-LLM, synchronous. Caller passes ``run_root`` (the ``triggers/<run_id>/`` dir) or
``plan_path`` + lets the gate glob the sibling artifacts.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from opl_cancer.plan.schemas import KNOWN_EXPERTS

from ..mechanical_gates import Gate, GateResult, GateStatus

_REPORT_AUTHOR_RE = re.compile(r"^#\s*Wave\s*1\s*[—\-]\s*([A-Za-z][\w\-]*)\s*/", re.MULTILINE)
# wave file → the artifact(s) proving the wave ran.
_WAVE_ARTIFACTS: dict[int, tuple[str, ...]] = {
    2: ("wave2_hypotheses.json", "tournament"),
    3: ("wave3_data_evidence.json", "data"),
    4: ("wave4_validation.json", "tasks"),  # tasks/w4_*/report.md
}


def _resolve_run_root(claim: dict[str, Any]) -> Path | None:
    if claim.get("run_root"):
        return Path(claim["run_root"])
    if claim.get("plan_path"):
        return Path(claim["plan_path"]).parent
    return None


def _planned_experts_and_waves(plan: dict[str, Any]) -> tuple[dict[str, str], set[int]]:
    """Return ({task_id: expert}, {planned wave numbers})."""
    task_expert: dict[str, str] = {}
    for t in plan.get("tasks", []) or []:
        if isinstance(t, dict) and t.get("id") and t.get("expert"):
            task_expert[str(t["id"])] = str(t["expert"]).lower()
    waves: set[int] = set()
    for w in plan.get("waves", []) or []:
        if isinstance(w, dict) and w.get("wave_number"):
            try:
                waves.add(int(w["wave_number"]))
            except (ValueError, TypeError):
                pass
    return task_expert, waves


def _wave_ran(run_root: Path, wave: int) -> bool:
    for name in _WAVE_ARTIFACTS.get(wave, ()):
        p = run_root / name
        if p.is_file():
            return True
        if p.is_dir():
            # directory counts only if it holds wave-specific artifacts
            if wave == 4 and list(p.glob("w4_*/report.md")):
                return True
            if wave == 3 and any(p.rglob("*")):
                return True
            if wave == 2 and list(p.glob("*.json")):
                return True
    return False


class G37ServiceCompletenessGate(Gate):
    """Planned full team + warranted waves must all have run, or be user-waived."""

    name = "G37_service_completeness"
    description = (
        "Every expert the planner assigned must have produced a Wave-1 report; "
        "every report author must be a roster expert; every planned wave must "
        "have left artifacts. Silent under-delivery / 20→4 collapse BLOCKS "
        "delivery unless a user-confirmed REPLAN record waives the gap."
    )
    failure_mode_code = "AP-UNDER-DELIVERY"
    family_id = "provenance"

    def check(self, claim: dict[str, Any]) -> GateResult:
        run_root = _resolve_run_root(claim)
        if run_root is None or not run_root.exists():
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message="G37 FAIL — no run_root/plan to verify completeness against.",
                evidence={"run_root": str(run_root)},
            )
        plan_path = run_root / "plan.json"
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message=f"G37 FAIL — plan.json missing/unreadable: {exc}",
                evidence={"plan_path": str(plan_path)},
            )

        task_expert, planned_waves = _planned_experts_and_waves(plan)
        planned_experts = set(task_expert.values())
        if not planned_experts:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message="G37 FAIL — plan.json declares no experts; nothing was planned.",
            )

        # explicit user-confirmed waivers
        waived_experts: set[str] = set()
        waived_waves: set[int] = set()
        replan_p = run_root / "replan.json"
        if replan_p.is_file():
            try:
                replan = json.loads(replan_p.read_text(encoding="utf-8"))
                if replan.get("confirmed_by_user"):
                    waived_experts = {str(x).lower() for x in replan.get("dropped_experts", [])}
                    waived_waves = {int(x) for x in replan.get("skipped_waves", [])}
            except (OSError, json.JSONDecodeError, ValueError, TypeError):
                pass

        # executed wave-1 reports → authors
        executed_experts: set[str] = set()
        non_roster_authors: set[str] = set()
        reports = list(run_root.glob("tasks/w1_*/report.md"))
        for rp in reports:
            task_id = rp.parent.name[len("w1_"):]
            expert = task_expert.get(task_id)
            text = ""
            try:
                text = rp.read_text(encoding="utf-8")
            except OSError:
                pass
            m = _REPORT_AUTHOR_RE.search(text)
            header_author = m.group(1).lower() if m else None
            author = expert or header_author
            if author:
                executed_experts.add(author)
                if author not in KNOWN_EXPERTS:
                    non_roster_authors.add(author)
            if header_author and header_author not in KNOWN_EXPERTS:
                non_roster_authors.add(header_author)

        problems: list[str] = []

        missing_experts = sorted(planned_experts - executed_experts - waived_experts)
        if missing_experts:
            problems.append(
                f"{len(missing_experts)} planned expert(s) produced NO report and were "
                f"not user-waived: {missing_experts} (under-delivery / silent collapse)"
            )
        if non_roster_authors:
            problems.append(
                f"non-roster author(s) {sorted(non_roster_authors)} — generic agents "
                "substituted for named personas (expert collapse)"
            )
        missing_waves = sorted((planned_waves - {1}) - waived_waves - {
            w for w in planned_waves if w == 1 or _wave_ran(run_root, w)
        })
        if missing_waves:
            problems.append(
                f"planned wave(s) {missing_waves} left no artifacts and were not "
                "user-waived (service silently shrank)"
            )

        if problems:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message=(
                    "G37 FAIL — service is incomplete relative to the plan. "
                    + " | ".join(problems)
                    + ". To narrow scope, write a user-confirmed replan.json; "
                    "the agent must never shrink the service silently."
                ),
                evidence={
                    "planned_experts": sorted(planned_experts),
                    "executed_experts": sorted(executed_experts),
                    "missing_experts": missing_experts,
                    "non_roster_authors": sorted(non_roster_authors),
                    "planned_waves": sorted(planned_waves),
                    "missing_waves": missing_waves,
                    "waived_experts": sorted(waived_experts),
                    "waived_waves": sorted(waived_waves),
                },
            )

        return GateResult(
            gate=self.name, status=GateStatus.PASS,
            message=(
                f"G37 OK — all {len(planned_experts)} planned expert(s) ran "
                f"({len(reports)} reports), all roster, planned waves "
                f"{sorted(planned_waves)} present."
            ),
            evidence={
                "planned_experts": sorted(planned_experts),
                "executed_experts": sorted(executed_experts),
            },
        )
