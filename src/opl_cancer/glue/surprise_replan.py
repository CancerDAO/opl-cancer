"""D3/ADR-0036 — the mid-run replan RUNTIME (spawns the task the policy approves).

``glue/surprise_followup.decide_surprise_followup`` is the pure discipline (a
genuine surprise must not be silently ignored; a chased one MUST carry a
testability_path). This module is the runtime the policy's docstring promised:
when a Wave-3 result contradicts the locked forecast or surfaces a strange-tail
anomaly AND is testable, write a replan task spec the host picks up — a new
task/expert that chases the surprise rather than only logging it to the failure
ledger.

The DETECTION (contradicted / anomaly / testability_path) is LLM judgment,
supplied by the caller (Wave-4 Aviv validation, or the host planner's
"Follow the surprise" step). Python only enforces the deterministic discipline
and emits the task — it never judges the phenotype.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from opl_cancer.glue.surprise_followup import decide_surprise_followup

REPLAN_DIRNAME = "replan"


def spawn_surprise_replan(
    run_root: Path | str,
    *,
    hypothesis_id: str,
    contradicted: bool,
    anomaly: bool,
    testability_path: str | None,
    trigger_detail: str = "",
    new_expert: str = "aviv",
) -> dict[str, Any]:
    """Act on a Wave-3 surprise. Returns the decision augmented with the spawn
    outcome (``spawned``, ``replan_task_path``). Writes
    ``<run_root>/replan/replan_<hyp_id>.json`` only when the surprise should be
    chased (decide_surprise_followup approves it); a surprise with no
    testability_path is left un-chased (blocked_reason set) — the
    manufactured-novelty guard. A non-surprise is a no-op.
    """
    decision = decide_surprise_followup(
        contradicted=contradicted, anomaly=anomaly, testability_path=testability_path
    )
    out: dict[str, Any] = {
        "hypothesis_id": hypothesis_id,
        "spawned": False,
        "replan_task_path": None,
        **decision,
    }
    if not decision["should_chase"]:
        return out

    replan_dir = Path(run_root) / REPLAN_DIRNAME
    replan_dir.mkdir(parents=True, exist_ok=True)
    task_id = f"replan_{hypothesis_id}"
    task = {
        "task_id": task_id,
        "kind": "surprise_followup",
        "source_hypothesis_id": hypothesis_id,
        "trigger": "contradicted_forecast" if contradicted else "strange_tail_anomaly",
        "expert": new_expert,
        "testability_path": testability_path,
        "rationale": trigger_detail,
        "status": "pending",
    }
    task_path = replan_dir / f"{task_id}.json"
    task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    out["spawned"] = True
    out["replan_task_path"] = str(task_path)
    return out


__all__ = ["spawn_surprise_replan", "REPLAN_DIRNAME"]
