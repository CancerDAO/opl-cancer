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


def build_forest(hyps: list[dict[str, Any]], flat_fallback: bool = True) -> tuple[dict[str, list[str]], list[str]]:
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
    if flat_fallback and not roots and by_id:
        # Renderer-only: a fully rootless (cyclic) forest must still display its
        # nodes. depth_map calls with flat_fallback=False so it does NOT fabricate
        # depth-1 for rootless nodes (that defeated the ceiling guard / livelock).
        roots = sorted(by_id)
        children = {hid: [] for hid in by_id}
    return children, sorted(roots)


def depth_map(hyps: list[dict[str, Any]]) -> dict[str, int]:
    """Per-node tree depth on the SAME forest the renderer builds (dangling
    parents = roots, root depth = 1), cycle-safe. Single source of truth for
    depth — used by observe, validate, AND the deepen budget so they cannot
    disagree (the bug iteration-2's review caught)."""
    # No flat-fallback: a rootless-cyclic forest yields NO depths, so every such
    # node is "missing" → treated as at-ceiling by assess_deepen (_depth default
    # = max_depth) → terminal (budget_spent), never an infinite frontier.
    children, roots = build_forest(hyps, flat_fallback=False)
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
    sv = str(w4_by_id.get(str(hyp.get("id")), "")).strip().lower()
    if sv == "validated":
        return "alive"
    if sv == "falsified":
        return "dead"
    # FAIL-SAFE: any other NON-EMPTY verdict (inconclusive / weakened / refuted /
    # rejected / disproven / any synonym the validator subagent may emit) is
    # "judged but not affirmatively alive" → pending. It must NEVER fall through
    # to the (possibly stale 'active') schema status and surface a Wave-4-
    # undermined lead as a live deepenable frontier (the 真假希望 anti-pattern).
    if sv:
        return "pending"
    st = str(hyp.get("status") or "").lower()  # only a MISSING verdict consults schema
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
    direct = children.get(target, [])

    # P1: a terminally-dead lead (Wave-4 falsified, or schema retired/saturated)
    # is NEVER recommended for deepening — that would present a disproven
    # direction as a live frontier (the false-hope / 真假希望 anti-pattern).
    if lifestate(by_id[target], w4_by_id) == "dead":
        return {"state": "dead_target", "target": target,
                "children_explored": len(direct)}

    # subtree (target + transitive descendants) via the direct-children map
    seen: set[str] = set()
    stack = [target]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(children.get(n, []))
    order = sorted(seen)  # deterministic tie-break (independent of set/hash order)
    alive = [s for s in order if lifestate(by_id[s], w4_by_id) == "alive"]
    pending = [s for s in order if lifestate(by_id[s], w4_by_id) == "pending"]

    # A node with NO depth entry is unreachable from any acyclic root (a cyclic
    # island, or the flat-fallback when there are zero roots) — treat it as AT the
    # ceiling so it can never be an infinitely-deepenable frontier. depths.get
    # defaulting to 1 was the non-termination hole: 1 < max_depth stayed true
    # forever for corrupted/cyclic parent_chains.
    def _depth(n: str) -> int:
        return depths.get(n, max_depth)

    # The frontier is an alive node not yet deepened (no children) with room. A
    # node is deepened AT MOST ONCE (spawning gives it children → never "ready"
    # again — a structural width cap), so each deepenable round consumes a ready
    # leaf and creates a node one level deeper: the frontier depth strictly
    # increases → bounded by max_depth → TERMINATION GUARANTEED.
    ready = [n for n in alive if not children.get(n) and _depth(n) < max_depth]
    if ready:
        frontier = max(ready, key=lambda s: (_depth(s), s))
        return {"state": "deepenable", "frontier": frontier,
                "frontier_depth": _depth(frontier), "max_depth": max_depth}

    # No ready alive leaf. If anything is still pending judgement, BLOCK re-spawn
    # (validate what's there first) — catches the relocated livelock where an
    # alive intermediate node's children are all pending.
    if pending:
        return {"state": "awaiting_judgement", "pending": len(pending),
                "children_explored": len(direct)}

    # An alive leaf pinned at (or above) the depth ceiling → budget spent.
    capped = [n for n in alive if not children.get(n) and _depth(n) >= max_depth]
    if capped:
        frontier = max(capped, key=lambda s: (_depth(s), s))
        return {"state": "budget_spent", "frontier": frontier,
                "frontier_depth": _depth(frontier), "max_depth": max_depth}

    # Every explored line under the target is terminally dead → dry.
    return {"state": "dry", "children_explored": len(direct)}


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
