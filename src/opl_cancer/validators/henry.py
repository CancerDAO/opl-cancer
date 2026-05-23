"""Henry — 4-layer IRB-substitute Auditor orchestrator. Spec §8.

Henry's role is the *transparency layer*: he does not block, but he forces
disclosure + acknowledgment for any claim at Level 3 (high-risk) or Level 4
(boundary/EAP). Founder-mode philosophy (per spec §17.1 fix-target):
levels gate the patient-facing surface, not gate the AI's freedom.

The 4 layers (spec §8):
  L1 — Risk-disclosure-card forced emission for L3/L4 claims.
  L2 — Model-disagreement surfacing (reviewer challenges => surfaced to patient).
  L3 — Known-serious-risk checklist forced from per-drug catalogue.
  L4 — Patient acknowledgment loop (pending acks queue under outstanding/).

memory:feedback_no_offline_only — Henry MUST fail loudly if the serious-risks
catalogue is missing in production. Tests inject a stub catalogue.
memory:feedback_no_false_completion — no silent skipping of L3/L4 claims.

P6/Iter 9 — L2 can optionally accept an LLM client for axis-naming summarisation
(see :meth:`HenryAuditor.summarise_disagreement_axes`). Env-gated; falls back to
verbatim surfacing if no client is provided.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opl_cancer.llm.base import LLMClient, LLMRequest

from opl_cancer.delivery.risk_card import (
    RiskDisclosureCard,
    RiskDisclosureCardError,
)
from opl_cancer.validators.permission_levels import (
    Level,
    requires_patient_acknowledgment,
    requires_risk_disclosure,
)


class HenryAuditError(RuntimeError):
    """Raised when Henry's preconditions fail (missing knowledge, malformed claim)."""


@dataclass
class HenryAuditResult:
    """Result of Henry's 4-layer audit on a single claim."""

    claim_id: str
    level: Level
    layer1_card: RiskDisclosureCard | None = None
    layer2_disagreements: list[str] = field(default_factory=list)
    layer3_serious_risks: list[str] = field(default_factory=list)
    layer4_ack_required: bool = False
    layer4_ack_pending_path: str | None = None
    notes: list[str] = field(default_factory=list)


