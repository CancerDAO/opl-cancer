"""intake_router — the deterministic CRISIS floor (de-scripted).

De-script (ADR-0040): task/method routing used to be a hand-curated keyword map
(``_KNOWN_TASK_KEYWORDS``) + keyword→method-DAG stubs (``_UNKNOWN_DAG_STUBS``) —
medical judgment written as ``if keyword in text``. That judgment now belongs to
the host LLM router (``prompts/pi/intake_router_llm.md``), which composes the task
package / method DAG semantically over the full registry.

What stays in Python is the ONE thing that must be deterministic: the G24 crisis
floor (an LLM cannot be allowed to suppress a verbatim self-harm hit). So
``route_intake`` now does exactly two things:
  1. run the mechanical G24 crisis gate FIRST (the non-suppressible safety floor);
  2. for any non-crisis question, defer task routing to the host LLM router.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


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
    # G24 crisis gate result. When crisis_block is True, Sid MUST emit
    # crisis_card.json and refuse to advance to any wave dispatch.
    crisis_block: bool = False
    crisis_evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def route_intake(user_question: str, profile: dict[str, Any] | None = None) -> IntakeRoute:
    """Crisis-floor intake. Crisis → crisis_card_emission (block); else defer to host LLM."""
    # ─── Path 0: CRISIS (the deterministic floor) — runs FIRST ──────────
    # G24 is a no-LLM mechanical gate (an LLM cannot suppress a verbatim SI
    # keyword hit). It is the non-suppressible floor behind the upstream LLM
    # crisis_detection prompt.
    crisis = _scan_crisis(user_question, profile)
    if crisis is not None:
        return IntakeRoute(
            matched_task_package="crisis_card_emission",
            acknowledgement=(
                "我先停下所有检索。你现在的安全是唯一要紧的事。"
                "我会立刻把危机支持资源给你，不会继续往下跑任何分析。"
            ),
            rationale="G24 crisis gate fired — crisis_card_emission takes priority over all routing.",
            crisis_block=True,
            crisis_evidence=crisis,
        )

    # ─── Non-crisis: defer task/method routing to the host LLM router ───
    return IntakeRoute(
        matched_task_package="host_llm_router",
        acknowledgement=_ack_for(user_question),
        rationale=(
            "non-crisis intake — task package / method DAG routing is deferred to "
            "the host LLM router (prompts/pi/intake_router_llm.md), not a keyword map."
        ),
    )


# ─── internals ────────────────────────────────────────────────────────────


def _scan_crisis(
    user_question: str, profile: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Run the mechanical G24 crisis gate over the raw patient question.

    Returns the gate's evidence dict on a crisis hit, else None. Kept mechanical
    by design (no-silent-fallback policy — fires even with no network/LLM)."""
    from opl_cancer.validators.gates.g24_crisis_detection import (
        G24CrisisDetectionGate,
    )
    from opl_cancer.validators.mechanical_gates import GateStatus

    claim: dict[str, Any] = {"patient_text": user_question or ""}
    if profile and profile.get("jurisdiction_hint"):
        claim["profile_jurisdiction_hint"] = profile["jurisdiction_hint"]
    result = G24CrisisDetectionGate().check(claim)
    if result.status == GateStatus.FAIL and result.block:
        return dict(result.evidence or {})
    return None


def _ack_for(user_question: str) -> str:
    if not user_question.strip():
        return "Question received — please give me a few more details so I can route it."
    snippet = user_question.strip()
    if len(snippet) > 160:
        snippet = snippet[:157] + "…"
    return f"Heard you: '{snippet}'. Let me route this to the right part of the team."


__all__ = ["IntakeRoute", "route_intake"]
