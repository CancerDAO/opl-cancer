"""intake_router — v2.5 RFC 0001 §8 item 8 (the c3195b66 bug fix).

Routes a free-form patient question to either:
1. A known v2.4 task package (exact match on a curated keyword map)
2. ``unknown_task_intake`` with a composed method DAG stub + L4 disclosure card

v2.5 ships the keyword-driven STUB. M5 swaps the keyword router for a real
LLM TaskComposer that produces an open-set DAG over the full MethodRegistry.

The release-gating regression: feeding the literal session-c3195b66 question
(see C3195B66_QUESTION constant in tests) MUST route to ``unknown_task_intake``
with a DAG that includes conformal_prediction + kaplan_meier, and an L4 card.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from opl_cancer.methods import MethodRegistry


# ─── known-task keyword map (small, hand-curated; M5 replaces) ─────────────


# Map of keyword tokens → existing task package name. First exact match wins.
# Keywords are lower-cased before lookup. Each entry should be specific
# enough that false positives are rare — when in doubt, omit; the unknown
# intake path is the safe default.
_KNOWN_TASK_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("acmg",), "acmg_germline_classification"),
    (("expanded access", "compassionate use"), "expanded_access_navigation"),
    (("meta-analysis", "meta analysis"), "meta_analysis"),
    (("cosmic signature", "mutational signature"), "cosmic_signature_extraction"),
    (("msi", "microsatellite"), "msi_detection"),
    (("tmb",), "tmb_calculation"),
    (("ddi", "drug-drug interaction"), "ddi_adme_dosing"),
    (("cpic", "pharmacogenomic"), "pharmacogenomics_cpic"),
    (("crisis", "suicide"), "crisis_card_emission"),
    (("subgroup",), "biostats_subgroup"),
    (("survival",), "biostats_survival"),
    (("recist",), "pathology_interpretation"),
    (("opentargets", "open targets"), "opentargets_evidence"),
]


# ─── compositional unknown-task patterns (DAG stubs) ────────────────────────


# Map of trigger-keyword tuple → composed method DAG node list. Keywords come
# from observed real-patient phrasing; M5 swaps for an LLM composer.
_UNKNOWN_DAG_STUBS: list[tuple[tuple[str, ...], list[str]]] = [
    # session-c3195b66 — AutoML / prognosis / public-databases
    (
        ("automl", "auto-ml", "机器学习建模", "公共数据库", "预测我的预后", "预测预后",
         "prognosis prediction", "predict my prognosis", "auto download", "auto-download"),
        ["kaplan_meier", "conformal_prediction"],
    ),
    # cohort projection prompts
    (
        ("cohort projection", "队列投影", "matched cohort", "n=1 projection"),
        ["kaplan_meier", "conformal_prediction"],
    ),
    # population PK prompts
    (
        ("population pk", "poppk", "nonmem", "群体药代"),
        ["popPK_NONMEM_proxy"],
    ),
]


# Standard L4 disclosure card text for AutoML-style requests.
_L4_CARD_AUTOML = (
    "**L4 Composed-Pipeline Disclosure** — this answer was produced by a "
    "composed method DAG, NOT a single certified task package. Method "
    "primitives used: {methods}. AutoML on N=1 data is not a safe operation "
    "(no IID assumption, no held-out validation, severe overfitting risk). "
    "What this team will instead do: surface the best available external "
    "cohort baseline (kaplan_meier) + a distribution-free uncertainty band "
    "(conformal_prediction) + transparent assumptions. The output is "
    "Level-4 speculative by definition. Patient is sole decision authority."
)


# ─── public API ────────────────────────────────────────────────────────────


@dataclass
class IntakeRoute:
    """Result of route_intake — Sid surfaces this back to the patient."""

    matched_task_package: str
    acknowledgement: str = ""
    decline_reasons: list[str] = field(default_factory=list)
    method_dag: list[dict[str, Any]] = field(default_factory=list)
    l4_disclosure_card: str | None = None
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def route_intake(user_question: str, profile: dict[str, Any] | None = None) -> IntakeRoute:
    """Route a patient question to a task package or the unknown_task_intake."""
    text = (user_question or "").lower()

    # ─── Path 1: known task ────────────────────────────────────────────
    for keywords, pkg in _KNOWN_TASK_KEYWORDS:
        if any(kw in text for kw in keywords):
            # Pull at least one method primitive into the DAG for traceability.
            method_dag = _dag_for_known_task(pkg)
            return IntakeRoute(
                matched_task_package=pkg,
                acknowledgement=f"Routing to task package: {pkg}",
                method_dag=method_dag,
                rationale=f"matched keyword set {keywords!r}",
            )

    # ─── Path 2: unknown task intake (the c3195b66 fix) ────────────────
    method_ids = _compose_unknown_dag(text)
    method_dag = [{"id": mid, "role": "speculative_pipeline_node"} for mid in method_ids]

    decline_reasons: list[str] = []
    if any(kw in text for kw in ("automl", "auto-ml", "机器学习建模", "预测我的预后", "公共数据库")):
        decline_reasons.extend(
            [
                "Naive AutoML on an N=1 patient context overfits — no IID "
                "assumption holds and there is no held-out validation set.",
                "'Optimal model + parameters' is a category error when only "
                "one observed unit is available.",
                "Safer alternative: external-cohort baseline (kaplan_meier) + "
                "distribution-free uncertainty (conformal_prediction).",
            ]
        )

    l4_card = _l4_card_for(method_ids, user_question)

    return IntakeRoute(
        matched_task_package="unknown_task_intake",
        acknowledgement=_ack_for(user_question),
        decline_reasons=decline_reasons,
        method_dag=method_dag,
        l4_disclosure_card=l4_card,
        rationale="no known task package matched; routed via compositional intake",
    )


# ─── internals ────────────────────────────────────────────────────────────


def _dag_for_known_task(task_pkg: str) -> list[dict[str, Any]]:
    """Surface at least one method primitive for traceability."""
    reg = MethodRegistry()
    reg.load_all()
    matches = [p for p in reg.all() if p.fast_path_task_package == task_pkg]
    if not matches:
        return []
    return [{"id": m.id, "role": "fast_path"} for m in matches]


def _compose_unknown_dag(text: str) -> list[str]:
    """Pick method primitives that match keywords in the question."""
    for keywords, dag in _UNKNOWN_DAG_STUBS:
        if any(kw.lower() in text for kw in keywords):
            return _filter_to_registered(dag)
    return _filter_to_registered(["kaplan_meier"])  # safest no-op default


def _filter_to_registered(method_ids: list[str]) -> list[str]:
    reg = MethodRegistry()
    reg.load_all()
    valid = {p.id for p in reg.all()}
    return [m for m in method_ids if m in valid]


def _ack_for(user_question: str) -> str:
    if not user_question.strip():
        return "Question received — please give me a few more details so I can route it."
    snippet = user_question.strip()
    if len(snippet) > 160:
        snippet = snippet[:157] + "…"
    return f"Heard you: '{snippet}'. Let me show you what we can actually do on N=1 here."


def _l4_card_for(method_ids: list[str], user_question: str) -> str:
    methods = ", ".join(method_ids) if method_ids else "(none — unresolved)"
    return _L4_CARD_AUTOML.format(methods=methods)


__all__ = ["IntakeRoute", "route_intake"]
