"""Deterministic explored→survived funnel + hypothesis-forest helpers (ADR-0042).

Single source of truth shared by the CLI (`observe`/`funnel`) and the delivery
runner (which auto-emits `funnel.json` so the patient brief can always render the
honest explored-vs-survived section). Pure reads — no LLM, no judgment; counts
only. The narrative is the brief's job (boundary: numbers=script, prose=prompt).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_hypotheses(run_root: Path) -> list[dict[str, Any]]:
    data = _load_json(run_root / "wave2_hypotheses.json") or {}
    return list(data.get("hypotheses") or [])


def build_forest(hyps: list[dict[str, Any]]) -> tuple[dict[str, list[str]], list[str]]:
    """(children-by-id, root-ids). parent_chain[0] is the immediate parent; an
    empty/absent parent marks a root. If a malformed/cyclic chain leaves every
    node a child (no roots), fall back to a flat forest so the patient's
    hypotheses are never silently dropped."""
    by_id = {str(h.get("id")): h for h in hyps if h.get("id")}
    children: dict[str, list[str]] = {hid: [] for hid in by_id}
    roots: list[str] = []
    for hid, h in by_id.items():
        chain = [str(x) for x in (h.get("parent_chain") or [])]
        parent = chain[0] if chain else None
        if parent and parent in by_id:
            children[parent].append(hid)
        else:
            roots.append(hid)
    if not roots and by_id:
        roots = sorted(by_id)
        children = {hid: [] for hid in by_id}
    return children, sorted(roots)


def depth_map(hyps: list[dict[str, Any]]) -> dict[str, int]:
    """Per-node tree depth on the SAME forest the renderer builds (dangling
    parents = roots, root depth = 1), cycle-safe. Single source of truth for
    depth — used by observe, validate, AND the deepen budget so they cannot
    disagree (the bug iteration-2's review caught)."""
    children, roots = build_forest(hyps)
    depth_of: dict[str, int] = {r: 1 for r in roots}
    stack = list(roots)
    while stack:
        n = stack.pop()
        for c in children.get(n, []):
            if c not in depth_of:  # cycle-safe
                depth_of[c] = depth_of[n] + 1
                stack.append(c)
    return depth_of


def forest_depth(hyps: list[dict[str, Any]]) -> int:
    dm = depth_map(hyps)
    return max(dm.values(), default=1) if hyps else 1


def w4_survival_by_id(run_root: Path) -> dict[str, str]:
    w4 = _load_json(Path(run_root) / "wave4_validation.json") or {}
    return {str(v.get("hyp_id")): str(v.get("survival_status") or "")
            for v in (w4.get("validations") or []) if v.get("hyp_id")}


def lifestate(hyp: dict[str, Any], w4_by_id: dict[str, str]) -> str:
    """Canonical tri-state of a hypothesis: 'alive' | 'dead' | 'pending'.

    Reconciles the TWO status vocabularies that disagreed across the codebase
    (the iteration-2 bug): the Wave-4 `survival_status` verdict
    (validated/falsified/inconclusive) takes precedence; otherwise the schema
    `Hypothesis.status` (active/retired/saturated/falsified). 'new', missing, and
    'inconclusive' are PENDING (not yet terminally judged) — they must BLOCK a
    `dry` verdict, never count as death (a freshly-scaffolded child must not look
    dead)."""
    sv = w4_by_id.get(str(hyp.get("id")), "")
    if sv == "validated":
        return "alive"
    if sv == "falsified":
        return "dead"
    if sv == "inconclusive":
        return "pending"
    st = str(hyp.get("status") or "").lower()
    if st in ("falsified", "retired", "saturated"):
        return "dead"   # terminally judged / exhausted — no more digging
    if st in ("active", "validated", "survives"):
        return "alive"
    return "pending"     # 'new', missing/None, unknown → not yet judged


def assess_deepen(hyps: list[dict[str, Any]], target: str, max_depth: int,
                  w4_by_id: dict[str, str]) -> dict[str, Any]:
    """Single source of truth for re-entry assessment, shared by `deepen` and
    observe's candidate_states. Advances the FRONTIER (deepest alive node in the
    target's subtree) so each round strictly increases depth — guaranteeing
    termination at max_depth — and declares `dry` only when no node in the
    subtree is alive OR pending (every direct line terminally dead)."""
    by_id = {str(h.get("id")): h for h in hyps if h.get("id")}
    if target not in by_id:
        return {"state": "absent"}
    children, _ = build_forest(hyps)       # DIRECT-parent children (matches the tree)
    depths = depth_map(hyps)

    # subtree (target + transitive descendants) via the direct-children map
    seen: set[str] = set()
    stack = [target]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(children.get(n, []))

    # Dryness is about the target's DESCENDANTS, not the target itself (the lead
    # is expected to stay 'alive' — that is not what we're asking).
    descendants = seen - {target}
    alive_desc = [s for s in descendants if lifestate(by_id[s], w4_by_id) == "alive"]
    pending_desc = [s for s in descendants if lifestate(by_id[s], w4_by_id) == "pending"]
    direct = children.get(target, [])

    # DRY: the lead WAS deepened (direct children exist) and every descendant is
    # terminally dead — no alive sub-lead, nothing still pending judgement.
    if direct and not alive_desc and not pending_desc:
        return {"state": "dry", "children_explored": len(direct)}

    # Frontier = the deepest ALIVE descendant (each round advances depth → bounded
    # by max_depth → termination guaranteed). If no alive descendant yet (first
    # round, or only-pending children), deepen the target itself.
    frontier = max(alive_desc, key=lambda s: depths.get(s, 1)) if alive_desc else target
    fdepth = depths.get(frontier, 1)
    if fdepth >= max_depth:
        return {"state": "budget_spent", "frontier": frontier,
                "frontier_depth": fdepth, "max_depth": max_depth}
    return {"state": "deepenable", "frontier": frontier,
            "frontier_depth": fdepth, "max_depth": max_depth}


def compute_funnel(run_root: Path) -> dict[str, Any]:
    """Explored→survived counts. Presence-not-truthiness on the wave-4 tallies
    (an explicit n_validated=0 must stay 0, not fall through to the by-verdict
    count)."""
    run_root = Path(run_root)
    hyps = load_hypotheses(run_root)
    explored = len(hyps)
    killed = 0
    kc = run_root / "killed_candidates.jsonl"
    if kc.is_file():
        killed = sum(1 for ln in kc.read_text(encoding="utf-8").splitlines() if ln.strip())
    w4 = _load_json(run_root / "wave4_validation.json") or {}
    vals = w4.get("validations") or []
    by_verdict: dict[str, int] = {}
    ties = 0
    for v in vals:
        s = str(v.get("survival_status") or v.get("aviv_verdict") or "unknown")
        by_verdict[s] = by_verdict.get(s, 0) + 1
        if v.get("discrimination_target"):
            ties += 1

    def _count(key: str, vk: str) -> int:
        return int(w4[key]) if key in w4 else by_verdict.get(vk, 0)

    return {
        "explored": explored,
        "killed_in_tournament": killed,
        "validated": _count("n_validated", "validated"),
        "falsified": _count("n_falsified", "falsified"),
        "inconclusive": _count("n_inconclusive", "inconclusive"),
        "verdicts": by_verdict,
        "ties_resolved_by_selection": ties,
        "tree_depth_reached": forest_depth(hyps),
    }


def emit_funnel(run_root: Path) -> dict[str, Any]:
    """Compute + persist triggers/<run_id>/funnel.json. Returns the funnel."""
    run_root = Path(run_root)
    fn = compute_funnel(run_root)
    fn["run_id"] = run_root.name
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "funnel.json").write_text(json.dumps(fn, ensure_ascii=False, indent=2), encoding="utf-8")
    return fn