class HenryAuditor:
    """4-layer IRB-substitute auditor. Stateless orchestrator.

    Args:
        serious_risks_path: path to per-drug serious-risks JSON catalogue.
        outstanding_dir: directory for L4 pending-ack records.
    """

    def __init__(
        self,
        serious_risks_path: Path,
        outstanding_dir: Path,
    ) -> None:
        if not serious_risks_path.exists():
            raise HenryAuditError(
                f"serious_risks catalogue missing at {serious_risks_path}; "
                "production refuses to fall back silently (memory:feedback_no_offline_only)."
            )
        self.serious_risks_path = serious_risks_path
        self.outstanding_dir = outstanding_dir
        self._catalogue: dict[str, Any] = json.loads(
            serious_risks_path.read_text(encoding="utf-8")
        )

    # ---- public API ----

    def audit_claim(
        self,
        *,
        claim_id: str,
        claim_text: str,
        level: Level,
        drugs_mentioned: list[str] | None = None,
        reviewer_challenges: list[str] | None = None,
        epistemic_gaps: list[str] | None = None,
        alternatives: list[str] | None = None,
    ) -> HenryAuditResult:
        """Run the 4 layers on one claim. Returns HenryAuditResult.

        For L0-L2 claims the result is essentially a pass-through (layers all
        return empty). For L3/L4 the layers fire and a risk_card + pending ack
        are produced.
        """
        result = HenryAuditResult(claim_id=claim_id, level=level)

        # L3 — serious-risk checklist (computed FIRST so L1 card can embed risks).
        serious = self._layer3_serious_risks(drugs_mentioned or [])
        result.layer3_serious_risks = serious

        # L1 — risk-disclosure-card emission for L3/L4.
        if requires_risk_disclosure(level):
            try:
                card = RiskDisclosureCard(
                    card_id=f"card-{claim_id}-{uuid.uuid4().hex[:8]}",
                    claim_text=claim_text,
                    level=3 if level == Level.L3_HIGH_RISK else 4,
                    known_serious_risks=serious,
                    epistemic_gaps=epistemic_gaps or ["unknown — patient cohort gap"],
                    alternatives=alternatives or [],
                )
            except RiskDisclosureCardError as exc:
                raise HenryAuditError(
                    f"L1 card emission failed for claim {claim_id!r}: {exc}"
                ) from exc
            result.layer1_card = card
        else:
            result.notes.append("L1 skipped — claim below L3 threshold.")

        # L2 — model-disagreement surfacing.
        result.layer2_disagreements = self._layer2_disagreements(reviewer_challenges or [])

        # L4 — patient acknowledgment loop.
        if requires_patient_acknowledgment(level) and result.layer1_card is not None:
            self.outstanding_dir.mkdir(parents=True, exist_ok=True)
            pending_path = self.outstanding_dir / f"{result.layer1_card.card_id}.json"
            pending_path.write_text(
                json.dumps(
                    {
                        "card_id": result.layer1_card.card_id,
                        "claim_id": claim_id,
                        "claim_text": claim_text,
                        "level": int(level),
                        "known_serious_risks": serious,
                        "epistemic_gaps": result.layer1_card.epistemic_gaps,
                        "alternatives": result.layer1_card.alternatives,
                        "created_at": result.layer1_card.created_at,
                        "patient_acknowledged_at": None,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            result.layer4_ack_required = True
            result.layer4_ack_pending_path = str(pending_path)

        return result

    # ---- private layers ----

    def _layer2_disagreements(self, reviewer_challenges: list[str]) -> list[str]:
        """L2 — surface reviewer disagreements verbatim (rule-based P5)."""
        return [c.strip() for c in reviewer_challenges if c and c.strip()]

    async def summarise_disagreement_axes(
        self,
        reviewer_challenges: list[str],
        *,
        llm_client: LLMClient,
        model_id: str,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        """L2 LLM extension (Iter 9 #3): name the disagreement axes.

        Env-gated — caller passes ``llm_client`` only when they want LLM
        summarisation. Returns ``{"axes": [...], "summary": "..."}`` JSON.

        memory:feedback_no_offline_only — if caller chose to invoke the LLM,
        any network failure surfaces as a raised exception (no silent fallback
        to rule-based verbatim).
        memory:reference_minimax_llm — when MiniMax is the client, caller must
        pass model_id="MiniMax-M2.7".
        """
        cleaned = self._layer2_disagreements(reviewer_challenges)
        if not cleaned:
            return {"axes": [], "summary": ""}
        prompt = (
            "You are summarising reviewer disagreement axes for a patient-facing "
            "report. Read the verbatim reviewer challenges below and return JSON:\n"
            "{\n"
            "  \"axes\": [\"<axis-1>\", \"<axis-2>\", ...],\n"
            "  \"summary\": \"<one-sentence neutral summary>\"\n"
            "}\n"
            "Axes are SHORT noun-phrases naming the dimension of disagreement "
            "(e.g. 'evidence_quality', 'dose_safety', 'population_generalisability'). "
            "Do NOT take a side. Do NOT invent challenges not in the list.\n\n"
            "Reviewer challenges (verbatim):\n"
            + "\n".join(f"- {c}" for c in cleaned)
        )
        resp = await llm_client.complete(
            LLMRequest(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        )
        parsed: dict[str, Any] = json.loads(resp.content)
        # Defensive validation — never propagate malformed shape downstream.
        axes_raw = parsed.get("axes", [])
        summary_raw = parsed.get("summary", "")
        if not isinstance(axes_raw, list):
            axes_raw = []
        return {
            "axes": [str(a) for a in axes_raw if isinstance(a, (str, int, float))],
            "summary": str(summary_raw),
        }

    def _layer3_serious_risks(self, drugs_mentioned: list[str]) -> list[str]:
        """L3 — collect serious risks for all named drugs from catalogue.

        Drug names are normalised case-insensitively. Unknown drugs are flagged
        in returned list so Henry surfaces 'unknown drug' rather than silently
        omitting (fail-closed per spec §7 G11 spirit).
        """
        out: list[str] = []
        for drug in drugs_mentioned:
            key = drug.strip().lower()
            entry = self._catalogue.get(key)
            if entry is None:
                out.append(f"[unknown drug: {drug!r} — not in serious-risks catalogue]")
                continue
            for risk in entry.get("known_serious_risks", []):
                out.append(f"{entry.get('inn', drug)}: {risk}")
        return out

    # ---- ack helpers ----

    def acknowledge(self, card_id: str, acknowledged_at: str) -> dict[str, Any]:
        """Mark a pending ack as acknowledged. Returns updated record."""
        path = self.outstanding_dir / f"{card_id}.json"
        if not path.exists():
            raise HenryAuditError(
                f"No pending ack for card_id={card_id!r} at {path}"
            )
        rec: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        rec["patient_acknowledged_at"] = acknowledged_at
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        return rec

    def list_pending(self) -> list[dict[str, Any]]:
        """List all pending (un-acknowledged) cards."""
        if not self.outstanding_dir.exists():
            return []
        out: list[dict[str, Any]] = []
        for p in sorted(self.outstanding_dir.glob("*.json")):
            rec = json.loads(p.read_text(encoding="utf-8"))
            if rec.get("patient_acknowledged_at") is None:
                out.append(rec)
        return out
