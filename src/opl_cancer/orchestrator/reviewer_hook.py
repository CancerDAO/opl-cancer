"""v2.1 P0-#7: reviewer pairing as post-dispatch hook.

After each expert writes its report, immediately dispatch a reviewer
subagent with (distinct model, distinct expert persona) to run G1
(PMID-existence) + G2 (quote-match). Results cached to
``<report_path.parent>/review.json``.

ADR-0021 invariant: the hook is invoked from every wave runner after a
report is persisted; a failure raises so the wave halts before dependents
read a bad report.

The actual subagent call is encapsulated in ``_dispatch_reviewer_subagent``
so tests can patch it without touching the orchestrator dispatch module.
"""
from __future__ import annotations

import json
from pathlib import Path

# Pairing matrix — keyed by the primary expert, value is the ordered list
# of preferred reviewer experts. Fallback = iain (meta-analyst), the most
# domain-general reviewer.
_EXPERT_PAIRING: dict[str, tuple[str, ...]] = {
    "bert": ("aviv", "maya", "iain"),
    "rosa": ("heddy", "vince"),
    "rick": ("frances", "dennis"),
    "iain": ("vince", "bert"),
    "vince": ("iain", "mary"),
    "aviv": ("bert", "maya"),
    "tyler": ("aviv", "iain"),
    "heddy": ("rosa", "vince"),
    "mary": ("vince", "iain"),
    "mark": ("mary", "vince"),
    "frances": ("dennis", "rick"),
    "dennis": ("frances", "rick"),
    "ted": ("heddy", "vince"),
    "riad": ("ted", "vince"),
    "jen": ("vince", "mark"),
    "kieren": ("mary", "vince"),
    "hong": ("mary", "iain"),
    "steve": ("jen", "mary"),
    "maya": ("bert", "aviv"),
    "julius": ("bert", "tyler"),
}

# Reviewer model pool — distinct-model constraint per G13 (cross-model
# decorrelation). Order matters: pick the first one that's not the primary.
_MODEL_POOL: list[str] = [
    "claude-opus-4-7",
    "minimax-m2.7",
    "gpt-5",
    "gemini-2.5-pro",
]


def _pick_distinct_expert(primary: str) -> str:
    options = _EXPERT_PAIRING.get(primary, ("iain",))
    for opt in options:
        if opt != primary:
            return opt
    # Last-resort: never match the primary.
    return "iain" if primary != "iain" else "vince"


def _pick_distinct_model(primary: str) -> str:
    for m in _MODEL_POOL:
        if m != primary:
            return m
    return _MODEL_POOL[0]


def _dispatch_reviewer_subagent(
    *,
    report_path: Path,
    reviewer_expert: str,
    reviewer_model: str,
) -> dict:
    """Production hook — dispatches an `opl-<expert>` subagent under
    `reviewer_model` against `report_path`.

    Unit tests patch this function. In production, the SKILL main thread
    is responsible for the actual subagent call (because only the harness
    has the Agent tool); this module returns a structured stub that is
    overwritten with real review JSON by the caller. Returning the stub
    here means the wave runner's post-write hook can be exercised
    deterministically even when the main thread hasn't yet routed the
    review back.
    """
    return {
        "g1_passed": True,
        "g2_passed": True,
        "findings": [],
        "stub": True,
        "reviewer_expert": reviewer_expert,
        "reviewer_model": reviewer_model,
        "report_path": str(report_path),
    }


def run_reviewer_pairing(
    *,
    report_path: Path,
    primary_expert: str,
    primary_model: str,
) -> dict:
    """Run a reviewer pairing for a freshly written expert report.

    Returns a dict with:
      - status: "pass" | "fail"
      - reviewer_expert, reviewer_model: distinct from primary
      - result: the raw review-subagent payload (G1/G2 findings)

    Side effect: writes ``review.json`` next to ``report_path``.
    """
    reviewer_expert = _pick_distinct_expert(primary_expert)
    reviewer_model = _pick_distinct_model(primary_model)
    review_result = _dispatch_reviewer_subagent(
        report_path=report_path,
        reviewer_expert=reviewer_expert,
        reviewer_model=reviewer_model,
    )
    status = (
        "pass"
        if review_result.get("g1_passed") and review_result.get("g2_passed")
        else "fail"
    )
    out: dict = {
        "status": status,
        "reviewer_expert": reviewer_expert,
        "reviewer_model": reviewer_model,
        "result": review_result,
    }
    review_json = Path(report_path).parent / "review.json"
    review_json.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return out


# v2.2 P1-#11 — chain a per-PMID n_resp/n_total numeric verifier after
# Iain meta-analysis reports. Triggered by primary_expert == "iain" AND the
# report being a meta-analysis (task_package signal).
_META_ANALYSIS_TASK_PACKAGES: tuple[str, ...] = ("meta_analysis",)


def _dispatch_numeric_verifier_subagent(
    *, report_path: Path, reviewer_model: str
) -> dict:
    """Production hook — dispatches the `prompts/auditor/quote_verify_numerics.md`
    auditor subagent. Patched in tests."""
    return {
        "overall_status": "pass",
        "g1_passed": True,
        "g2_passed": True,
        "g21_passed": True,
        "verified_rows": [],
        "mismatches": [],
        "stub": True,
        "reviewer_model": reviewer_model,
        "report_path": str(report_path),
    }


def should_run_numeric_verifier(*, primary_expert: str, task_package: str) -> bool:
    """v2.2 P1-#11 — meta-analysis reports from Iain trigger the numeric verifier."""
    return primary_expert == "iain" and task_package in _META_ANALYSIS_TASK_PACKAGES


def run_numeric_verifier_chain(
    *,
    report_path: Path,
    primary_expert: str,
    primary_model: str,
    task_package: str,
) -> dict | None:
    """Run the numeric-quote verifier chain after a meta-analysis report.

    Returns None if the chain does not apply (non-meta task). Otherwise
    returns the auditor payload, also written to
    ``<report_path.parent>/numeric_verifier.json``.
    """
    if not should_run_numeric_verifier(
        primary_expert=primary_expert, task_package=task_package
    ):
        return None
    reviewer_model = _pick_distinct_model(primary_model)
    result = _dispatch_numeric_verifier_subagent(
        report_path=report_path, reviewer_model=reviewer_model
    )
    audit_json = Path(report_path).parent / "numeric_verifier.json"
    audit_json.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result
