"""Insight card + evidence + reviewer + auditor schemas. Spec §5.2.

P2 additions: Hypothesis + TournamentRound (spec §5.1 hypotheses + tournaments).
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ClaimLayer(str, Enum):
    ESTABLISHED = "established"
    EXPLORATORY = "exploratory"
    SPECULATIVE = "speculative"


class EvidenceType(str, Enum):
    PMID = "pmid"
    DATASET = "dataset"
    GUIDELINE = "guideline"
    TRIAL = "trial"
    KB = "knowledge_base"


class Evidence(BaseModel):
    type: EvidenceType
    id: str = Field(min_length=1)
    quote: str = ""
    extras: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _pmid_quote_required(self) -> "Evidence":
        """Safety eval S6: PMID-type evidence must have a non-empty quote."""
        if self.type == EvidenceType.PMID and not self.quote:
            raise ValueError("PMID evidence must have a non-empty quote (S6)")
        return self


class ProducedBy(BaseModel):
    executor_task: str
    model: str
    prompt_version: str
    run_id: str


class ReviewedBy(BaseModel):
    reviewer_model: str
    verdict: Literal["pass", "fail", "needs_revision"]
    challenges: list[str] = Field(default_factory=list)
    review_prompts_used: list[str] = Field(default_factory=list)


class AuditedBy(BaseModel):
    auditor_run: str
    permission_level: int = Field(ge=0, le=4)
    clearances: list[str] = Field(default_factory=list)
    risk_card_id: str | None = None


class WithdrawStatus(BaseModel):
    reason: str
    withdrawn_at: str
    evidence: str = ""


class InsightCard(BaseModel):
    """Single patient-facing claim, append-only versioned. Spec §5.2."""

    id: str
    version: int = Field(ge=1)
    claim: str
    claim_layer: ClaimLayer
    evidence: list[Evidence] = Field(min_length=1)
    produced_by: ProducedBy
    reviewed_by: ReviewedBy
    audited_by: AuditedBy
    provenance_hash: str
    created_at: str
    patient_surfaced_at: str | None = None
    patient_acknowledged_at: str | None = None
    withdraw_status: WithdrawStatus | None = None
    supersedes: str | None = None
    on_chain_receipt: str | None = None  # always None in v0 (no chain integration)

    @field_validator("provenance_hash")
    @classmethod
    def _hash_must_be_sha256(cls, v: str) -> str:
        if not v.startswith("sha256:") or len(v) != 7 + 64:
            raise ValueError("provenance_hash must be sha256:<64 hex chars>")
        return v


# ============================================================================
# P2 — Hypothesis + TournamentRound (spec §5.1)
# ============================================================================


HypothesisStatus = Literal["active", "retired", "saturated", "falsified"]

GenerationStrategy = Literal[
    "literature_gap",
    "cross_domain",
    "novel_mechanism",
    "feasibility_first",
    "target_synergy_emergent",
    "undrugged_target_design",
    "evolution_combination",
    "evolution_simplification",
    "evolution_extension",
    "evolution_analogy",
    "evolution_resilience",
    "evolution_outside_box",
    "feedback_driven",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Hypothesis(BaseModel):
    """A speculative directional claim produced by the hypothesis-generation loop.

    Founder-mode philosophy (founder-mode design intent): hypotheses
    are by definition exploratory; default ``claim_layer="speculative"`` and
    uncertainty must be surfaced.
    """

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    claim_layer: ClaimLayer = ClaimLayer.SPECULATIVE
    elo_rating: float = 1200.0
    status: HypothesisStatus = "active"
    parent_chain: list[str] = Field(default_factory=list)
    generation_strategy: GenerationStrategy = "literature_gap"
    evidence_refs: list[dict[str, str]] = Field(default_factory=list)
    meta_critique_inherited: list[str] = Field(default_factory=list)
    rationale: str = ""
    created_at: str = Field(default_factory=_utc_now_iso)


class TournamentOutcome(BaseModel):
    """One pair outcome inside a round."""

    a: str
    b: str
    winner: Literal["A", "B", "draw"]
    reason: str = ""


class TournamentRound(BaseModel):
    """A single round of the Co-Sci-style Elo tournament. Spec §5.1 tournaments table."""

    round_id: str
    wave_index: int = Field(ge=0)
    participants: list[str] = Field(default_factory=list)
    pairings: list[tuple[str, str]] = Field(default_factory=list)
    outcomes: list[TournamentOutcome] = Field(default_factory=list)
    elo_deltas: list[dict[str, float]] = Field(default_factory=list)
    meta_critique: str = ""
    created_at: str = Field(default_factory=_utc_now_iso)
