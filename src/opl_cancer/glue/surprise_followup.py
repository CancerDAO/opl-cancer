"""D3 / ADR-0036 — follow-the-surprise discipline policy.

Chance favors the prepared mind: a research team's biggest wins come from chasing
the thing it wasn't looking for. OPL was architected to route all surprise into
gates and suppress it; D3 turns an unexpected Wave-3 result into a promoted
replan instead of a mere failure-ledger entry.

The DETECTION (does this Wave-3 result contradict the pre-registered forecast, or
is it a strange-tail anomaly?) is LLM judgment — the host decides and passes
``contradicted`` / ``anomaly`` (see prompts/pi/goal_backward_planner.md
"Follow the surprise"). This pure policy enforces the deterministic DISCIPLINE:

  * a genuine surprise must not be silently ignored, AND
  * a chased surprise MUST carry a ``testability_path`` (the manufactured-novelty
    guard — no chasing a shiny anomaly with no way to test it).

The mid-run replan RUNTIME (spawning the new task/expert) lives in the
orchestrator, which is mid-extraction (PRD §9 open-Q#3); this policy is the
verifiable core the runtime will call.
"""
from __future__ import annotations


def decide_surprise_followup(
    *, contradicted: bool, anomaly: bool, testability_path: str | None
) -> dict[str, object]:
    """Decide whether a Wave-3 surprise should be chased. Pure + deterministic."""
    is_surprise = bool(contradicted or anomaly)
    if not is_surprise:
        return {"is_surprise": False, "should_chase": False, "blocked_reason": ""}
    if testability_path and testability_path.strip():
        return {"is_surprise": True, "should_chase": True, "blocked_reason": ""}
    return {
        "is_surprise": True,
        "should_chase": False,
        "blocked_reason": (
            "surprise has no testability_path — chasing it would be manufactured "
            "novelty; record it in the failure ledger and seek a kill-test first."
        ),
    }


__all__ = ["decide_surprise_followup"]
