"""Risk-disclosure-card model + renderer. Spec §7 G8 + §8 layer 1.

Founder-mode philosophy: an L3/L4 claim MUST be surfaced with an explicit
disclosure card BEFORE it reaches the patient brief body. The card encodes:
  - what could go wrong (named, not euphemized)
  - what we don't know (epistemic gaps)
  - what alternative paths exist
  - what the patient must confirm before we proceed

memory:feedback_no_false_completion — no silent omission of L3/L4 risks.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class RiskDisclosureCardError(ValueError):
    """Raised when a card is malformed (missing required field per spec §8.L1)."""


class RiskDisclosureCard(BaseModel):
    """Spec §8 layer 1 forced disclosure card.

    Required for any insight at Level 3 (high-risk) or Level 4 (boundary/EAP).
    """

    card_id: str = Field(..., min_length=1)
    claim_text: str = Field(..., min_length=1)
    level: Literal[3, 4]
    known_serious_risks: list[str] = Field(default_factory=list)
    epistemic_gaps: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    requires_patient_acknowledgment: bool = True
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    patient_acknowledged_at: str | None = None
    source_claim_hash: str | None = None

    @field_validator("known_serious_risks")
    @classmethod
    def _validate_risks(cls, v: list[str]) -> list[str]:
        return v

    @model_validator(mode="after")
    def _validate_l3_l4_requires_risk_or_gap(self) -> "RiskDisclosureCard":
        if not self.known_serious_risks and not self.epistemic_gaps:
            raise RiskDisclosureCardError(
                f"RiskDisclosureCard {self.card_id!r} level={self.level} "
                "must declare at least one known_serious_risk OR epistemic_gap "
                "(fail-closed per spec §8 L1)."
            )
        return self

    def to_hashable(self) -> str:
        """Stable hash representation (excludes ack timestamp)."""
        payload = self.model_dump(exclude={"patient_acknowledged_at", "created_at"})
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    def content_hash(self) -> str:
        return "sha256:" + hashlib.sha256(self.to_hashable().encode("utf-8")).hexdigest()


def render_risk_card_markdown(card: RiskDisclosureCard) -> str:
    """Patient-facing markdown rendering."""
    risks = "\n".join(f"- {r}" for r in card.known_serious_risks) or "- (none catalogued)"
    gaps = "\n".join(f"- {g}" for g in card.epistemic_gaps) or "- (none flagged)"
    alts = "\n".join(f"- {a}" for a in card.alternatives) or "- (none surfaced)"
    ack_line = (
        f"\n**Acknowledged at:** {card.patient_acknowledged_at}"
        if card.patient_acknowledged_at
        else "\n**Status:** awaiting patient acknowledgment"
    )
    return (
        f"### Risk Disclosure Card — Level {card.level}\n\n"
        f"**Card ID:** `{card.card_id}`\n\n"
        f"**Claim:** {card.claim_text}\n\n"
        f"**Known serious risks:**\n{risks}\n\n"
        f"**What we do not know:**\n{gaps}\n\n"
        f"**Alternatives surfaced:**\n{alts}\n"
        f"{ack_line}\n"
    )


def render_risk_card_html(card: RiskDisclosureCard) -> str:
    """Patient-facing HTML rendering (no external CSS — inline tags only)."""

    def _list(items: list[str], empty: str) -> str:
        if not items:
            return f"<li><em>{empty}</em></li>"
        return "".join(f"<li>{_html_escape(i)}</li>" for i in items)

    ack = (
        f"<p><strong>Acknowledged at:</strong> {_html_escape(card.patient_acknowledged_at or '')}</p>"
        if card.patient_acknowledged_at
        else "<p><strong>Status:</strong> awaiting patient acknowledgment</p>"
    )
    return (
        f'<section class="risk-disclosure-card" data-level="{card.level}">'
        f"<h3>Risk Disclosure Card — Level {card.level}</h3>"
        f"<p><strong>Card ID:</strong> <code>{_html_escape(card.card_id)}</code></p>"
        f"<p><strong>Claim:</strong> {_html_escape(card.claim_text)}</p>"
        f"<p><strong>Known serious risks:</strong></p>"
        f"<ul>{_list(card.known_serious_risks, 'none catalogued')}</ul>"
        f"<p><strong>What we do not know:</strong></p>"
        f"<ul>{_list(card.epistemic_gaps, 'none flagged')}</ul>"
        f"<p><strong>Alternatives surfaced:</strong></p>"
        f"<ul>{_list(card.alternatives, 'none surfaced')}</ul>"
        f"{ack}"
        f"</section>"
    )


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
